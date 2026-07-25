"""POST-DATA-PIPELINE quality gate -- BLOCKING gate with 6 validation checks.

Implements REQ-DP-021: the post-pipeline quality gate that must pass before
the pipeline can progress. Runs 6 checks from Section 8.2:

1. Contract coverage: Data contract exists and covers all extracted columns
2. Quality assertions: All assertions pass (pre-mask and post-mask)
3. Masking correctness: Masking applied correctly (via PII validator)
4. Lineage completeness: Lineage events emitted for every operation
5. Restricted data check: No restricted data in non-production targets
6. Referential integrity: FK relationships preserved across masked tables

Returns a GateResult with per-check pass/fail and overall verdict.
Gate mode is BLOCKING -- pipeline cannot progress on failure.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from gates.pii_validator import PIIValidator, PIIScanResult, PiiScanUnavailable
from gates.gate_registry import GateRegistry

logger = logging.getLogger(__name__)

# Check identifiers
CHECK_1_CONTRACT = "contract_coverage"
CHECK_2_QUALITY = "quality_assertions"
CHECK_3_MASKING = "masking_correctness"
CHECK_4_LINEAGE = "lineage_completeness"
CHECK_5_RESTRICTED = "restricted_data_check"
CHECK_6_INTEGRITY = "referential_integrity"


@dataclass
class CheckResult:
    """Result of a single gate validation check."""
    check_name: str
    passed: bool
    detail: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "detail": self.detail,
            "metadata": self.metadata,
        }


@dataclass
class GateResult:
    """Aggregated result of the POST-DATA-PIPELINE gate."""
    gate_name: str = "POST-DATA-PIPELINE"
    verdict: str = "FAIL"  # "PASS" or "FAIL"
    mode: str = "blocking"
    checks_run: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    check_results: list[CheckResult] = field(default_factory=list)
    execution_time_ms: float = 0.0
    failed_checks: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "verdict": self.verdict,
            "mode": self.mode,
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "check_results": [cr.to_dict() for cr in self.check_results],
            "execution_time_ms": round(self.execution_time_ms, 2),
            "failed_checks": self.failed_checks,
        }


@dataclass
class PipelineContext:
    """All the inputs needed for the gate to run its 6 checks.

    Collects results from upstream pipeline steps so the gate can
    validate them without re-executing anything.
    """
    pipeline_id: str
    target_tier: str  # "production", "staging", "development", etc.

    # CHECK 1: Contract coverage
    contract: Optional[dict[str, Any]] = None  # Data contract dict
    extracted_columns: Optional[list[str]] = None  # ["table.column", ...]

    # CHECK 2: Quality assertions
    quality_results: Optional[dict[str, Any]] = None  # QualityReport-like dict

    # CHECK 3: Masking correctness (via PII validator)
    masked_dataset: Optional[dict[str, list[dict[str, Any]]]] = None
    classifications: Optional[dict[str, str]] = None  # {"table.column": tier}
    strategy_map: Optional[dict[str, str]] = None     # {"table.column": strategy}

    # CHECK 4: Lineage completeness
    expected_lineage_operations: Optional[list[str]] = None  # ["extract", "transform", "mask"]
    emitted_lineage_events: Optional[list[dict[str, Any]]] = None

    # CHECK 5: Restricted data check
    # Uses classifications + target_tier

    # CHECK 6: Referential integrity
    integrity_report: Optional[dict[str, Any]] = None  # IntegrityReport-like dict


class PostDataPipelineGate:
    """POST-DATA-PIPELINE BLOCKING quality gate.

    Runs 6 validation checks and returns a GateResult. The pipeline
    cannot progress if any check fails (BLOCKING mode).
    """

    def __init__(
        self,
        pii_validator: Optional[PIIValidator] = None,
        gate_registry: Optional[GateRegistry] = None,
    ):
        """Initialize the gate.

        Args:
            pii_validator: PIIValidator for CHECK 3 (masking correctness).
                           If None, CHECK 3 will be skipped with a warning.
            gate_registry: Optional GateRegistry for recording results.
        """
        self._pii_validator = pii_validator
        self._gate_registry = gate_registry

    def evaluate(self, context: PipelineContext) -> GateResult:
        """Run all 6 validation checks and return the gate result.

        This is the main entry point. Runs all checks regardless of
        individual failures (does not short-circuit) so the caller
        gets a complete picture.

        Args:
            context: Pipeline context with all inputs for the 6 checks.

        Returns:
            GateResult with per-check pass/fail and overall verdict.
        """
        start = time.monotonic()
        check_results: list[CheckResult] = []

        # Run all 6 checks
        check_results.append(self._check_contract_coverage(context))
        check_results.append(self._check_quality_assertions(context))
        check_results.append(self._check_masking_correctness(context))
        check_results.append(self._check_lineage_completeness(context))
        check_results.append(self._check_restricted_data(context))
        check_results.append(self._check_referential_integrity(context))

        elapsed = (time.monotonic() - start) * 1000

        passed = sum(1 for cr in check_results if cr.passed)
        failed = sum(1 for cr in check_results if not cr.passed)
        failed_names = [cr.check_name for cr in check_results if not cr.passed]

        verdict = "PASS" if failed == 0 else "FAIL"

        result = GateResult(
            gate_name="POST-DATA-PIPELINE",
            verdict=verdict,
            mode="blocking",
            checks_run=len(check_results),
            checks_passed=passed,
            checks_failed=failed,
            check_results=check_results,
            execution_time_ms=elapsed,
            failed_checks=failed_names,
        )

        # Record in gate registry if available
        if self._gate_registry is not None:
            self._gate_registry.record_execution(
                gate_name="POST-DATA-PIPELINE",
                pipeline_id=context.pipeline_id,
                verdict=verdict,
                check_results={cr.check_name: cr.passed for cr in check_results},
                duration_ms=elapsed,
            )

        if verdict == "FAIL":
            logger.warning(
                "POST-DATA-PIPELINE gate FAILED for pipeline=%s: %d/%d checks failed (%s)",
                context.pipeline_id,
                failed,
                len(check_results),
                ", ".join(failed_names),
            )
        else:
            logger.info(
                "POST-DATA-PIPELINE gate PASSED for pipeline=%s: all %d checks passed (%.2fms)",
                context.pipeline_id,
                len(check_results),
                elapsed,
            )

        return result

    def _check_contract_coverage(self, context: PipelineContext) -> CheckResult:
        """CHECK 1: Data contract exists and covers all extracted columns.

        Verifies that:
        - A data contract is provided
        - Every extracted column is defined in the contract
        """
        if context.contract is None:
            return CheckResult(
                check_name=CHECK_1_CONTRACT,
                passed=False,
                detail="No data contract provided",
            )

        if context.extracted_columns is None:
            return CheckResult(
                check_name=CHECK_1_CONTRACT,
                passed=False,
                detail="No extracted columns list provided",
            )

        # Get columns defined in the contract
        contract_columns = set()
        columns_section = context.contract.get("columns", {})
        if isinstance(columns_section, dict):
            contract_columns = set(columns_section.keys())
        elif isinstance(columns_section, list):
            for col_def in columns_section:
                if isinstance(col_def, dict) and "name" in col_def:
                    contract_columns.add(col_def["name"])
                elif isinstance(col_def, str):
                    contract_columns.add(col_def)

        extracted = set(context.extracted_columns)
        uncovered = extracted - contract_columns

        if uncovered:
            return CheckResult(
                check_name=CHECK_1_CONTRACT,
                passed=False,
                detail=f"{len(uncovered)} extracted column(s) not covered by contract",
                metadata={"uncovered_columns": sorted(uncovered)},
            )

        return CheckResult(
            check_name=CHECK_1_CONTRACT,
            passed=True,
            detail=f"All {len(extracted)} extracted columns covered by contract",
            metadata={"covered_columns": len(extracted)},
        )

    def _check_quality_assertions(self, context: PipelineContext) -> CheckResult:
        """CHECK 2: All quality assertions pass (pre-mask and post-mask).

        Accepts a QualityReport-style dict with assertions_passed and
        assertions_failed counts.
        """
        if context.quality_results is None:
            return CheckResult(
                check_name=CHECK_2_QUALITY,
                passed=False,
                detail="No quality assertion results provided",
            )

        qr = context.quality_results
        failed_count = qr.get("assertions_failed", 0)
        passed_count = qr.get("assertions_passed", 0)
        total_run = qr.get("assertions_run", 0)

        if total_run == 0:
            return CheckResult(
                check_name=CHECK_2_QUALITY,
                passed=False,
                detail="No quality assertions were executed",
            )

        if failed_count > 0:
            return CheckResult(
                check_name=CHECK_2_QUALITY,
                passed=False,
                detail=f"{failed_count} of {total_run} quality assertion(s) failed",
                metadata={
                    "assertions_run": total_run,
                    "assertions_passed": passed_count,
                    "assertions_failed": failed_count,
                },
            )

        return CheckResult(
            check_name=CHECK_2_QUALITY,
            passed=True,
            detail=f"All {total_run} quality assertions passed",
            metadata={
                "assertions_run": total_run,
                "assertions_passed": passed_count,
            },
        )

    def _check_masking_correctness(self, context: PipelineContext) -> CheckResult:
        """CHECK 3: Masking applied correctly (post-mask PII validation).

        Uses the PIIValidator to sample 100 rows and scan for residual PII
        in Confidential and Restricted columns.
        """
        if self._pii_validator is None:
            return CheckResult(
                check_name=CHECK_3_MASKING,
                passed=False,
                detail="PII validator not configured",
            )

        if context.masked_dataset is None:
            return CheckResult(
                check_name=CHECK_3_MASKING,
                passed=False,
                detail="No masked dataset provided for PII validation",
            )

        if context.classifications is None:
            return CheckResult(
                check_name=CHECK_3_MASKING,
                passed=False,
                detail="No column classifications provided",
            )

        if context.strategy_map is None:
            return CheckResult(
                check_name=CHECK_3_MASKING,
                passed=False,
                detail="No masking strategy map provided",
            )

        try:
            scan_result: PIIScanResult = self._pii_validator.validate(
                masked_dataset=context.masked_dataset,
                classifications=context.classifications,
                strategy_map=context.strategy_map,
            )
        except PiiScanUnavailable as exc:
            # The scanner could not produce a trustworthy answer. Fail the
            # check: an unverifiable dataset must not pass a PII gate just
            # because the analyser was unavailable.
            return CheckResult(
                check_name=CHECK_3_MASKING,
                passed=False,
                detail=f"PII validation could not run: {exc}",
                metadata={"scanner_available": False},
            )

        if not scan_result.passed:
            violation_details = [
                f"{cr.table}.{cr.column}: {cr.violations_found} violation(s) "
                f"({', '.join(cr.violating_entity_types)})"
                for cr in scan_result.column_results
                if not cr.is_clean
            ]
            return CheckResult(
                check_name=CHECK_3_MASKING,
                passed=False,
                detail=(
                    f"PII validation failed: {scan_result.violations} column(s) "
                    f"with violations"
                ),
                metadata={
                    "violations": scan_result.violations,
                    "violation_details": violation_details,
                    "rows_sampled": scan_result.total_rows_sampled,
                },
            )

        return CheckResult(
            check_name=CHECK_3_MASKING,
            passed=True,
            detail=(
                f"PII validation passed: {scan_result.columns_scanned} columns "
                f"scanned, {scan_result.total_rows_sampled} rows sampled"
            ),
            metadata={
                "columns_scanned": scan_result.columns_scanned,
                "rows_sampled": scan_result.total_rows_sampled,
            },
        )

    def _check_lineage_completeness(self, context: PipelineContext) -> CheckResult:
        """CHECK 4: Lineage events emitted for every operation.

        Verifies that for each expected operation (extract, transform, mask, etc.),
        at least one lineage event was emitted.
        """
        if context.expected_lineage_operations is None:
            return CheckResult(
                check_name=CHECK_4_LINEAGE,
                passed=False,
                detail="No expected lineage operations provided",
            )

        if context.emitted_lineage_events is None:
            return CheckResult(
                check_name=CHECK_4_LINEAGE,
                passed=False,
                detail="No emitted lineage events provided",
            )

        # Collect operations from emitted events
        emitted_operations: set[str] = set()
        for event in context.emitted_lineage_events:
            op = event.get("operation") or event.get("event", {}).get("operation")
            if op:
                emitted_operations.add(op.lower())

        expected = set(op.lower() for op in context.expected_lineage_operations)
        missing = expected - emitted_operations

        if missing:
            return CheckResult(
                check_name=CHECK_4_LINEAGE,
                passed=False,
                detail=f"{len(missing)} expected lineage operation(s) missing",
                metadata={
                    "missing_operations": sorted(missing),
                    "emitted_operations": sorted(emitted_operations),
                },
            )

        return CheckResult(
            check_name=CHECK_4_LINEAGE,
            passed=True,
            detail=(
                f"All {len(expected)} expected lineage operations found "
                f"({len(context.emitted_lineage_events)} events total)"
            ),
            metadata={
                "expected_operations": sorted(expected),
                "total_events": len(context.emitted_lineage_events),
            },
        )

    def _check_restricted_data(self, context: PipelineContext) -> CheckResult:
        """CHECK 5: No restricted data present in non-production targets.

        If the target tier is not 'production', verify that no columns
        classified as 'restricted' contain actual data (should be
        redacted or masked).
        """
        if context.target_tier is None:
            return CheckResult(
                check_name=CHECK_5_RESTRICTED,
                passed=False,
                detail="No target tier specified",
            )

        # Production targets are exempt (restricted data allowed)
        if context.target_tier.lower() == "production":
            return CheckResult(
                check_name=CHECK_5_RESTRICTED,
                passed=True,
                detail="Production target: restricted data check not applicable",
            )

        if context.classifications is None:
            return CheckResult(
                check_name=CHECK_5_RESTRICTED,
                passed=False,
                detail="No column classifications provided",
            )

        if context.masked_dataset is None:
            return CheckResult(
                check_name=CHECK_5_RESTRICTED,
                passed=False,
                detail="No masked dataset provided for restricted data check",
            )

        # Find restricted columns
        restricted_columns: list[str] = [
            col for col, cls in context.classifications.items()
            if cls.lower() == "restricted"
        ]

        if not restricted_columns:
            return CheckResult(
                check_name=CHECK_5_RESTRICTED,
                passed=True,
                detail="No restricted columns in dataset",
            )

        # Check that restricted columns are properly masked (NULL or [REDACTED])
        violations: list[str] = []
        for fq_col in restricted_columns:
            parts = fq_col.split(".", 1)
            if len(parts) != 2:
                continue
            table_name, col_name = parts

            rows = context.masked_dataset.get(table_name, [])
            for row_idx, row in enumerate(rows):
                value = row.get(col_name)
                if value is not None and value != "[REDACTED]" and value != "":
                    # Check if it looks properly masked (tokens/FPE are OK)
                    if isinstance(value, str) and (
                        value.startswith("TOK-")
                        or value.startswith("TOKEN_")
                        or value == "****"
                        or value == "[REDACTED]"
                    ):
                        continue
                    violations.append(f"{fq_col} row {row_idx}")
                    if len(violations) >= 10:
                        break  # Cap violation reporting

        if violations:
            return CheckResult(
                check_name=CHECK_5_RESTRICTED,
                passed=False,
                detail=(
                    f"Restricted data found in non-production target "
                    f"'{context.target_tier}': {len(violations)} violation(s)"
                ),
                metadata={
                    "target_tier": context.target_tier,
                    "restricted_columns": restricted_columns,
                    "violation_count": len(violations),
                },
            )

        return CheckResult(
            check_name=CHECK_5_RESTRICTED,
            passed=True,
            detail=(
                f"No restricted data found in non-production target "
                f"'{context.target_tier}' ({len(restricted_columns)} restricted columns checked)"
            ),
        )

    def _check_referential_integrity(self, context: PipelineContext) -> CheckResult:
        """CHECK 6: FK relationships preserved across masked tables.

        Uses the IntegrityReport from the masking engine to verify that
        all FK relationships hold after masking.
        """
        if context.integrity_report is None:
            return CheckResult(
                check_name=CHECK_6_INTEGRITY,
                passed=True,
                detail="No FK relationships to check (single table or no FKs)",
            )

        ir = context.integrity_report
        checked = ir.get("checked", 0)
        failed = ir.get("failed", 0)

        if checked == 0:
            return CheckResult(
                check_name=CHECK_6_INTEGRITY,
                passed=True,
                detail="No FK relationships checked (trivial pass)",
            )

        if failed > 0:
            # Extract failure details
            failure_details = []
            for result in ir.get("results", []):
                if not result.get("passed", True):
                    failure_details.append(result.get("detail", "unknown"))

            return CheckResult(
                check_name=CHECK_6_INTEGRITY,
                passed=False,
                detail=f"{failed} of {checked} FK relationship(s) broken after masking",
                metadata={
                    "checked": checked,
                    "failed": failed,
                    "failure_details": failure_details,
                },
            )

        return CheckResult(
            check_name=CHECK_6_INTEGRITY,
            passed=True,
            detail=f"All {checked} FK relationship(s) preserved after masking",
            metadata={"checked": checked},
        )
