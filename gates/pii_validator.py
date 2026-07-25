"""Post-mask PII validation -- samples rows and scans with Presidio.

Samples up to 100 random rows from each masked target dataset table,
scans all Confidential and Restricted columns using the Presidio
analyzer client (real or mock), and verifies that masking strategies
were correctly applied:
- FPE-masked values: must not match original (format validation)
- Tokenized values: must match token format (e.g., NAME_ prefix or TOKEN_ prefix)
- Redacted values: must be NULL or '[REDACTED]'

Returns per-column scan results with clean/violation status.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any

from masking_engine.app.ner.presidio_client import BasePresidioClient, RecognizedEntity

logger = logging.getLogger(__name__)


class PiiScanUnavailable(RuntimeError):
    """The PII analyser could not produce a trustworthy result.

    Raised instead of returning "no entities found", so a scanner outage
    fails the gate rather than silently approving unmasked data.
    """

# Token format patterns for different masking strategies
TOKEN_PATTERNS = [
    re.compile(r"^[A-Z]+_[a-zA-Z0-9]+$"),   # NAME_abc123, TOKEN_xyz
    re.compile(r"^TOK-[a-f0-9]+$", re.I),     # TOK-abcdef01
    re.compile(r"^\*{3,}$"),                    # ****
]

# Valid redacted values
REDACTED_VALUES = {None, "", "[REDACTED]", "NULL", "REDACTED"}

# Default sample size per table
DEFAULT_SAMPLE_SIZE = 100

# Classifications that require PII scanning
SCAN_CLASSIFICATIONS = {"confidential", "restricted"}


@dataclass
class ColumnScanResult:
    """Result of scanning a single column for residual PII."""

    table: str
    column: str
    classification: str
    status: str  # "clean" or "violation"
    rows_scanned: int
    violations_found: int = 0
    violating_entity_types: list[str] = field(default_factory=list)
    detail: str = ""

    @property
    def is_clean(self) -> bool:
        return self.status == "clean"


@dataclass
class PIIScanResult:
    """Aggregated result of PII validation across all tables and columns."""

    tables_scanned: int
    columns_scanned: int
    total_rows_sampled: int
    violations: int
    column_results: list[ColumnScanResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.violations == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tables_scanned": self.tables_scanned,
            "columns_scanned": self.columns_scanned,
            "total_rows_sampled": self.total_rows_sampled,
            "violations": self.violations,
            "passed": self.passed,
            "column_results": [
                {
                    "table": cr.table,
                    "column": cr.column,
                    "classification": cr.classification,
                    "status": cr.status,
                    "rows_scanned": cr.rows_scanned,
                    "violations_found": cr.violations_found,
                    "violating_entity_types": cr.violating_entity_types,
                    "detail": cr.detail,
                }
                for cr in self.column_results
            ],
        }


class PIIValidator:
    """Post-mask PII validator using Presidio analysis.

    Samples up to 100 rows from each table, scans Confidential and
    Restricted columns, and verifies masking was applied correctly.
    """

    def __init__(
        self,
        presidio_client: BasePresidioClient,
        sample_size: int = DEFAULT_SAMPLE_SIZE,
        confidence_threshold: float = 0.70,
    ):
        """Initialize the PII validator.

        Args:
            presidio_client: Presidio client (real or mock) for entity detection.
            sample_size: Max rows to sample per table (default 100).
            confidence_threshold: Minimum confidence score for PII detection.
        """
        self._client = presidio_client
        self._sample_size = sample_size
        self._confidence_threshold = confidence_threshold

    def validate(
        self,
        masked_dataset: dict[str, list[dict[str, Any]]],
        classifications: dict[str, str],
        strategy_map: dict[str, str],
    ) -> PIIScanResult:
        """Validate that PII has been properly masked in the dataset.

        Args:
            masked_dataset: {table_name: [{col: val, ...}]} -- masked data.
            classifications: {"table.column": classification_tier} map.
            strategy_map: {"table.column": masking_strategy} map.

        Returns:
            PIIScanResult with per-column results.
        """
        column_results: list[ColumnScanResult] = []
        tables_scanned = 0
        total_rows_sampled = 0

        for table_name, rows in masked_dataset.items():
            if not rows:
                continue

            tables_scanned += 1

            # Sample up to sample_size rows
            if len(rows) > self._sample_size:
                sampled_rows = random.sample(rows, self._sample_size)
            else:
                sampled_rows = list(rows)

            total_rows_sampled += len(sampled_rows)

            # Identify columns that need scanning (Confidential/Restricted)
            columns_to_scan = self._get_scannable_columns(
                table_name, rows[0].keys(), classifications
            )

            for col_name in columns_to_scan:
                fq_name = f"{table_name}.{col_name}"
                classification = classifications.get(fq_name, "internal")
                strategy = strategy_map.get(fq_name, "passthrough")

                result = self._scan_column(
                    table_name=table_name,
                    col_name=col_name,
                    classification=classification,
                    strategy=strategy,
                    sampled_rows=sampled_rows,
                )
                column_results.append(result)

        violations = sum(1 for cr in column_results if not cr.is_clean)

        scan_result = PIIScanResult(
            tables_scanned=tables_scanned,
            columns_scanned=len(column_results),
            total_rows_sampled=total_rows_sampled,
            violations=violations,
            column_results=column_results,
        )

        if violations > 0:
            logger.warning(
                "PII validation found %d column(s) with violations across %d tables",
                violations,
                tables_scanned,
            )
        else:
            logger.info(
                "PII validation passed: %d columns scanned across %d tables",
                len(column_results),
                tables_scanned,
            )

        return scan_result

    def _get_scannable_columns(
        self,
        table_name: str,
        column_names: Any,
        classifications: dict[str, str],
    ) -> list[str]:
        """Get columns that require PII scanning based on classification.

        Only Confidential and Restricted columns are scanned.
        """
        scannable = []
        for col_name in column_names:
            fq_name = f"{table_name}.{col_name}"
            classification = classifications.get(fq_name, "")
            if classification.lower() in SCAN_CLASSIFICATIONS:
                scannable.append(col_name)
        return scannable

    def _scan_column(
        self,
        table_name: str,
        col_name: str,
        classification: str,
        strategy: str,
        sampled_rows: list[dict[str, Any]],
    ) -> ColumnScanResult:
        """Scan a single column in the sampled rows for residual PII.

        First checks format correctness based on the masking strategy,
        then runs Presidio analysis on string values that pass format checks
        to detect any lingering PII.
        """
        violations_found = 0
        violating_entity_types: set[str] = set()
        rows_scanned = 0

        for row in sampled_rows:
            value = row.get(col_name)
            rows_scanned += 1

            # Check strategy-specific format
            if strategy in ("redact", "redaction"):
                if not self._is_valid_redacted(value):
                    violations_found += 1
                    violating_entity_types.add("REDACTION_FORMAT_VIOLATION")
                continue

            if strategy in ("tokenize", "tokenization"):
                if value is not None and isinstance(value, str):
                    if not self._is_valid_token(value):
                        # Value doesn't match token format -- check for PII
                        entities = self._analyze_value(value)
                        if entities:
                            violations_found += 1
                            for e in entities:
                                violating_entity_types.add(e.entity_type)
                continue

            if strategy in ("format_preserve_encrypt", "fpe"):
                if value is not None and isinstance(value, str):
                    # FPE values should not trigger PII detection
                    entities = self._analyze_value(value)
                    if entities:
                        violations_found += 1
                        for e in entities:
                            violating_entity_types.add(e.entity_type)
                continue

            # For any other strategy (including passthrough on non-sensitive
            # columns that still got scanned for some reason), do PII check
            if value is not None and isinstance(value, str) and value.strip():
                entities = self._analyze_value(value)
                if entities:
                    violations_found += 1
                    for e in entities:
                        violating_entity_types.add(e.entity_type)

        entity_types_list = sorted(violating_entity_types)

        if violations_found > 0:
            detail = (
                f"{violations_found} row(s) with residual PII or format violations "
                f"in {table_name}.{col_name} (strategy={strategy})"
            )
            status = "violation"
        else:
            detail = f"Column {table_name}.{col_name} clean after masking"
            status = "clean"

        return ColumnScanResult(
            table=table_name,
            column=col_name,
            classification=classification,
            status=status,
            rows_scanned=rows_scanned,
            violations_found=violations_found,
            violating_entity_types=entity_types_list,
            detail=detail,
        )

    def _analyze_value(self, value: str) -> list[RecognizedEntity]:
        """Run Presidio analysis on a single value, filtering by threshold.

        Raises PiiScanUnavailable if the analyser fails.

        This used to swallow the exception and return [], which callers read
        as "no PII found" — so a Presidio outage silently turned this gate
        into a rubber stamp and let unmasked data through. A PII gate that
        cannot scan must stop the pipeline, not approve it.
        """
        if not value or not value.strip():
            return []
        try:
            entities = self._client.analyze(value)
        except Exception as exc:
            logger.error("Presidio analysis failed for value: %s", exc)
            raise PiiScanUnavailable(
                f"PII analysis failed and the result cannot be trusted: {exc}"
            ) from exc
        return [e for e in entities if e.score >= self._confidence_threshold]

    @staticmethod
    def _is_valid_redacted(value: Any) -> bool:
        """Check if value is a valid redacted form (NULL or [REDACTED])."""
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() in REDACTED_VALUES
        return False

    @staticmethod
    def _is_valid_token(value: str) -> bool:
        """Check if value matches a known token format."""
        if not value:
            return False
        for pattern in TOKEN_PATTERNS:
            if pattern.match(value):
                return True
        return False
