"""
Tests for the core Assertion Engine.

Validates all assertion types with passing and failing datasets,
on_failure behavior, and integration with the parser + executor.
"""

import pytest
from quality.assertion_engine import AssertionEngine, QualityAssertionError
from quality.duckdb_executor import DuckDBExecutor


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def executor():
    """Provide a DuckDB executor with test data loaded."""
    ex = DuckDBExecutor()
    yield ex
    ex.close()


def _load_standard_data(executor):
    """Load standard customer/order test data."""
    customers = [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "tier": "gold"},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "tier": "silver"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "tier": "gold"},
    ]
    orders = [
        {"id": 10, "customer_id": 1, "amount": 100, "status": "active"},
        {"id": 11, "customer_id": 1, "amount": 200, "status": "active"},
        {"id": 12, "customer_id": 2, "amount": 50, "status": "pending"},
        {"id": 13, "customer_id": 3, "amount": 300, "status": "complete"},
    ]
    executor.load_table("customers", customers)
    executor.load_table("orders", orders)


# ===================================================================
# IS NOT NULL
# ===================================================================

class TestIsNotNull:
    def test_pass_no_nulls(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["customers.email IS NOT NULL"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1
        assert report.assertions_failed == 0
        assert report.details[0].passed is True

    def test_fail_with_nulls(self, executor):
        data = [
            {"id": 1, "email": "a@b.com"},
            {"id": 2, "email": None},
            {"id": 3, "email": None},
        ]
        executor.load_table("customers", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["customers.email IS NOT NULL"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].passed is False
        assert report.details[0].failing_row_count == 2


# ===================================================================
# IS UNIQUE
# ===================================================================

class TestIsUnique:
    def test_pass_unique_values(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["customers.id IS UNIQUE"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1
        assert report.details[0].passed is True

    def test_fail_with_duplicates(self, executor):
        data = [
            {"id": 1, "email": "a@b.com"},
            {"id": 1, "email": "c@d.com"},
            {"id": 2, "email": "e@f.com"},
        ]
        executor.load_table("customers", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["customers.id IS UNIQUE"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].passed is False
        assert report.details[0].failing_row_count == 1  # 3 - 2 distinct = 1


# ===================================================================
# Comparison (>= N)
# ===================================================================

class TestComparison:
    def test_pass_all_above(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["orders.amount >= 0"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1

    def test_fail_values_below(self, executor):
        data = [
            {"id": 1, "amount": 100},
            {"id": 2, "amount": -5},
            {"id": 3, "amount": 50},
        ]
        executor.load_table("orders", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["orders.amount >= 0"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].failing_row_count == 1


# ===================================================================
# ROW_COUNT
# ===================================================================

class TestRowCount:
    def test_pass_with_data(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["ROW_COUNT(customers) > 0"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1
        assert report.details[0].passed is True

    def test_fail_empty_table(self, executor):
        executor.load_table("customers", [])
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["ROW_COUNT(customers) > 0"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].passed is False

    def test_gte_threshold(self, executor):
        data = [{"id": i} for i in range(5)]
        executor.load_table("items", data)
        engine = AssertionEngine(executor)

        # Should pass: 5 >= 5
        report = engine.run_assertions(
            ["ROW_COUNT(items) >= 5"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1

        # Should fail: 5 >= 10
        executor.drop_table("items")
        executor.load_table("items", data)
        report = engine.run_assertions(
            ["ROW_COUNT(items) >= 10"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1


# ===================================================================
# MATCHES (regex)
# ===================================================================

class TestMatches:
    def test_pass_matching_regex(self, executor):
        data = [
            {"id": 1, "code": "ORD-001"},
            {"id": 2, "code": "ORD-002"},
            {"id": 3, "code": "ORD-100"},
        ]
        executor.load_table("orders", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["orders.code MATCHES '^ORD-[0-9]+'"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1

    def test_fail_non_matching(self, executor):
        data = [
            {"id": 1, "code": "ORD-001"},
            {"id": 2, "code": "INVALID"},
            {"id": 3, "code": "ORD-100"},
        ]
        executor.load_table("orders", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["orders.code MATCHES '^ORD-[0-9]+'"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].failing_row_count == 1


# ===================================================================
# Custom ASSERT
# ===================================================================

class TestCustomAssert:
    def test_pass_no_results(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        # This should return 0 rows (no premium customers with null email)
        report = engine.run_assertions(
            ["ASSERT SELECT * FROM customers WHERE email IS NULL AND tier = 'gold'"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1

    def test_fail_with_results(self, executor):
        data = [
            {"id": 1, "email": None, "tier": "gold"},
            {"id": 2, "email": "b@c.com", "tier": "silver"},
        ]
        executor.load_table("customers", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["ASSERT SELECT * FROM customers WHERE email IS NULL AND tier = 'gold'"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].failing_row_count == 1


# ===================================================================
# BETWEEN
# ===================================================================

class TestBetween:
    def test_pass_all_in_range(self, executor):
        data = [{"id": i, "score": 50 + i} for i in range(10)]
        executor.load_table("scores", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["scores.score BETWEEN 0 AND 100"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1

    def test_fail_out_of_range(self, executor):
        data = [
            {"id": 1, "score": 50},
            {"id": 2, "score": 150},
            {"id": 3, "score": -10},
        ]
        executor.load_table("scores", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["scores.score BETWEEN 0 AND 100"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].failing_row_count == 2


# ===================================================================
# IN VALUES
# ===================================================================

class TestInValues:
    def test_pass_all_valid(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["orders.status IN ('active', 'pending', 'complete')"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1

    def test_fail_invalid_values(self, executor):
        data = [
            {"id": 1, "status": "active"},
            {"id": 2, "status": "unknown"},
        ]
        executor.load_table("orders", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["orders.status IN ('active', 'pending')"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1
        assert report.details[0].failing_row_count == 1


# ===================================================================
# COUNT(DISTINCT ...)
# ===================================================================

class TestCountDistinct:
    def test_pass_enough_distinct(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["COUNT(DISTINCT customers.tier) >= 2"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_passed == 1

    def test_fail_not_enough_distinct(self, executor):
        data = [
            {"id": 1, "tier": "gold"},
            {"id": 2, "tier": "gold"},
            {"id": 3, "tier": "gold"},
        ]
        executor.load_table("customers", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["COUNT(DISTINCT customers.tier) >= 2"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1


# ===================================================================
# on_failure behavior
# ===================================================================

class TestOnFailure:
    def test_block_raises_error(self, executor):
        data = [{"id": 1, "email": None}]
        executor.load_table("customers", data)
        engine = AssertionEngine(executor)

        with pytest.raises(QualityAssertionError) as exc_info:
            engine.run_assertions(
                ["customers.email IS NOT NULL"],
                phase="pre_mask",
                on_failure="block",
            )

        assert exc_info.value.report.assertions_failed == 1

    def test_warn_continues(self, executor):
        data = [{"id": 1, "email": None}]
        executor.load_table("customers", data)
        engine = AssertionEngine(executor)

        # Should NOT raise, just return report with failures
        report = engine.run_assertions(
            ["customers.email IS NOT NULL"],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_failed == 1

    def test_block_with_passing_assertions(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)

        # All pass — should NOT raise even with block
        report = engine.run_assertions(
            ["customers.email IS NOT NULL", "customers.id IS UNIQUE"],
            phase="pre_mask",
            on_failure="block",
        )
        assert report.assertions_passed == 2
        assert report.assertions_failed == 0


# ===================================================================
# Quality Report
# ===================================================================

class TestQualityReport:
    def test_report_structure(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            [
                "customers.email IS NOT NULL",
                "customers.id IS UNIQUE",
                "orders.amount >= 0",
                "ROW_COUNT(customers) > 0",
            ],
            phase="pre_mask",
            on_failure="warn",
        )

        assert report.assertions_run == 4
        assert report.assertions_passed == 4
        assert report.assertions_failed == 0
        assert report.phase == "pre_mask"
        assert report.execution_time_total_ms >= 0
        assert len(report.details) == 4

        for detail in report.details:
            assert detail.phase == "pre_mask"
            assert detail.execution_time_ms >= 0

    def test_lineage_dict(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["customers.email IS NOT NULL"],
            phase="pre_mask",
            on_failure="warn",
        )

        lineage = report.to_lineage_dict()
        assert lineage == {
            "assertions_run": 1,
            "assertions_passed": 1,
        }

    def test_full_dict(self, executor):
        _load_standard_data(executor)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            ["customers.email IS NOT NULL"],
            phase="post_mask",
            on_failure="warn",
        )

        d = report.to_dict()
        assert d["assertions_run"] == 1
        assert d["phase"] == "post_mask"
        assert len(d["details"]) == 1
        assert d["details"][0]["assertion_text"] == "customers.email IS NOT NULL"
        assert d["details"][0]["passed"] is True

    def test_mixed_pass_fail(self, executor):
        data = [
            {"id": 1, "email": "a@b.com"},
            {"id": 1, "email": None},
        ]
        executor.load_table("customers", data)
        engine = AssertionEngine(executor)
        report = engine.run_assertions(
            [
                "customers.email IS NOT NULL",  # fails (1 null)
                "customers.id IS UNIQUE",        # fails (duplicate id)
            ],
            phase="pre_mask",
            on_failure="warn",
        )
        assert report.assertions_run == 2
        assert report.assertions_passed == 0
        assert report.assertions_failed == 2
