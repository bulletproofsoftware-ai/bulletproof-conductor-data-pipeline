"""
Core Assertion Engine for the Conductor Data Pipeline.

Orchestrates parsing and execution of quality assertions against
in-memory DuckDB datasets. Returns a QualityReport with per-assertion
results.
"""

from __future__ import annotations

import logging
import time
from typing import List

from quality.assertion_parser import (
    AssertionType,
    ParsedAssertion,
    parse_assertion,
)
from quality.duckdb_executor import DuckDBExecutor
from quality.quality_report import AssertionResult, QualityReport

logger = logging.getLogger(__name__)


class QualityAssertionError(Exception):
    """
    Raised when assertions fail and on_failure == 'block'.
    Contains the QualityReport for inspection.
    """

    def __init__(self, message: str, report: QualityReport) -> None:
        super().__init__(message)
        self.report = report


class AssertionEngine:
    """
    Parses and executes quality assertions from pipeline YAML.

    Usage:
        executor = DuckDBExecutor()
        executor.load_table("customers", customer_data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            assertions=["customers.email IS NOT NULL", "customers.id IS UNIQUE"],
            phase="pre_mask",
            on_failure="block",
        )
    """

    def __init__(self, executor: DuckDBExecutor) -> None:
        self._executor = executor

    def run_assertions(
        self,
        assertions: List[str],
        phase: str = "pre_mask",
        on_failure: str = "block",
    ) -> QualityReport:
        """
        Parse and execute all assertions, returning a QualityReport.

        Args:
            assertions: List of assertion DSL strings from pipeline YAML.
            phase: Execution phase ('pre_mask' or 'post_mask').
            on_failure: 'block' to raise QualityAssertionError on failure,
                        'warn' to log warnings and continue.

        Returns:
            QualityReport with per-assertion results.

        Raises:
            QualityAssertionError: If any assertion fails and on_failure == 'block'.
        """
        results: List[AssertionResult] = []
        total_start = time.monotonic()

        for assertion_text in assertions:
            result = self._execute_single(assertion_text, phase)
            results.append(result)

        total_time = (time.monotonic() - total_start) * 1000
        passed_count = sum(1 for r in results if r.passed)
        failed_count = sum(1 for r in results if not r.passed)

        report = QualityReport(
            assertions_run=len(results),
            assertions_passed=passed_count,
            assertions_failed=failed_count,
            phase=phase,
            execution_time_total_ms=round(total_time, 2),
            details=results,
        )

        if failed_count > 0:
            failed_texts = [
                r.assertion_text for r in results if not r.passed
            ]
            message = (
                f"{failed_count} assertion(s) failed in phase '{phase}': "
                f"{failed_texts}"
            )

            if on_failure == "block":
                raise QualityAssertionError(message, report)
            else:
                logger.warning(message)

        return report

    def _execute_single(
        self, assertion_text: str, phase: str
    ) -> AssertionResult:
        """
        Parse and execute a single assertion.

        Returns an AssertionResult regardless of pass/fail.
        """
        start = time.monotonic()

        try:
            parsed = parse_assertion(assertion_text)
            passed, failing_count = self._evaluate(parsed)
        except Exception as e:
            # Parse or execution error counts as a failure
            elapsed = (time.monotonic() - start) * 1000
            logger.error(
                "Assertion failed with error: %s — %s",
                assertion_text, e,
            )
            return AssertionResult(
                assertion_text=assertion_text,
                phase=phase,
                passed=False,
                failing_row_count=-1,
                execution_time_ms=round(elapsed, 2),
            )

        elapsed = (time.monotonic() - start) * 1000
        return AssertionResult(
            assertion_text=assertion_text,
            phase=phase,
            passed=passed,
            failing_row_count=failing_count,
            execution_time_ms=round(elapsed, 2),
        )

    def _evaluate(self, parsed: ParsedAssertion) -> tuple:
        """
        Execute a parsed assertion and return (passed: bool, failing_count: int).
        """
        rows = self._executor.execute_sql(parsed.sql)

        if not rows or not rows[0]:
            count = 0
        else:
            count = rows[0][0]
            if count is None:
                count = 0
            count = int(count)

        if parsed.assertion_type == AssertionType.ROW_COUNT:
            # Parse the fail condition to determine pass/fail
            # fail_condition is like "count <= 0" — we need to negate
            # The original assertion was ROW_COUNT(table) > N
            # SQL is SELECT COUNT(*) FROM table
            # We need to evaluate: does the count satisfy the ORIGINAL operator?
            passed = self._evaluate_row_count(parsed, count)
            # For ROW_COUNT, "failing_count" is not meaningful in the same
            # way; we report the actual count
            return (passed, 0 if passed else count)

        if parsed.assertion_type == AssertionType.COUNT_DISTINCT:
            # Similar: SQL returns COUNT(DISTINCT col), we check against threshold
            passed = self._evaluate_count_distinct(parsed, count)
            return (passed, 0 if passed else count)

        if parsed.assertion_type == AssertionType.CUSTOM_ASSERT:
            # Custom ASSERT: fail if result has > 0 rows
            # The SQL was executed; count is the number of rows
            # Actually for ASSERT, we need row count of result, not first column
            result_rows = rows
            row_count = len(result_rows)
            # But if the query returns a scalar, we count rows
            passed = row_count == 0
            return (passed, row_count)

        # For standard assertions (IS NOT NULL, IS UNIQUE, comparison,
        # BETWEEN, IN, MATCHES): count > 0 means failure
        passed = count == 0
        return (passed, count)

    def _evaluate_row_count(
        self, parsed: ParsedAssertion, actual_count: int
    ) -> bool:
        """
        Evaluate ROW_COUNT assertion.

        The fail_condition contains the negated operator, e.g. "count <= 0"
        means the original assertion was ROW_COUNT(table) > 0.
        We extract the original operator and threshold from the original text.
        """
        import re

        match = re.match(
            r"^ROW_COUNT\(\s*\w+\s*\)\s*(>=|<=|!=|>|<|=)\s*(.+)$",
            parsed.original_text,
            re.IGNORECASE,
        )
        if not match:
            return False

        operator = match.group(1)
        threshold = int(float(match.group(2).strip()))
        return _compare(actual_count, operator, threshold)

    def _evaluate_count_distinct(
        self, parsed: ParsedAssertion, actual_count: int
    ) -> bool:
        """
        Evaluate COUNT(DISTINCT column) assertion.

        Extract the original operator and threshold from the original text.
        """
        import re

        match = re.match(
            r"^COUNT\(\s*DISTINCT\s+\S+\s*\)\s*(>=|<=|!=|>|<|=)\s*(.+)$",
            parsed.original_text,
            re.IGNORECASE,
        )
        if not match:
            return False

        operator = match.group(1)
        threshold = int(float(match.group(2).strip()))
        return _compare(actual_count, operator, threshold)


def _compare(actual: int, operator: str, threshold: int) -> bool:
    """Evaluate a comparison: actual <op> threshold."""
    ops = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "=": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    fn = ops.get(operator)
    if fn is None:
        return False
    return fn(actual, threshold)
