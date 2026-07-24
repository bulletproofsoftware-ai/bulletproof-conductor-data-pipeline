"""
Schema Drift Detector -- Compare source schema to data contract (Section 12.10).

REQ-DP-040: Schema drift detection (missing/changed columns fail pipeline).

Detection rules:
- New column in source, not in contract: Warning logged, column NOT extracted
- Column in contract, missing from source: SCHEMA_DRIFT error, pipeline fails
- Type change (e.g., VARCHAR->INTEGER): SCHEMA_DRIFT error, pipeline fails

On SCHEMA_DRIFT: data-engineer must update pipeline definition + request new contract.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Error code
SCHEMA_DRIFT = "SCHEMA_DRIFT"


@dataclass
class ColumnDrift:
    """Describes a single column-level drift."""
    column: str
    drift_type: str  # "added", "removed", "type_changed"
    detail: str
    source_type: Optional[str] = None
    contract_type: Optional[str] = None


@dataclass
class DriftReport:
    """Full drift report comparing source schema to contract."""
    has_drift: bool
    added_columns: list[ColumnDrift] = field(default_factory=list)
    removed_columns: list[ColumnDrift] = field(default_factory=list)
    type_changes: list[ColumnDrift] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_breaking_drift(self) -> bool:
        """Return True if there are breaking changes (removed columns or type changes)."""
        return len(self.removed_columns) > 0 or len(self.type_changes) > 0

    def safe_columns(self, contract_columns: list[str]) -> list[str]:
        """Return column names that are safe to extract.

        Safe = present in both contract and source with no type change.
        Callers pass the full contract column list; this method subtracts
        removed, type-changed, and added (source-only) columns.

        Args:
            contract_columns: All column names defined in the data contract.

        Returns:
            Sorted list of column names safe to extract.
        """
        removed_names = {d.column for d in self.removed_columns}
        changed_names = {d.column for d in self.type_changes}
        added_names = {d.column for d in self.added_columns}
        unsafe = removed_names | changed_names | added_names
        return sorted(c for c in contract_columns if c not in unsafe)


class SchemaDriftDetector:
    """
    Compares a source schema (from connector catalog) against the
    data contract's column list to detect drift.
    """

    def detect(
        self,
        source_schema: dict[str, dict],
        contract_columns: dict[str, dict],
        table_name: Optional[str] = None,
    ) -> DriftReport:
        """
        Compare source schema columns to contract columns and produce a drift report.

        Args:
            source_schema: Dict mapping column names to metadata dicts.
                           Each value must have at least {"type": str}.
                           Column names may be qualified (table.col) or unqualified.
            contract_columns: Dict mapping column names to contract definitions.
                              Column names should match the format used in source_schema.
                              Each value may have {"source_type": str} for type comparison.
            table_name: Optional table name for log messages.

        Returns:
            DriftReport with added, removed, and type-changed columns.
        """
        source_names = set(source_schema.keys())
        contract_names = set(contract_columns.keys())

        added: list[ColumnDrift] = []
        removed: list[ColumnDrift] = []
        type_changes: list[ColumnDrift] = []
        errors: list[dict] = []
        warnings: list[str] = []

        prefix = f"table '{table_name}'" if table_name else "source"

        # --- New columns in source, not in contract ---
        new_in_source = source_names - contract_names
        for col in sorted(new_in_source):
            drift = ColumnDrift(
                column=col,
                drift_type="added",
                detail=f"Column '{col}' exists in {prefix} but not in contract. Will NOT be extracted.",
                source_type=source_schema[col].get("type"),
            )
            added.append(drift)
            msg = f"SCHEMA_DRIFT_WARNING: {drift.detail}"
            warnings.append(msg)
            logger.warning(msg)

        # --- Columns in contract, missing from source ---
        missing_from_source = contract_names - source_names
        for col in sorted(missing_from_source):
            drift = ColumnDrift(
                column=col,
                drift_type="removed",
                detail=f"Column '{col}' in contract is missing from {prefix}. Pipeline MUST fail.",
                contract_type=contract_columns[col].get("source_type"),
            )
            removed.append(drift)
            error = {
                "error_code": SCHEMA_DRIFT,
                "message": drift.detail,
                "column": col,
            }
            errors.append(error)
            logger.error("SCHEMA_DRIFT: %s", drift.detail)

        # --- Type changes for columns present in both ---
        common = source_names & contract_names
        for col in sorted(common):
            source_type = source_schema[col].get("type")
            contract_type = contract_columns[col].get("source_type")

            # Only flag if both have type info and they differ (case-insensitive, G9 fix)
            if source_type and contract_type and source_type.lower() != contract_type.lower():
                drift = ColumnDrift(
                    column=col,
                    drift_type="type_changed",
                    detail=(
                        f"Column '{col}' type changed: contract={contract_type}, "
                        f"source={source_type}. Pipeline MUST fail."
                    ),
                    source_type=source_type,
                    contract_type=contract_type,
                )
                type_changes.append(drift)
                error = {
                    "error_code": SCHEMA_DRIFT,
                    "message": drift.detail,
                    "column": col,
                }
                errors.append(error)
                logger.error("SCHEMA_DRIFT: %s", drift.detail)

        has_drift = len(added) > 0 or len(removed) > 0 or len(type_changes) > 0

        return DriftReport(
            has_drift=has_drift,
            added_columns=added,
            removed_columns=removed,
            type_changes=type_changes,
            errors=errors,
            warnings=warnings,
        )
