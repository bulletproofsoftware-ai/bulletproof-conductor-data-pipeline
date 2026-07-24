"""
Quality report data structures for the assertion engine.

Aggregates per-assertion results into a report JSON compatible with the
lineage event 'quality' field (SPEC Section 7.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class AssertionResult:
    """Result of a single assertion execution."""

    assertion_text: str
    phase: str  # "pre_mask" or "post_mask"
    passed: bool
    failing_row_count: int
    execution_time_ms: float

    def to_dict(self) -> dict:
        return {
            "assertion_text": self.assertion_text,
            "phase": self.phase,
            "passed": self.passed,
            "failing_row_count": self.failing_row_count,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class QualityReport:
    """Aggregated quality report across all assertions for a phase."""

    assertions_run: int
    assertions_passed: int
    assertions_failed: int
    phase: str
    execution_time_total_ms: float
    details: List[AssertionResult] = field(default_factory=list)

    def to_lineage_dict(self) -> dict:
        """Format for lineage event quality field."""
        return {
            "assertions_run": self.assertions_run,
            "assertions_passed": self.assertions_passed,
        }

    def to_dict(self) -> dict:
        """Full report as dict."""
        return {
            "assertions_run": self.assertions_run,
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
            "phase": self.phase,
            "execution_time_total_ms": self.execution_time_total_ms,
            "details": [d.to_dict() for d in self.details],
        }
