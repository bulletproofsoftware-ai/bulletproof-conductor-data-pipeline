"""
Tests for the Transform Engine.

Validates join, filter, derive, and aggregate operations,
including sequential transform chains.
"""

import pytest
from quality.duckdb_executor import DuckDBExecutor
from quality.transform_engine import TransformEngine, TransformError


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def executor():
    ex = DuckDBExecutor()
    yield ex
    ex.close()


def _load_standard_data(executor):
    """Load customers and orders tables."""
    customers = [
        {"id": 1, "name": "Alice", "tier": "gold"},
        {"id": 2, "name": "Bob", "tier": "silver"},
        {"id": 3, "name": "Charlie", "tier": "gold"},
        {"id": 4, "name": "Diana", "tier": "bronze"},
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
# JOIN
# ===================================================================

class TestJoin:
    def test_left_join_row_count(self, executor):
        """Left join: all customers appear, even without orders."""
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "join",
                "left": "customers",
                "right": "orders",
                "on": "customers.id = orders.customer_id",
                "type": "left",
            }
        ])

        rows = executor.execute_sql(
            "SELECT COUNT(*) FROM customers_orders_joined"
        )
        # 4 customers: Alice(2 orders), Bob(1), Charlie(1), Diana(0) = 5 rows
        # Diana gets a NULL-filled row from LEFT JOIN
        assert rows[0][0] == 5

    def test_inner_join_row_count(self, executor):
        """Inner join: only customers with orders."""
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "join",
                "left": "customers",
                "right": "orders",
                "on": "customers.id = orders.customer_id",
                "type": "inner",
            }
        ])

        rows = executor.execute_sql(
            "SELECT COUNT(*) FROM customers_orders_joined"
        )
        # Only Alice(2), Bob(1), Charlie(1) = 4 rows
        assert rows[0][0] == 4

    def test_custom_output_name(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "join",
                "left": "customers",
                "right": "orders",
                "on": "customers.id = orders.customer_id",
                "type": "inner",
                "output": "cust_orders",
            }
        ])

        rows = executor.execute_sql("SELECT COUNT(*) FROM cust_orders")
        assert rows[0][0] == 4

    def test_cross_join(self, executor):
        executor.load_table("a", [{"x": 1}, {"x": 2}])
        executor.load_table("b", [{"y": 10}, {"y": 20}, {"y": 30}])
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "join",
                "left": "a",
                "right": "b",
                "on": "1=1",
                "type": "cross",
            }
        ])

        rows = executor.execute_sql("SELECT COUNT(*) FROM a_b_joined")
        assert rows[0][0] == 6  # 2 * 3

    def test_missing_fields_raises(self, executor):
        engine = TransformEngine(executor)
        with pytest.raises(TransformError, match="requires"):
            engine.execute_transforms([
                {"operation": "join", "left": "customers"}
            ])

    def test_invalid_join_type(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)
        with pytest.raises(TransformError, match="Invalid join type"):
            engine.execute_transforms([
                {
                    "operation": "join",
                    "left": "customers",
                    "right": "orders",
                    "on": "customers.id = orders.customer_id",
                    "type": "natural",
                }
            ])


# ===================================================================
# FILTER
# ===================================================================

class TestFilter:
    def test_filter_rows(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "filter",
                "input": "orders",
                "expression": "amount >= 100",
            }
        ])

        rows = executor.execute_sql(
            "SELECT COUNT(*) FROM orders_filtered"
        )
        # Orders with amount >= 100: 100, 200, 300 = 3
        assert rows[0][0] == 3

    def test_filter_with_string_condition(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "filter",
                "input": "orders",
                "expression": "status = 'active'",
                "output": "active_orders",
            }
        ])

        rows = executor.execute_sql(
            "SELECT COUNT(*) FROM active_orders"
        )
        assert rows[0][0] == 2

    def test_filter_to_empty(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "filter",
                "input": "orders",
                "expression": "amount > 99999",
                "output": "empty_orders",
            }
        ])

        rows = executor.execute_sql("SELECT COUNT(*) FROM empty_orders")
        assert rows[0][0] == 0


# ===================================================================
# DERIVE
# ===================================================================

class TestDerive:
    def test_simple_derive(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "derive",
                "table": "orders",
                "field": "amount_tax",
                "expression": "amount * 0.1",
            }
        ])

        rows = executor.execute_sql(
            "SELECT amount, amount_tax FROM orders ORDER BY amount"
        )
        # amount=50 -> tax=5.0, amount=100 -> tax=10.0, etc.
        assert abs(float(rows[0][1]) - 5.0) < 0.01
        assert abs(float(rows[1][1]) - 10.0) < 0.01

    def test_derive_with_output(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "derive",
                "table": "orders",
                "field": "doubled",
                "expression": "amount * 2",
                "output": "orders_doubled",
            }
        ])

        rows = executor.execute_sql(
            "SELECT doubled FROM orders_doubled ORDER BY doubled"
        )
        assert rows[0][0] == 100  # 50 * 2
        assert rows[1][0] == 200  # 100 * 2

    def test_derive_aggregate_with_group_by(self, executor):
        """Aggregate derive: SUM(amount) GROUP BY customer_id."""
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "derive",
                "table": "orders",
                "field": "customer_total",
                "expression": "SUM(amount) GROUP BY customer_id",
                "output": "orders_with_total",
            }
        ])

        rows = executor.execute_sql(
            "SELECT customer_id, customer_total "
            "FROM orders_with_total "
            "ORDER BY customer_id"
        )
        # customer_id=1: 100+200=300, customer_id=2: 50, customer_id=3: 300
        assert rows[0][1] == 300  # Alice
        assert rows[1][1] == 300  # Alice's second order also gets 300
        assert rows[2][1] == 50   # Bob
        assert rows[3][1] == 300  # Charlie


# ===================================================================
# AGGREGATE
# ===================================================================

class TestAggregate:
    def test_group_by_with_sum(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "aggregate",
                "input": "orders",
                "group_by": ["customer_id"],
                "aggregations": [
                    {"function": "SUM", "column": "amount", "alias": "total"},
                    {"function": "COUNT", "column": "*", "alias": "order_count"},
                ],
                "output": "customer_totals",
            }
        ])

        rows = executor.execute_sql(
            "SELECT customer_id, total, order_count "
            "FROM customer_totals ORDER BY customer_id"
        )
        assert len(rows) == 3
        assert rows[0] == (1, 300, 2)  # Alice: 100+200, 2 orders
        assert rows[1] == (2, 50, 1)   # Bob: 50, 1 order
        assert rows[2] == (3, 300, 1)  # Charlie: 300, 1 order

    def test_aggregate_with_string_expressions(self, executor):
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "aggregate",
                "input": "orders",
                "group_by": "status",
                "aggregations": [
                    "SUM(amount) AS total_amount",
                    "COUNT(*) AS cnt",
                ],
                "output": "status_summary",
            }
        ])

        rows = executor.execute_sql(
            "SELECT status, total_amount, cnt "
            "FROM status_summary ORDER BY status"
        )
        assert len(rows) == 3
        # active: 100+200=300, 2 orders
        assert rows[0] == ("active", 300, 2)
        # complete: 300, 1 order
        assert rows[1] == ("complete", 300, 1)
        # pending: 50, 1 order
        assert rows[2] == ("pending", 50, 1)

    def test_aggregate_missing_fields(self, executor):
        engine = TransformEngine(executor)
        with pytest.raises(TransformError, match="requires"):
            engine.execute_transforms([
                {"operation": "aggregate", "input": "orders"}
            ])


# ===================================================================
# Sequential Transforms
# ===================================================================

class TestSequentialTransforms:
    def test_filter_then_aggregate(self, executor):
        """Filter active orders, then aggregate."""
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "filter",
                "input": "orders",
                "expression": "status = 'active'",
                "output": "active_orders",
            },
            {
                "operation": "aggregate",
                "input": "active_orders",
                "group_by": ["customer_id"],
                "aggregations": [
                    {"function": "SUM", "column": "amount", "alias": "total"},
                ],
                "output": "active_totals",
            },
        ])

        rows = executor.execute_sql(
            "SELECT customer_id, total FROM active_totals ORDER BY customer_id"
        )
        # Only customer_id=1 has active orders: 100+200=300
        assert len(rows) == 1
        assert rows[0] == (1, 300)

    def test_join_then_filter(self, executor):
        """Join customers and orders, then filter."""
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        engine.execute_transforms([
            {
                "operation": "join",
                "left": "customers",
                "right": "orders",
                "on": "customers.id = orders.customer_id",
                "type": "inner",
                "output": "joined",
            },
            {
                "operation": "filter",
                "input": "joined",
                "expression": "tier = 'gold'",
                "output": "gold_orders",
            },
        ])

        rows = executor.execute_sql("SELECT COUNT(*) FROM gold_orders")
        # Gold customers: Alice(2 orders) + Charlie(1 order) = 3
        assert rows[0][0] == 3

    def test_skips_unknown_operations(self, executor):
        """Non-transform operations like 'classify' should be skipped."""
        _load_standard_data(executor)
        engine = TransformEngine(executor)

        # Should not raise
        engine.execute_transforms([
            {"operation": "classify", "auto": True},
            {
                "operation": "filter",
                "input": "orders",
                "expression": "amount > 0",
                "output": "positive_orders",
            },
        ])

        rows = executor.execute_sql("SELECT COUNT(*) FROM positive_orders")
        assert rows[0][0] == 4
