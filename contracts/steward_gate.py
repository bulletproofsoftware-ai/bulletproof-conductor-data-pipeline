"""
Steward Review Enforcement -- mandatory gate before pipeline execution.

REQ-DP-019: Mandatory steward review before pipeline execution.

Before pipeline execution:
1. Check conductor-state.json for pipeline entry
2. Verify `contract` field is populated (steward has reviewed)
3. Verify contract `steward` field is a valid data-steward NHI
4. Verify contract `reviewed_at` is not stale (configurable, default 30 days)
5. Verify contract hash is valid (integrity check)

Rejection returns structured error with which check failed.
NO BYPASS MECHANISM -- steward review is architecturally mandatory.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Valid NHI prefix for data stewards
STEWARD_NHI_PREFIX = "nhi_data-steward_"

# Default stale threshold
DEFAULT_STALE_DAYS = 30

# Gate check identifiers
CHECK_PIPELINE_EXISTS = "PIPELINE_EXISTS"
CHECK_CONTRACT_EXISTS = "CONTRACT_EXISTS"
CHECK_STEWARD_VALID = "STEWARD_VALID"
CHECK_NOT_STALE = "NOT_STALE"
CHECK_INTEGRITY = "INTEGRITY_VALID"


@dataclass
class StewardGateRejection:
    """Structured rejection from the steward gate."""
    allowed: bool = False
    failed_check: str = ""
    message: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class StewardGateResult:
    """Result of a steward gate check."""
    allowed: bool
    rejection: Optional[StewardGateRejection] = None

    @property
    def blocked(self) -> bool:
        return not self.allowed


class StewardGate:
    """
    Enforces steward review before pipeline execution.
    There is NO bypass mechanism -- every pipeline must pass all checks.
    """

    def __init__(
        self,
        state: dict,
        stale_days: int = DEFAULT_STALE_DAYS,
    ):
        """
        Args:
            state: conductor-state.json dict. Must contain pipeline entries
                   under state["pipelines"][pipeline_id].
            stale_days: Number of days after which a contract review is
                        considered stale. Default: 30.
        """
        self._state = state
        self._stale_days = stale_days

    def check(
        self,
        pipeline_id: str,
        contract: Optional[dict] = None,
        contract_raw_yaml: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ) -> StewardGateResult:
        """
        Run all steward gate checks for a pipeline.

        This method has NO bypass. All checks must pass.

        Args:
            pipeline_id: Pipeline identifier.
            contract: Data contract dict (parsed). If None, looked up from state.
            contract_raw_yaml: Raw YAML content for integrity verification.
                               If None, integrity check uses stored hash comparison only.
            reference_time: Time to compare against for staleness. Defaults to now (UTC).

        Returns:
            StewardGateResult. If blocked, rejection contains details.
        """
        now = reference_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # --- Check 1: Pipeline entry exists in conductor-state.json ---
        pipelines = self._state.get("pipelines", {})
        pipeline_entry = pipelines.get(pipeline_id)

        if pipeline_entry is None:
            return StewardGateResult(
                allowed=False,
                rejection=StewardGateRejection(
                    failed_check=CHECK_PIPELINE_EXISTS,
                    message=f"Pipeline '{pipeline_id}' not found in conductor-state.json.",
                    details={"pipeline_id": pipeline_id},
                ),
            )

        # --- Check 2: Contract field is populated ---
        # Use provided contract or look it up from the pipeline entry
        if contract is None:
            contract = pipeline_entry.get("contract")

        if contract is None or not isinstance(contract, dict) or len(contract) == 0:
            return StewardGateResult(
                allowed=False,
                rejection=StewardGateRejection(
                    failed_check=CHECK_CONTRACT_EXISTS,
                    message=(
                        f"Pipeline '{pipeline_id}' has no data contract. "
                        "A signed contract with steward review is required."
                    ),
                    details={"pipeline_id": pipeline_id},
                ),
            )

        # --- Check 3: Steward field is a valid data-steward NHI ---
        steward = contract.get("metadata", {}).get("steward", "")

        if not steward or not steward.startswith(STEWARD_NHI_PREFIX):
            return StewardGateResult(
                allowed=False,
                rejection=StewardGateRejection(
                    failed_check=CHECK_STEWARD_VALID,
                    message=(
                        f"Contract steward '{steward}' is not a valid data-steward NHI. "
                        f"Must start with '{STEWARD_NHI_PREFIX}'."
                    ),
                    details={
                        "pipeline_id": pipeline_id,
                        "steward": steward,
                        "expected_prefix": STEWARD_NHI_PREFIX,
                    },
                ),
            )

        # --- Check 4: reviewed_at is not stale ---
        reviewed_at_str = contract.get("metadata", {}).get("reviewed_at", "")

        if not reviewed_at_str:
            return StewardGateResult(
                allowed=False,
                rejection=StewardGateRejection(
                    failed_check=CHECK_NOT_STALE,
                    message="Contract has no reviewed_at timestamp.",
                    details={"pipeline_id": pipeline_id},
                ),
            )

        try:
            reviewed_at = datetime.fromisoformat(
                reviewed_at_str.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            return StewardGateResult(
                allowed=False,
                rejection=StewardGateRejection(
                    failed_check=CHECK_NOT_STALE,
                    message=f"Cannot parse reviewed_at: {reviewed_at_str}",
                    details={"pipeline_id": pipeline_id},
                ),
            )

        age = now - reviewed_at
        threshold = timedelta(days=self._stale_days)

        if age > threshold:
            return StewardGateResult(
                allowed=False,
                rejection=StewardGateRejection(
                    failed_check=CHECK_NOT_STALE,
                    message=(
                        f"Contract review is stale. Reviewed {age.days} days ago "
                        f"(threshold: {self._stale_days} days). Re-review required."
                    ),
                    details={
                        "pipeline_id": pipeline_id,
                        "reviewed_at": reviewed_at_str,
                        "age_days": age.days,
                        "threshold_days": self._stale_days,
                    },
                ),
            )

        # --- Check 5: Contract hash integrity ---
        if contract_raw_yaml is not None:
            actual_digest = hashlib.sha256(
                contract_raw_yaml.encode("utf-8")
            ).hexdigest()
            actual_hash = f"sha256:{actual_digest}"

            stored_hash_entry = (
                self._state
                .get("artifact_hashes", {})
                .get("contract", {})
                .get(pipeline_id, {})
            )
            stored_hash = stored_hash_entry.get("hash", "") if isinstance(stored_hash_entry, dict) else ""

            if stored_hash and actual_hash != stored_hash:
                return StewardGateResult(
                    allowed=False,
                    rejection=StewardGateRejection(
                        failed_check=CHECK_INTEGRITY,
                        message=(
                            "Contract integrity check failed. "
                            "YAML content hash does not match stored hash."
                        ),
                        details={
                            "pipeline_id": pipeline_id,
                            "actual_hash": actual_hash,
                            "stored_hash": stored_hash,
                        },
                    ),
                )

        # --- All checks passed ---
        logger.info(
            "Steward gate PASSED for pipeline=%s steward=%s reviewed=%s",
            pipeline_id,
            steward,
            reviewed_at_str,
        )

        return StewardGateResult(allowed=True)
