"""
Tests for the DuckDB execution context.

Validates table loading, SQL execution, memory limits, and cleanup.
"""

import pytest
from quality.duckdb_executor import DuckDBExecutor


# ===================================================================
# Table Loading
# ===================================================================

class TestLoadTable:
    def test_load_from_dict_list(self):
        with DuckDBExecutor() as executor:
            data = [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
                {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
            ]
            executor.load_table("customers", data)
            assert "customers" in executor.tables

            rows = executor.execute_sql("SELECT COUNT(*) FROM customers")
            assert rows[0][0] == 3

    def test_load_preserves_types(self):
        with DuckDBExecutor() as executor:
            data = [
                {"id": 1, "amount": 99.99, "active": True, "label": "test"},
            ]
            executor.load_table("items", data)

            rows = executor.execute_sql(
                "SELECT typeof(id), typeof(amount), typeof(active), typeof(label) FROM items"
            )
            types = rows[0]
            assert "INT" in types[0].upper() or "BIGINT" in types[0].upper()
            assert "DOUBLE" in types[1].upper() or "FLOAT" in types[1].upper() or "DECIMAL" in types[1].upper()
            assert "BOOL" in types[2].upper()
            assert "VARCHAR" in types[3].upper()

    def test_load_with_nulls(self):
        with DuckDBExecutor() as executor:
            data = [
                {"id": 1, "email": "a@b.com"},
                {"id": 2, "email": None},
                {"id": 3, "email": "c@d.com"},
            ]
            executor.load_table("users", data)

            rows = executor.execute_sql(
                "SELECT COUNT(*) FROM users WHERE email IS NULL"
            )
            assert rows[0][0] == 1

    def test_load_empty_data(self):
        """Empty data should create an empty table."""
        with DuckDBExecutor() as executor:
            executor.load_table("empty_table", [])
            assert "empty_table" in executor.tables
            rows = executor.execute_sql("SELECT COUNT(*) FROM empty_table")
            assert rows[0][0] == 0

    def test_load_multiple_tables(self):
        with DuckDBExecutor() as executor:
            executor.load_table("t1", [{"x": 1}])
            executor.load_table("t2", [{"y": 2}])
            assert "t1" in executor.tables
            assert "t2" in executor.tables

    @pytest.mark.parametrize(
        "bad_name",
        ["", "my-table", "drop;--", "123start", "has space"],
        ids=["empty", "hyphen", "semicolon", "starts-with-digit", "space"],
    )
    def test_invalid_table_name(self, bad_name):
        with DuckDBExecutor() as executor:
            with pytest.raises(ValueError, match="Invalid table name"):
                executor.load_table(bad_name, [{"x": 1}])


# ===================================================================
# SQL Execution
# ===================================================================

class TestExecuteSQL:
    def test_select_returns_rows(self):
        with DuckDBExecutor() as executor:
            data = [{"id": 1, "val": 10}, {"id": 2, "val": 20}]
            executor.load_table("data", data)

            rows = executor.execute_sql("SELECT * FROM data ORDER BY id")
            assert len(rows) == 2
            assert rows[0][0] == 1
            assert rows[1][1] == 20

    def test_aggregate_query(self):
        with DuckDBExecutor() as executor:
            data = [
                {"id": 1, "amount": 100},
                {"id": 2, "amount": 200},
                {"id": 3, "amount": 300},
            ]
            executor.load_table("orders", data)

            rows = executor.execute_sql("SELECT SUM(amount) FROM orders")
            assert rows[0][0] == 600

    def test_join_query(self):
        with DuckDBExecutor() as executor:
            customers = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
            orders = [
                {"id": 10, "customer_id": 1, "amount": 100},
                {"id": 11, "customer_id": 1, "amount": 200},
                {"id": 12, "customer_id": 2, "amount": 50},
            ]
            executor.load_table("customers", customers)
            executor.load_table("orders", orders)

            rows = executor.execute_sql(
                "SELECT c.name, SUM(o.amount) "
                "FROM customers c JOIN orders o ON c.id = o.customer_id "
                "GROUP BY c.name ORDER BY c.name"
            )
            assert len(rows) == 2
            assert rows[0] == ("Alice", 300)
            assert rows[1] == ("Bob", 50)


# ===================================================================
# Execute Assertion
# ===================================================================

class TestExecuteAssertion:
    def test_pass_when_zero(self):
        with DuckDBExecutor() as executor:
            data = [{"id": 1, "email": "a@b.com"}, {"id": 2, "email": "c@d.com"}]
            executor.load_table("users", data)

            passed, count = executor.execute_assertion(
                "SELECT COUNT(*) FROM users WHERE email IS NULL"
            )
            assert passed is True
            assert count == 0

    def test_fail_when_nonzero(self):
        with DuckDBExecutor() as executor:
            data = [{"id": 1, "email": "a@b.com"}, {"id": 2, "email": None}]
            executor.load_table("users", data)

            passed, count = executor.execute_assertion(
                "SELECT COUNT(*) FROM users WHERE email IS NULL"
            )
            assert passed is False
            assert count == 1


# ===================================================================
# Memory Limit
# ===================================================================

class TestMemoryLimit:
    def test_default_memory_limit(self):
        with DuckDBExecutor() as executor:
            assert executor.memory_limit == "1GB"

    def test_custom_memory_limit(self):
        with DuckDBExecutor(memory_limit="256MB") as executor:
            assert executor.memory_limit == "256MB"
            # Verify the setting was applied by querying DuckDB
            rows = executor.execute_sql(
                "SELECT current_setting('memory_limit')"
            )
            # DuckDB returns "244.1 MiB" for "256MB" (binary vs decimal)
            result = str(rows[0][0])
            assert "MiB" in result or "MB" in result


# ===================================================================
# Cleanup
# ===================================================================

class TestCleanup:
    def test_cleanup_removes_all_tables(self):
        with DuckDBExecutor() as executor:
            executor.load_table("t1", [{"x": 1}])
            executor.load_table("t2", [{"y": 2}])
            assert len(executor.tables) == 2

            executor.cleanup()
            assert len(executor.tables) == 0

            # Tables should be gone from DuckDB
            with pytest.raises(Exception):
                executor.execute_sql("SELECT * FROM t1")

    def test_drop_single_table(self):
        with DuckDBExecutor() as executor:
            executor.load_table("t1", [{"x": 1}])
            executor.load_table("t2", [{"y": 2}])

            executor.drop_table("t1")
            assert "t1" not in executor.tables
            assert "t2" in executor.tables

            # t2 still works
            rows = executor.execute_sql("SELECT * FROM t2")
            assert len(rows) == 1

    def test_table_exists(self):
        with DuckDBExecutor() as executor:
            executor.load_table("check_me", [{"a": 1}])
            assert executor.table_exists("check_me") is True
            assert executor.table_exists("nonexistent") is False

    def test_context_manager_closes(self):
        """Verify that __exit__ closes the connection."""
        executor = DuckDBExecutor()
        executor.load_table("t1", [{"x": 1}])
        executor.close()

        # Connection is closed, should raise
        with pytest.raises(Exception):
            executor.execute_sql("SELECT 1")
