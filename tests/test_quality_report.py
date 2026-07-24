"""
Tests for the Quality Report data structures.
"""

from quality.quality_report import AssertionResult, QualityReport


class TestAssertionResult:
    def test_to_dict(self):
        result = AssertionResult(
            assertion_text="customers.email IS NOT NULL",
            phase="pre_mask",
            passed=True,
            failing_row_count=0,
            execution_time_ms=1.23,
        )
        d = result.to_dict()
        assert d == {
            "assertion_text": "customers.email IS NOT NULL",
            "phase": "pre_mask",
            "passed": True,
            "failing_row_count": 0,
            "execution_time_ms": 1.23,
        }


class TestQualityReport:
    def test_to_lineage_dict(self):
        report = QualityReport(
            assertions_run=4,
            assertions_passed=3,
            assertions_failed=1,
            phase="pre_mask",
            execution_time_total_ms=10.5,
            details=[],
        )
        assert report.to_lineage_dict() == {
            "assertions_run": 4,
            "assertions_passed": 3,
        }

    def test_to_dict(self):
        detail = AssertionResult(
            assertion_text="t.c IS NOT NULL",
            phase="post_mask",
            passed=False,
            failing_row_count=5,
            execution_time_ms=2.0,
        )
        report = QualityReport(
            assertions_run=1,
            assertions_passed=0,
            assertions_failed=1,
            phase="post_mask",
            execution_time_total_ms=2.0,
            details=[detail],
        )
        d = report.to_dict()
        assert d["assertions_run"] == 1
        assert d["assertions_failed"] == 1
        assert d["phase"] == "post_mask"
        assert len(d["details"]) == 1
        assert d["details"][0]["passed"] is False

    def test_empty_report(self):
        report = QualityReport(
            assertions_run=0,
            assertions_passed=0,
            assertions_failed=0,
            phase="pre_mask",
            execution_time_total_ms=0.0,
        )
        assert report.to_dict()["details"] == []
        assert report.to_lineage_dict() == {
            "assertions_run": 0,
            "assertions_passed": 0,
        }
