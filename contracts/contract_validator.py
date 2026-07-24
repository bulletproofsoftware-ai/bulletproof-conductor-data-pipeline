"""
Contract Validation Logic -- typed error returns for contract enforcement.

Returns structured errors:
- CONTRACT_REQUIRED: No contract exists for pipeline
- CONTRACT_INCOMPLETE: Contract doesn't cover all requested columns
- CONTRACT_TAMPERED: Hash mismatch (INTEGRITY_VIOLATION)
- CONTRACT_EXPIRED: Contract version predates latest schema change (stale)
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Error type constants
CONTRACT_REQUIRED = "CONTRACT_REQUIRED"
CONTRACT_INCOMPLETE = "CONTRACT_INCOMPLETE"
CONTRACT_TAMPERED = "CONTRACT_TAMPERED"
CONTRACT_EXPIRED = "CONTRACT_EXPIRED"

# Default stale threshold
DEFAULT_STALE_DAYS = 30


@dataclass
class ContractValidationError:
    """Typed contract validation error."""
    error_code: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ContractValidationResult:
    """Result of contract validation."""
    valid: bool
    errors: list[ContractValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ContractValidator:
    """
    Validates data contracts against pipelines, source schemas,
    and integrity hashes. All validation methods return typed errors.
    """

    def __init__(self, stale_days: int = DEFAULT_STALE_DAYS):
        """
        Args:
            stale_days: Number of days after which a contract is considered stale.
                        Default: 30.
        """
        self._stale_days = stale_days

    def validate_against_pipeline(
        self,
        contract: Optional[dict],
        pipeline: dict,
    ) -> ContractValidationResult:
        """
        Verify that a contract exists and covers all columns in the
        pipeline's extraction list.

        Args:
            contract: Data contract dict (or None if no contract exists).
            pipeline: Pipeline definition dict.

        Returns:
            ContractValidationResult with typed errors if invalid.
        """
        errors: list[ContractValidationError] = []
        warnings: list[str] = []

        # Check 1: Contract must exist
        if contract is None:
            errors.append(ContractValidationError(
                error_code=CONTRACT_REQUIRED,
                message="No data contract provided. Extraction requires a signed data contract.",
            ))
            return ContractValidationResult(valid=False, errors=errors)

        # Check 2: Contract covers all requested columns
        contract_columns = set(contract.get("columns", {}).keys())
        source = pipeline.get("source", {})
        tables = source.get("extraction", {}).get("tables", [])

        missing_columns: list[str] = []
        for table_spec in tables:
            table_name = table_spec.get("name", "")
            columns = table_spec.get("columns", [])
            for col in columns:
                qualified = f"{table_name}.{col}"
                if qualified not in contract_columns:
                    missing_columns.append(qualified)

        if missing_columns:
            errors.append(ContractValidationError(
                error_code=CONTRACT_INCOMPLETE,
                message=(
                    f"Contract does not cover {len(missing_columns)} pipeline column(s): "
                    f"{', '.join(missing_columns)}"
                ),
                details={"missing_columns": missing_columns},
            ))

        valid = len(errors) == 0
        return ContractValidationResult(valid=valid, errors=errors, warnings=warnings)

    def validate_against_schema(
        self,
        contract: dict,
        source_schema: dict[str, dict],
    ) -> ContractValidationResult:
        """
        Verify that contract columns exist in the source schema with
        matching types.

        Args:
            contract: Data contract dict.
            source_schema: Dict mapping qualified column names to
                           {"type": str, ...} dicts from the source.

        Returns:
            ContractValidationResult with typed errors if invalid.
        """
        errors: list[ContractValidationError] = []
        warnings: list[str] = []

        contract_columns = contract.get("columns", {})

        for col_name in contract_columns:
            if col_name not in source_schema:
                errors.append(ContractValidationError(
                    error_code=CONTRACT_INCOMPLETE,
                    message=f"Contract column '{col_name}' not found in source schema.",
                    details={"column": col_name},
                ))
            else:
                # Check type compatibility if source schema includes type info
                source_type = source_schema[col_name].get("type")
                contract_type = contract_columns[col_name].get("source_type")
                if source_type and contract_type and source_type != contract_type:
                    warnings.append(
                        f"Type mismatch for '{col_name}': contract={contract_type}, source={source_type}"
                    )

        valid = len(errors) == 0
        return ContractValidationResult(valid=valid, errors=errors, warnings=warnings)

    def validate_integrity(
        self,
        contract_raw_yaml: str,
        expected_hash: str,
    ) -> ContractValidationResult:
        """
        Verify that the contract YAML hash matches the expected hash
        stored in conductor-state.json.

        SHA-256 is computed on the raw YAML content, not the parsed dict.

        Args:
            contract_raw_yaml: Raw YAML content string.
            expected_hash: Expected hash from conductor-state.json
                           (with or without 'sha256:' prefix).

        Returns:
            ContractValidationResult with CONTRACT_TAMPERED error on mismatch.
        """
        actual_digest = hashlib.sha256(contract_raw_yaml.encode("utf-8")).hexdigest()
        actual_hash = f"sha256:{actual_digest}"

        # Normalize expected hash
        if not expected_hash.startswith("sha256:"):
            expected_normalized = f"sha256:{expected_hash}"
        else:
            expected_normalized = expected_hash

        if actual_hash != expected_normalized:
            return ContractValidationResult(
                valid=False,
                errors=[ContractValidationError(
                    error_code=CONTRACT_TAMPERED,
                    message="Contract integrity check failed. YAML content hash does not match stored hash.",
                    details={
                        "actual_hash": actual_hash,
                        "expected_hash": expected_normalized,
                    },
                )],
            )

        return ContractValidationResult(valid=True)

    def validate_freshness(
        self,
        contract: dict,
        reference_time: Optional[datetime] = None,
    ) -> ContractValidationResult:
        """
        Verify that a contract is not stale (review date within threshold).

        Args:
            contract: Data contract dict with metadata.reviewed_at.
            reference_time: Time to compare against. Defaults to now (UTC).

        Returns:
            ContractValidationResult with CONTRACT_EXPIRED error if stale.
        """
        reviewed_at_str = contract.get("metadata", {}).get("reviewed_at", "")
        if not reviewed_at_str:
            return ContractValidationResult(
                valid=False,
                errors=[ContractValidationError(
                    error_code=CONTRACT_EXPIRED,
                    message="Contract has no reviewed_at timestamp.",
                )],
            )

        try:
            reviewed_at = datetime.fromisoformat(reviewed_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return ContractValidationResult(
                valid=False,
                errors=[ContractValidationError(
                    error_code=CONTRACT_EXPIRED,
                    message=f"Cannot parse reviewed_at timestamp: {reviewed_at_str}",
                )],
            )

        now = reference_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        age = now - reviewed_at
        threshold = timedelta(days=self._stale_days)

        if age > threshold:
            return ContractValidationResult(
                valid=False,
                errors=[ContractValidationError(
                    error_code=CONTRACT_EXPIRED,
                    message=(
                        f"Contract review is stale. Reviewed {age.days} days ago "
                        f"(threshold: {self._stale_days} days). Re-review required."
                    ),
                    details={
                        "reviewed_at": reviewed_at_str,
                        "age_days": age.days,
                        "threshold_days": self._stale_days,
                    },
                )],
            )

        return ContractValidationResult(valid=True)
