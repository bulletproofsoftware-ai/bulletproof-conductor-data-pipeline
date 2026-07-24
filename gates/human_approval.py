"""Human approval workflow for Confidential+ data operations.

Generates 256-bit cryptographically random approval tokens (single-use,
time-limited), manages approval payloads, and processes approve/reject/
request-changes decisions. Tokens are bound to pipeline_execution_id +
contract_version and expire after a configurable timeout (default 24hr).

All access is audited: IP, timestamp, token ID, decision.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default timeout: 24 hours in seconds
DEFAULT_TIMEOUT_SECONDS = 24 * 60 * 60

# Classifications that require human approval
APPROVAL_REQUIRED_CLASSIFICATIONS = {"confidential", "restricted"}

# Operations that require human approval when processing sensitive data
APPROVAL_REQUIRED_OPERATIONS = {"data_mask", "data_load"}


class ApprovalDecision(str, Enum):
    """Possible human approval decisions."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    TIMEOUT = "timeout"
    PENDING = "pending"


@dataclass
class ApprovalAuditEntry:
    """Audit record for approval endpoint access."""
    token_id: str
    timestamp: float
    ip_address: str
    decision: str
    reason: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "timestamp": self.timestamp,
            "ip_address": self.ip_address,
            "decision": self.decision,
            "reason": self.reason,
            "user_agent": self.user_agent,
        }


@dataclass
class ApprovalPayload:
    """Information presented to the human reviewer."""
    pipeline_id: str
    source_description: str
    target_tier: str
    row_count: int
    column_classifications: dict[str, str]
    strategy_map: dict[str, str]
    sample_rows: list[dict[str, Any]]
    risk_assessment: dict[str, int]
    contract_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "source_description": self.source_description,
            "target_tier": self.target_tier,
            "row_count": self.row_count,
            "column_classifications": self.column_classifications,
            "strategy_map": self.strategy_map,
            "sample_rows": self.sample_rows,
            "risk_assessment": self.risk_assessment,
            "contract_version": self.contract_version,
        }


@dataclass
class ApprovalToken:
    """A cryptographically random approval token bound to a pipeline execution."""
    token_hex: str  # 256-bit hex string (64 chars)
    token_id: str   # Short identifier (first 16 chars of hash)
    pipeline_execution_id: str
    contract_version: str
    created_at: float
    expires_at: float
    used: bool = False
    decision: ApprovalDecision = ApprovalDecision.PENDING
    decision_reason: Optional[str] = None
    decision_timestamp: Optional[float] = None
    payload: Optional[ApprovalPayload] = None

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired based on current time."""
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.used and not self.is_expired

    def to_dict(self) -> dict[str, Any]:
        result = {
            "token_id": self.token_id,
            "pipeline_execution_id": self.pipeline_execution_id,
            "contract_version": self.contract_version,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "used": self.used,
            "decision": self.decision.value,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
        }
        if self.decision_reason:
            result["decision_reason"] = self.decision_reason
        if self.decision_timestamp:
            result["decision_timestamp"] = self.decision_timestamp
        return result


class HumanApprovalWorkflow:
    """Manages human approval tokens and decisions for sensitive data operations.

    Tokens are 256-bit cryptographically random (secrets.token_hex(32)),
    single-use, and time-limited. Each token is bound to a specific
    pipeline_execution_id + contract_version pair.
    """

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        notification_webhook: Optional[str] = None,
    ):
        """Initialize the approval workflow.

        Args:
            timeout_seconds: Token expiration time in seconds (default 24hr).
            notification_webhook: Optional webhook URL for approval notifications.
        """
        self._timeout_seconds = timeout_seconds
        self._notification_webhook = notification_webhook
        self._tokens: dict[str, ApprovalToken] = {}  # token_hex -> ApprovalToken
        self._audit_log: list[ApprovalAuditEntry] = []

    @property
    def audit_log(self) -> list[ApprovalAuditEntry]:
        """Return a copy of the audit log."""
        return list(self._audit_log)

    @property
    def pending_tokens(self) -> list[ApprovalToken]:
        """Return all pending (not used, not expired) tokens."""
        return [t for t in self._tokens.values() if t.is_valid]

    def requires_approval(
        self,
        operation: str,
        data_classification: str,
    ) -> bool:
        """Check if an operation requires human approval.

        Approval is required when:
        - Operation is data_mask or data_load
        - Data classification is Confidential or Restricted

        Args:
            operation: The operation being performed.
            data_classification: The highest classification in the dataset.

        Returns:
            True if human approval is required.
        """
        return (
            operation.lower() in APPROVAL_REQUIRED_OPERATIONS
            and data_classification.lower() in APPROVAL_REQUIRED_CLASSIFICATIONS
        )

    def generate_token(
        self,
        pipeline_execution_id: str,
        contract_version: str,
        payload: Optional[ApprovalPayload] = None,
    ) -> ApprovalToken:
        """Generate a new 256-bit cryptographically random approval token.

        Args:
            pipeline_execution_id: The pipeline execution this token is for.
            contract_version: The contract version this token is bound to.
            payload: Optional approval payload for the reviewer.

        Returns:
            The generated ApprovalToken.
        """
        # Generate 256-bit random token (32 bytes = 64 hex chars)
        token_hex = secrets.token_hex(32)

        # Create a short token ID from SHA-256 of the token
        token_id = hashlib.sha256(token_hex.encode()).hexdigest()[:16]

        now = time.time()
        token = ApprovalToken(
            token_hex=token_hex,
            token_id=token_id,
            pipeline_execution_id=pipeline_execution_id,
            contract_version=contract_version,
            created_at=now,
            expires_at=now + self._timeout_seconds,
            payload=payload,
        )

        self._tokens[token_hex] = token
        logger.info(
            "Generated approval token %s for pipeline=%s contract=%s (expires in %ds)",
            token_id,
            pipeline_execution_id,
            contract_version,
            self._timeout_seconds,
        )
        return token

    def validate_token(self, token_hex: str) -> tuple[bool, str]:
        """Validate an approval token.

        Args:
            token_hex: The token hex string to validate.

        Returns:
            Tuple of (is_valid, reason_if_invalid).
        """
        token = self._tokens.get(token_hex)
        if token is None:
            return False, "Token not found"
        if token.used:
            return False, "Token already used (single-use)"
        if token.is_expired:
            return False, "Token expired"
        return True, "Valid"

    def process_decision(
        self,
        token_hex: str,
        decision: ApprovalDecision,
        ip_address: str = "127.0.0.1",
        reason: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Process a human approval decision.

        Marks the token as used (single-use enforcement) and records the
        decision. Creates an audit log entry.

        Args:
            token_hex: The approval token.
            decision: The decision (approve/reject/request_changes).
            ip_address: IP address of the reviewer.
            reason: Optional reason (required for reject/request_changes).
            user_agent: Optional user agent string.

        Returns:
            Tuple of (success, message).
        """
        # Validate the token first
        is_valid, validation_msg = self.validate_token(token_hex)
        if not is_valid:
            # Still audit the attempt
            token = self._tokens.get(token_hex)
            token_id = token.token_id if token else "unknown"
            self._record_audit(
                token_id=token_id,
                ip_address=ip_address,
                decision=f"REJECTED:{validation_msg}",
                reason=reason,
                user_agent=user_agent,
            )
            return False, validation_msg

        token = self._tokens[token_hex]

        # Mark as used (single-use)
        token.used = True
        token.decision = decision
        token.decision_reason = reason
        token.decision_timestamp = time.time()

        # Audit the decision
        self._record_audit(
            token_id=token.token_id,
            ip_address=ip_address,
            decision=decision.value,
            reason=reason,
            user_agent=user_agent,
        )

        logger.info(
            "Approval decision for token %s: %s (pipeline=%s)",
            token.token_id,
            decision.value,
            token.pipeline_execution_id,
        )

        return True, f"Decision recorded: {decision.value}"

    def check_timeout(self, token_hex: str) -> bool:
        """Check if a token has timed out and auto-reject if so.

        Args:
            token_hex: The token to check.

        Returns:
            True if the token timed out (and was auto-rejected).
        """
        token = self._tokens.get(token_hex)
        if token is None:
            return False
        if token.used:
            return False
        if token.is_expired:
            # Auto-reject on timeout
            token.used = True
            token.decision = ApprovalDecision.TIMEOUT
            token.decision_reason = "Automatic rejection: token expired"
            token.decision_timestamp = time.time()

            self._record_audit(
                token_id=token.token_id,
                ip_address="system",
                decision="timeout",
                reason="Automatic rejection: token expired",
            )

            logger.warning(
                "Token %s timed out -- automatic rejection for pipeline=%s",
                token.token_id,
                token.pipeline_execution_id,
            )
            return True
        return False

    def get_token(self, token_hex: str) -> Optional[ApprovalToken]:
        """Retrieve a token by its hex value."""
        return self._tokens.get(token_hex)

    def get_decision(self, token_hex: str) -> Optional[ApprovalDecision]:
        """Get the decision for a token, handling timeout auto-rejection.

        Args:
            token_hex: The token to check.

        Returns:
            The ApprovalDecision, or None if token not found.
        """
        token = self._tokens.get(token_hex)
        if token is None:
            return None

        # Check for timeout auto-rejection
        if not token.used and token.is_expired:
            self.check_timeout(token_hex)

        return token.decision

    def build_payload(
        self,
        pipeline_id: str,
        source_description: str,
        target_tier: str,
        row_count: int,
        column_classifications: dict[str, str],
        strategy_map: dict[str, str],
        masked_dataset: dict[str, list[dict[str, Any]]],
        contract_version: str,
        sample_size: int = 5,
    ) -> ApprovalPayload:
        """Build the approval payload presented to the human reviewer.

        Args:
            pipeline_id: Pipeline identifier.
            source_description: Description of the data source.
            target_tier: Target environment tier.
            row_count: Total number of rows in the dataset.
            column_classifications: {col: classification} map.
            strategy_map: {col: strategy} map.
            masked_dataset: The masked dataset for sampling.
            contract_version: Data contract version.
            sample_size: Number of rows to include in sample (default 5).

        Returns:
            ApprovalPayload for the reviewer.
        """
        # Sample rows from the first table
        sample_rows: list[dict[str, Any]] = []
        for table_name, rows in masked_dataset.items():
            if rows:
                sample_rows = rows[:sample_size]
                break

        # Build risk assessment
        restricted_count = sum(
            1 for c in column_classifications.values()
            if c.lower() == "restricted"
        )
        confidential_count = sum(
            1 for c in column_classifications.values()
            if c.lower() == "confidential"
        )

        risk_assessment = {
            "restricted_columns": restricted_count,
            "confidential_columns": confidential_count,
            "total_sensitive_columns": restricted_count + confidential_count,
        }

        return ApprovalPayload(
            pipeline_id=pipeline_id,
            source_description=source_description,
            target_tier=target_tier,
            row_count=row_count,
            column_classifications=column_classifications,
            strategy_map=strategy_map,
            sample_rows=sample_rows,
            risk_assessment=risk_assessment,
            contract_version=contract_version,
        )

    def _record_audit(
        self,
        token_id: str,
        ip_address: str,
        decision: str,
        reason: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Record an audit log entry."""
        entry = ApprovalAuditEntry(
            token_id=token_id,
            timestamp=time.time(),
            ip_address=ip_address,
            decision=decision,
            reason=reason,
            user_agent=user_agent,
        )
        self._audit_log.append(entry)
        logger.info(
            "AUDIT: token=%s ip=%s decision=%s",
            token_id,
            ip_address,
            decision,
        )
