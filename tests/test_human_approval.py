"""Tests for the human approval workflow.

Covers:
- Approval token generation (256-bit, cryptographically random)
- Token bound to pipeline + contract version
- Token single-use (second use rejected)
- Token expires after timeout
- Approval payload includes all required fields
- Approve action: gate passes
- Reject action: gate fails with rejection reason
- Timeout: automatic rejection
- Audit logging
"""

import time

import pytest

from gates.human_approval import (
    HumanApprovalWorkflow,
    ApprovalDecision,
)


@pytest.fixture
def workflow() -> HumanApprovalWorkflow:
    """Workflow with default 24hr timeout."""
    return HumanApprovalWorkflow(timeout_seconds=24 * 60 * 60)


@pytest.fixture
def short_timeout_workflow() -> HumanApprovalWorkflow:
    """Workflow with very short timeout for expiry testing."""
    return HumanApprovalWorkflow(timeout_seconds=0.1)


class TestTokenGeneration:
    """Test approval token generation."""

    def test_token_is_256_bit(self, workflow: HumanApprovalWorkflow) -> None:
        """Token should be 256-bit (32 bytes = 64 hex chars)."""
        token = workflow.generate_token(
            pipeline_execution_id="pipe-001",
            contract_version="v1.0",
        )
        assert len(token.token_hex) == 64  # 32 bytes as hex
        # Verify it's valid hex
        int(token.token_hex, 16)

    def test_tokens_are_unique(self, workflow: HumanApprovalWorkflow) -> None:
        """Each generated token should be unique."""
        tokens = set()
        for i in range(20):
            token = workflow.generate_token(
                pipeline_execution_id=f"pipe-{i:03d}",
                contract_version="v1.0",
            )
            tokens.add(token.token_hex)
        assert len(tokens) == 20

    def test_token_has_id(self, workflow: HumanApprovalWorkflow) -> None:
        """Token should have a short ID derived from the token hex."""
        token = workflow.generate_token(
            pipeline_execution_id="pipe-001",
            contract_version="v1.0",
        )
        assert token.token_id is not None
        assert len(token.token_id) == 16

    def test_token_starts_as_pending(self, workflow: HumanApprovalWorkflow) -> None:
        """Newly generated token should have PENDING decision."""
        token = workflow.generate_token(
            pipeline_execution_id="pipe-001",
            contract_version="v1.0",
        )
        assert token.decision == ApprovalDecision.PENDING
        assert token.used is False


class TestTokenBinding:
    """Test token binding to pipeline + contract version."""

    def test_token_bound_to_pipeline(self, workflow: HumanApprovalWorkflow) -> None:
        token = workflow.generate_token(
            pipeline_execution_id="pipe-001",
            contract_version="v1.0",
        )
        assert token.pipeline_execution_id == "pipe-001"
        assert token.contract_version == "v1.0"

    def test_different_pipelines_get_different_tokens(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        t1 = workflow.generate_token("pipe-001", "v1.0")
        t2 = workflow.generate_token("pipe-002", "v1.0")
        assert t1.token_hex != t2.token_hex
        assert t1.pipeline_execution_id != t2.pipeline_execution_id


class TestSingleUse:
    """Test that tokens are single-use."""

    def test_second_use_rejected(self, workflow: HumanApprovalWorkflow) -> None:
        """Using a token a second time should fail."""
        token = workflow.generate_token("pipe-001", "v1.0")

        # First use: should succeed
        success1, msg1 = workflow.process_decision(
            token_hex=token.token_hex,
            decision=ApprovalDecision.APPROVE,
            ip_address="203.0.113.1",
        )
        assert success1 is True

        # Second use: should fail
        success2, msg2 = workflow.process_decision(
            token_hex=token.token_hex,
            decision=ApprovalDecision.APPROVE,
            ip_address="203.0.113.1",
        )
        assert success2 is False
        assert "single-use" in msg2.lower() or "already used" in msg2.lower()

    def test_token_marked_used_after_decision(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")
        assert token.used is False

        workflow.process_decision(
            token.token_hex, ApprovalDecision.APPROVE, ip_address="203.0.113.1"
        )
        assert token.used is True

    def test_validation_fails_after_use(self, workflow: HumanApprovalWorkflow) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")
        workflow.process_decision(
            token.token_hex, ApprovalDecision.APPROVE, ip_address="203.0.113.1"
        )

        is_valid, reason = workflow.validate_token(token.token_hex)
        assert is_valid is False
        assert "used" in reason.lower() or "single" in reason.lower()


class TestTokenExpiry:
    """Test that tokens expire after timeout."""

    def test_token_expires(self, short_timeout_workflow: HumanApprovalWorkflow) -> None:
        """Token should be invalid after timeout period."""
        token = short_timeout_workflow.generate_token("pipe-001", "v1.0")
        assert token.is_valid is True

        # Wait for expiry
        time.sleep(0.2)

        assert token.is_expired is True
        assert token.is_valid is False

    def test_expired_token_rejected(
        self, short_timeout_workflow: HumanApprovalWorkflow
    ) -> None:
        """Processing a decision on an expired token should fail."""
        token = short_timeout_workflow.generate_token("pipe-001", "v1.0")
        time.sleep(0.2)

        success, msg = short_timeout_workflow.process_decision(
            token.token_hex, ApprovalDecision.APPROVE, ip_address="203.0.113.1"
        )
        assert success is False
        assert "expired" in msg.lower()

    def test_token_valid_before_expiry(self, workflow: HumanApprovalWorkflow) -> None:
        """Token should be valid before the timeout."""
        token = workflow.generate_token("pipe-001", "v1.0")
        is_valid, _ = workflow.validate_token(token.token_hex)
        assert is_valid is True


class TestApprovalPayload:
    """Test approval payload contains all required fields."""

    def test_payload_has_all_fields(self, workflow: HumanApprovalWorkflow) -> None:
        payload = workflow.build_payload(
            pipeline_id="pipe-001",
            source_description="PostgreSQL production DB",
            target_tier="staging",
            row_count=1000,
            column_classifications={
                "customers.name": "confidential",
                "customers.ssn": "restricted",
                "customers.id": "internal",
            },
            strategy_map={
                "customers.name": "tokenize",
                "customers.ssn": "redact",
                "customers.id": "passthrough",
            },
            masked_dataset={
                "customers": [
                    {"name": "NAME_a1", "ssn": "[REDACTED]", "id": 1},
                    {"name": "NAME_b2", "ssn": "[REDACTED]", "id": 2},
                    {"name": "NAME_c3", "ssn": "[REDACTED]", "id": 3},
                ]
            },
            contract_version="v2.1",
            sample_size=5,
        )

        # Pipeline summary
        assert payload.pipeline_id == "pipe-001"
        assert payload.source_description == "PostgreSQL production DB"
        assert payload.target_tier == "staging"
        assert payload.row_count == 1000

        # Contract classifications
        assert "customers.name" in payload.column_classifications
        assert payload.column_classifications["customers.name"] == "confidential"

        # Strategy map
        assert "customers.ssn" in payload.strategy_map
        assert payload.strategy_map["customers.ssn"] == "redact"

        # Sample rows
        assert len(payload.sample_rows) <= 5
        assert len(payload.sample_rows) == 3  # Only 3 rows available

        # Risk assessment
        assert payload.risk_assessment["restricted_columns"] == 1
        assert payload.risk_assessment["confidential_columns"] == 1
        assert payload.risk_assessment["total_sensitive_columns"] == 2

        # Contract version
        assert payload.contract_version == "v2.1"

    def test_payload_serialization(self, workflow: HumanApprovalWorkflow) -> None:
        payload = workflow.build_payload(
            pipeline_id="pipe-001",
            source_description="test",
            target_tier="staging",
            row_count=10,
            column_classifications={"t.c": "confidential"},
            strategy_map={"t.c": "tokenize"},
            masked_dataset={"t": [{"c": "NAME_abc"}]},
            contract_version="v1.0",
        )
        d = payload.to_dict()
        assert "pipeline_id" in d
        assert "risk_assessment" in d
        assert "sample_rows" in d


class TestApproveAction:
    """Test approve action."""

    def test_approve_records_decision(self, workflow: HumanApprovalWorkflow) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")

        success, msg = workflow.process_decision(
            token.token_hex,
            ApprovalDecision.APPROVE,
            ip_address="203.0.113.1",
        )

        assert success is True
        assert token.decision == ApprovalDecision.APPROVE
        assert token.decision_timestamp is not None

    def test_approve_decision_retrievable(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")
        workflow.process_decision(
            token.token_hex,
            ApprovalDecision.APPROVE,
            ip_address="203.0.113.1",
        )

        decision = workflow.get_decision(token.token_hex)
        assert decision == ApprovalDecision.APPROVE


class TestRejectAction:
    """Test reject action."""

    def test_reject_with_reason(self, workflow: HumanApprovalWorkflow) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")

        success, msg = workflow.process_decision(
            token.token_hex,
            ApprovalDecision.REJECT,
            ip_address="203.0.113.1",
            reason="Data quality insufficient",
        )

        assert success is True
        assert token.decision == ApprovalDecision.REJECT
        assert token.decision_reason == "Data quality insufficient"

    def test_request_changes(self, workflow: HumanApprovalWorkflow) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")

        success, msg = workflow.process_decision(
            token.token_hex,
            ApprovalDecision.REQUEST_CHANGES,
            ip_address="203.0.113.1",
            reason="Need additional masking for SSN field",
        )

        assert success is True
        assert token.decision == ApprovalDecision.REQUEST_CHANGES
        assert "additional masking" in token.decision_reason


class TestTimeout:
    """Test timeout results in automatic rejection."""

    def test_timeout_auto_rejects(
        self, short_timeout_workflow: HumanApprovalWorkflow
    ) -> None:
        token = short_timeout_workflow.generate_token("pipe-001", "v1.0")
        time.sleep(0.2)

        timed_out = short_timeout_workflow.check_timeout(token.token_hex)

        assert timed_out is True
        assert token.decision == ApprovalDecision.TIMEOUT
        assert token.used is True
        assert "expired" in token.decision_reason.lower()

    def test_get_decision_auto_detects_timeout(
        self, short_timeout_workflow: HumanApprovalWorkflow
    ) -> None:
        """get_decision should auto-detect timeout."""
        token = short_timeout_workflow.generate_token("pipe-001", "v1.0")
        time.sleep(0.2)

        decision = short_timeout_workflow.get_decision(token.token_hex)
        assert decision == ApprovalDecision.TIMEOUT

    def test_non_expired_token_not_timed_out(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")
        timed_out = workflow.check_timeout(token.token_hex)
        assert timed_out is False
        assert token.decision == ApprovalDecision.PENDING


class TestAuditLogging:
    """Test that all approval actions are audited."""

    def test_approval_creates_audit_entry(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")
        workflow.process_decision(
            token.token_hex,
            ApprovalDecision.APPROVE,
            ip_address="203.0.113.100",
            user_agent="Mozilla/5.0",
        )

        audit = workflow.audit_log
        assert len(audit) >= 1

        entry = audit[-1]
        assert entry.token_id == token.token_id
        assert entry.ip_address == "203.0.113.100"
        assert entry.decision == "approve"
        assert entry.user_agent == "Mozilla/5.0"
        assert entry.timestamp > 0

    def test_rejection_creates_audit_entry(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        token = workflow.generate_token("pipe-001", "v1.0")
        workflow.process_decision(
            token.token_hex,
            ApprovalDecision.REJECT,
            ip_address="203.0.113.1",
            reason="Not ready",
        )

        audit = workflow.audit_log
        assert len(audit) >= 1
        assert audit[-1].decision == "reject"
        assert audit[-1].reason == "Not ready"

    def test_invalid_token_attempt_audited(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        """Even invalid token attempts should be audited."""
        workflow.process_decision(
            "nonexistent_token_hex",
            ApprovalDecision.APPROVE,
            ip_address="203.0.113.1",
        )

        audit = workflow.audit_log
        assert len(audit) >= 1
        # Should contain a rejection/failure record
        assert "REJECTED" in audit[-1].decision or "Token not found" in audit[-1].decision

    def test_timeout_audited(
        self, short_timeout_workflow: HumanApprovalWorkflow
    ) -> None:
        token = short_timeout_workflow.generate_token("pipe-001", "v1.0")
        time.sleep(0.2)

        short_timeout_workflow.check_timeout(token.token_hex)

        audit = short_timeout_workflow.audit_log
        assert len(audit) >= 1
        timeout_entry = next(
            (e for e in audit if e.decision == "timeout"), None
        )
        assert timeout_entry is not None
        assert timeout_entry.ip_address == "system"


class TestRequiresApproval:
    """Test the requires_approval check."""

    def test_data_mask_confidential_requires_approval(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        assert workflow.requires_approval("data_mask", "confidential") is True

    def test_data_load_restricted_requires_approval(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        assert workflow.requires_approval("data_load", "restricted") is True

    def test_data_extract_does_not_require_approval(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        assert workflow.requires_approval("data_extract", "confidential") is False

    def test_internal_data_does_not_require_approval(
        self, workflow: HumanApprovalWorkflow
    ) -> None:
        assert workflow.requires_approval("data_mask", "internal") is False
        assert workflow.requires_approval("data_load", "public") is False
