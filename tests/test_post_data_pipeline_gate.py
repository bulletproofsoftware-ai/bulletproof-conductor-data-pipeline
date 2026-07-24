"""Tests for the POST-DATA-PIPELINE quality gate.

Covers all 6 validation checks with pass and fail scenarios:
1. Contract coverage
2. Quality assertions
3. Masking correctness (via PII validator)
4. Lineage completeness
5. Restricted data check
6. Referential integrity
"""

import pytest

from gates.post_data_pipeline import (
    PostDataPipelineGate,
    PipelineContext,
    CHECK_1_CONTRACT,
    CHECK_2_QUALITY,
    CHECK_3_MASKING,
    CHECK_4_LINEAGE,
    CHECK_5_RESTRICTED,
    CHECK_6_INTEGRITY,
)
from gates.pii_validator import PIIValidator
from masking_engine.app.ner.presidio_client import MockPresidioClient


def _make_passing_context() -> PipelineContext:
    """Build a PipelineContext that will pass all 6 checks."""
    return PipelineContext(
        pipeline_id="test-pipeline-001",
        target_tier="staging",
        # CHECK 1: Contract covers all columns
        contract={
            "columns": {
                "customers.name": {"classification": "confidential"},
                "customers.email": {"classification": "confidential"},
                "customers.id": {"classification": "internal"},
            }
        },
        extracted_columns=["customers.name", "customers.email", "customers.id"],
        # CHECK 2: All assertions pass
        quality_results={
            "assertions_run": 3,
            "assertions_passed": 3,
            "assertions_failed": 0,
            "phase": "post_mask",
        },
        # CHECK 3: Masked dataset with no PII leaks
        masked_dataset={
            "customers": [
                {"name": "NAME_a1b2c3", "email": "EMAIL_x9y8z7", "id": 1},
                {"name": "NAME_d4e5f6", "email": "EMAIL_w6v5u4", "id": 2},
            ]
        },
        classifications={
            "customers.name": "confidential",
            "customers.email": "confidential",
            "customers.id": "internal",
        },
        strategy_map={
            "customers.name": "tokenize",
            "customers.email": "tokenize",
            "customers.id": "passthrough",
        },
        # CHECK 4: All lineage events emitted
        expected_lineage_operations=["extract", "transform", "mask"],
        emitted_lineage_events=[
            {"operation": "extract", "pipeline_id": "test-pipeline-001"},
            {"operation": "transform", "pipeline_id": "test-pipeline-001"},
            {"operation": "mask", "pipeline_id": "test-pipeline-001"},
        ],
        # CHECK 5: Restricted data check (no restricted columns in this test)
        # (classifications above have no restricted columns)
        # CHECK 6: Integrity passes
        integrity_report={
            "checked": 1,
            "passed": 1,
            "failed": 0,
            "results": [
                {
                    "left_table": "customers",
                    "left_column": "id",
                    "right_table": "orders",
                    "right_column": "customer_id",
                    "passed": True,
                    "detail": "All FK values found",
                }
            ],
        },
    )


@pytest.fixture
def pii_validator() -> PIIValidator:
    """PIIValidator with mock Presidio client."""
    client = MockPresidioClient()
    return PIIValidator(presidio_client=client, sample_size=100)


@pytest.fixture
def gate(pii_validator: PIIValidator) -> PostDataPipelineGate:
    """Gate instance with PII validator."""
    return PostDataPipelineGate(pii_validator=pii_validator)


class TestAllChecksPassing:
    """Test that all 6 checks pass returns a PASS verdict."""

    def test_all_checks_pass(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        result = gate.evaluate(ctx)

        assert result.verdict == "PASS"
        assert result.passed is True
        assert result.checks_run == 6
        assert result.checks_passed == 6
        assert result.checks_failed == 0
        assert result.failed_checks == []
        assert result.mode == "blocking"

    def test_gate_result_has_all_check_names(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        result = gate.evaluate(ctx)

        check_names = {cr.check_name for cr in result.check_results}
        assert CHECK_1_CONTRACT in check_names
        assert CHECK_2_QUALITY in check_names
        assert CHECK_3_MASKING in check_names
        assert CHECK_4_LINEAGE in check_names
        assert CHECK_5_RESTRICTED in check_names
        assert CHECK_6_INTEGRITY in check_names


class TestCheck1ContractCoverage:
    """CHECK 1: Contract coverage validation."""

    def test_no_contract_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.contract = None
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert CHECK_1_CONTRACT in result.failed_checks
        check = next(cr for cr in result.check_results if cr.check_name == CHECK_1_CONTRACT)
        assert not check.passed
        assert "No data contract" in check.detail

    def test_uncovered_columns_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.extracted_columns = [
            "customers.name", "customers.email", "customers.id", "customers.ssn"
        ]
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert CHECK_1_CONTRACT in result.failed_checks
        check = next(cr for cr in result.check_results if cr.check_name == CHECK_1_CONTRACT)
        assert not check.passed
        assert "not covered" in check.detail

    def test_contract_with_list_format(self, gate: PostDataPipelineGate) -> None:
        """Contract columns as list of dicts also works."""
        ctx = _make_passing_context()
        ctx.contract = {
            "columns": [
                {"name": "customers.name"},
                {"name": "customers.email"},
                {"name": "customers.id"},
            ]
        }
        result = gate.evaluate(ctx)
        check = next(cr for cr in result.check_results if cr.check_name == CHECK_1_CONTRACT)
        assert check.passed


class TestCheck2QualityAssertions:
    """CHECK 2: Quality assertion validation."""

    def test_failed_assertions_fails_gate(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.quality_results = {
            "assertions_run": 5,
            "assertions_passed": 3,
            "assertions_failed": 2,
        }
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert CHECK_2_QUALITY in result.failed_checks
        check = next(cr for cr in result.check_results if cr.check_name == CHECK_2_QUALITY)
        assert not check.passed
        assert "2 of 5" in check.detail

    def test_no_quality_results_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.quality_results = None
        result = gate.evaluate(ctx)

        assert CHECK_2_QUALITY in result.failed_checks

    def test_zero_assertions_run_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.quality_results = {
            "assertions_run": 0,
            "assertions_passed": 0,
            "assertions_failed": 0,
        }
        result = gate.evaluate(ctx)

        check = next(cr for cr in result.check_results if cr.check_name == CHECK_2_QUALITY)
        assert not check.passed


class TestCheck3MaskingCorrectness:
    """CHECK 3: Masking correctness via PII validation."""

    def test_unmasked_pii_fails_gate(self, gate: PostDataPipelineGate) -> None:
        """Real PII (known name) in a confidential column should fail."""
        ctx = _make_passing_context()
        ctx.masked_dataset = {
            "customers": [
                {"name": "John Doe", "email": "EMAIL_x9y8z7", "id": 1},
                {"name": "NAME_d4e5f6", "email": "EMAIL_w6v5u4", "id": 2},
            ]
        }
        ctx.strategy_map = {
            "customers.name": "tokenize",
            "customers.email": "tokenize",
            "customers.id": "passthrough",
        }
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert CHECK_3_MASKING in result.failed_checks

    def test_no_pii_validator_fails(self) -> None:
        """Gate without PII validator should fail CHECK 3."""
        gate = PostDataPipelineGate(pii_validator=None)
        ctx = _make_passing_context()
        result = gate.evaluate(ctx)

        check = next(cr for cr in result.check_results if cr.check_name == CHECK_3_MASKING)
        assert not check.passed
        assert "not configured" in check.detail

    def test_no_masked_dataset_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.masked_dataset = None
        result = gate.evaluate(ctx)

        check = next(cr for cr in result.check_results if cr.check_name == CHECK_3_MASKING)
        assert not check.passed


class TestCheck4LineageCompleteness:
    """CHECK 4: Lineage completeness validation."""

    def test_missing_lineage_event_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        # Missing the "mask" event
        ctx.emitted_lineage_events = [
            {"operation": "extract"},
            {"operation": "transform"},
        ]
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert CHECK_4_LINEAGE in result.failed_checks
        check = next(cr for cr in result.check_results if cr.check_name == CHECK_4_LINEAGE)
        assert "missing" in check.detail.lower()
        assert "mask" in check.metadata.get("missing_operations", [])

    def test_no_lineage_events_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.emitted_lineage_events = None
        result = gate.evaluate(ctx)

        assert CHECK_4_LINEAGE in result.failed_checks

    def test_lineage_with_nested_event_structure(self, gate: PostDataPipelineGate) -> None:
        """Events with nested 'event' key should also work."""
        ctx = _make_passing_context()
        ctx.emitted_lineage_events = [
            {"event": {"operation": "extract"}},
            {"event": {"operation": "transform"}},
            {"event": {"operation": "mask"}},
        ]
        result = gate.evaluate(ctx)

        check = next(cr for cr in result.check_results if cr.check_name == CHECK_4_LINEAGE)
        assert check.passed


class TestCheck5RestrictedData:
    """CHECK 5: Restricted data in non-production targets."""

    def test_restricted_data_in_non_prod_fails(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.target_tier = "staging"
        ctx.classifications = {
            "customers.name": "confidential",
            "customers.ssn": "restricted",
            "customers.id": "internal",
        }
        ctx.masked_dataset = {
            "customers": [
                {"name": "NAME_a1b2c3", "ssn": "123-45-6789", "id": 1},  # SSN not masked!
            ]
        }
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert CHECK_5_RESTRICTED in result.failed_checks

    def test_production_target_exempt(self, gate: PostDataPipelineGate) -> None:
        """Production targets skip the restricted data check."""
        ctx = _make_passing_context()
        ctx.target_tier = "production"
        ctx.classifications = {
            "customers.ssn": "restricted",
        }
        ctx.masked_dataset = {
            "customers": [
                {"ssn": "123-45-6789"},
            ]
        }
        result = gate.evaluate(ctx)

        check = next(cr for cr in result.check_results if cr.check_name == CHECK_5_RESTRICTED)
        assert check.passed

    def test_properly_masked_restricted_passes(self, gate: PostDataPipelineGate) -> None:
        """Restricted data that is properly masked (redacted/tokenized) should pass."""
        ctx = _make_passing_context()
        ctx.target_tier = "staging"
        ctx.classifications = {
            "customers.name": "confidential",
            "customers.ssn": "restricted",
            "customers.id": "internal",
        }
        ctx.masked_dataset = {
            "customers": [
                {"name": "NAME_a1b2c3", "ssn": "[REDACTED]", "id": 1},
                {"name": "NAME_d4e5f6", "ssn": None, "id": 2},
            ]
        }
        result = gate.evaluate(ctx)

        check = next(cr for cr in result.check_results if cr.check_name == CHECK_5_RESTRICTED)
        assert check.passed


class TestCheck6ReferentialIntegrity:
    """CHECK 6: FK relationships preserved."""

    def test_broken_fk_fails_gate(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        ctx.integrity_report = {
            "checked": 2,
            "passed": 1,
            "failed": 1,
            "results": [
                {"passed": True, "detail": "OK"},
                {
                    "passed": False,
                    "detail": "3 FK values in orders.customer_id not found in customers.id",
                },
            ],
        }
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert CHECK_6_INTEGRITY in result.failed_checks

    def test_no_fk_relationships_passes(self, gate: PostDataPipelineGate) -> None:
        """No integrity report means no FKs to check -- trivial pass."""
        ctx = _make_passing_context()
        ctx.integrity_report = None
        result = gate.evaluate(ctx)

        check = next(cr for cr in result.check_results if cr.check_name == CHECK_6_INTEGRITY)
        assert check.passed


class TestGateIsBlocking:
    """Verify the gate is BLOCKING -- cannot progress on failure."""

    def test_gate_mode_is_blocking(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        result = gate.evaluate(ctx)
        assert result.mode == "blocking"

    def test_single_check_failure_blocks(self, gate: PostDataPipelineGate) -> None:
        """Even one check failing should result in overall FAIL."""
        ctx = _make_passing_context()
        ctx.contract = None  # Fail only CHECK 1
        result = gate.evaluate(ctx)

        assert result.verdict == "FAIL"
        assert result.checks_failed >= 1
        assert not result.passed


class TestGateResultSerialization:
    """Test GateResult to_dict serialization."""

    def test_to_dict_contains_all_fields(self, gate: PostDataPipelineGate) -> None:
        ctx = _make_passing_context()
        result = gate.evaluate(ctx)
        d = result.to_dict()

        assert "gate_name" in d
        assert "verdict" in d
        assert "mode" in d
        assert "checks_run" in d
        assert "checks_passed" in d
        assert "checks_failed" in d
        assert "check_results" in d
        assert "execution_time_ms" in d
        assert "failed_checks" in d
        assert isinstance(d["check_results"], list)
        assert len(d["check_results"]) == 6
