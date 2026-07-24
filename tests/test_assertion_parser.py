"""
Tests for the assertion DSL parser.

Validates that each assertion type parses correctly, invalid syntax
is rejected, and SQL injection attempts are blocked.
"""

import pytest
from quality.assertion_parser import (
    AssertionType,
    AssertionParseError,
    parse_assertion,
)


# ===================================================================
# IS NOT NULL
# ===================================================================

class TestIsNotNull:
    def test_parse_basic(self):
        result = parse_assertion("customers.email IS NOT NULL")
        assert result.assertion_type == AssertionType.IS_NOT_NULL
        assert result.table == "customers"
        assert result.column == "email"
        assert "IS NULL" in result.sql
        assert result.fail_condition == "count > 0"

    def test_parse_case_insensitive(self):
        result = parse_assertion("customers.email is not null")
        assert result.assertion_type == AssertionType.IS_NOT_NULL

    def test_generated_sql(self):
        result = parse_assertion("orders.status IS NOT NULL")
        assert result.sql == "SELECT COUNT(*) FROM orders WHERE status IS NULL"


# ===================================================================
# IS UNIQUE
# ===================================================================

class TestIsUnique:
    def test_parse_basic(self):
        result = parse_assertion("customers.id IS UNIQUE")
        assert result.assertion_type == AssertionType.IS_UNIQUE
        assert result.table == "customers"
        assert result.column == "id"
        assert "DISTINCT" in result.sql

    def test_generated_sql(self):
        result = parse_assertion("orders.id IS UNIQUE")
        assert result.sql == "SELECT COUNT(*) - COUNT(DISTINCT id) FROM orders"


# ===================================================================
# Comparison (>= N, > N, etc.)
# ===================================================================

class TestComparison:
    def test_parse_gte(self):
        result = parse_assertion("orders.amount >= 0")
        assert result.assertion_type == AssertionType.COMPARISON
        assert result.table == "orders"
        assert result.column == "amount"
        assert result.sql == "SELECT COUNT(*) FROM orders WHERE NOT (amount >= 0)"

    def test_parse_gt(self):
        result = parse_assertion("orders.amount > 100")
        assert result.sql == "SELECT COUNT(*) FROM orders WHERE NOT (amount > 100)"

    def test_parse_lte(self):
        result = parse_assertion("orders.amount <= 9999")
        assert result.sql == "SELECT COUNT(*) FROM orders WHERE NOT (amount <= 9999)"

    def test_parse_negative_number(self):
        result = parse_assertion("metrics.score >= -10")
        assert result.sql == "SELECT COUNT(*) FROM metrics WHERE NOT (score >= -10)"

    def test_parse_float(self):
        result = parse_assertion("metrics.rate >= 0.5")
        assert result.sql == "SELECT COUNT(*) FROM metrics WHERE NOT (rate >= 0.5)"


# ===================================================================
# BETWEEN
# ===================================================================

class TestBetween:
    def test_parse_basic(self):
        result = parse_assertion("orders.amount BETWEEN 0 AND 10000")
        assert result.assertion_type == AssertionType.BETWEEN
        assert result.table == "orders"
        assert result.column == "amount"
        assert result.sql == "SELECT COUNT(*) FROM orders WHERE amount NOT BETWEEN 0 AND 10000"

    def test_parse_floats(self):
        result = parse_assertion("metrics.rate BETWEEN 0.0 AND 1.0")
        assert result.sql == "SELECT COUNT(*) FROM metrics WHERE rate NOT BETWEEN 0.0 AND 1.0"


# ===================================================================
# ROW_COUNT
# ===================================================================

class TestRowCount:
    def test_parse_gt(self):
        result = parse_assertion("ROW_COUNT(customers) > 0")
        assert result.assertion_type == AssertionType.ROW_COUNT
        assert result.table == "customers"
        assert result.column is None
        assert result.sql == "SELECT COUNT(*) FROM customers"

    def test_parse_gte(self):
        result = parse_assertion("ROW_COUNT(orders) >= 100")
        assert result.assertion_type == AssertionType.ROW_COUNT
        assert result.sql == "SELECT COUNT(*) FROM orders"


# ===================================================================
# IN VALUES
# ===================================================================

class TestInValues:
    def test_parse_strings(self):
        result = parse_assertion("orders.status IN ('active', 'pending', 'complete')")
        assert result.assertion_type == AssertionType.IN_VALUES
        assert result.table == "orders"
        assert result.column == "status"
        assert "NOT IN" in result.sql
        assert "'active'" in result.sql
        assert "'pending'" in result.sql
        assert "'complete'" in result.sql

    def test_parse_numbers(self):
        result = parse_assertion("orders.tier IN (1, 2, 3)")
        assert result.assertion_type == AssertionType.IN_VALUES
        assert "NOT IN (1, 2, 3)" in result.sql

    def test_parse_mixed(self):
        # Numbers and strings mixed
        result = parse_assertion("items.code IN ('A', 'B', 'C')")
        assert result.assertion_type == AssertionType.IN_VALUES


# ===================================================================
# MATCHES
# ===================================================================

class TestMatches:
    def test_parse_basic(self):
        result = parse_assertion("customers.email MATCHES '^[^@]+@[^@]+\\.[^@]+$'")
        assert result.assertion_type == AssertionType.MATCHES
        assert result.table == "customers"
        assert result.column == "email"
        assert "regexp_matches" in result.sql

    def test_parse_simple_regex(self):
        result = parse_assertion("orders.code MATCHES '^ORD-[0-9]+'")
        assert result.assertion_type == AssertionType.MATCHES
        assert "regexp_matches" in result.sql


# ===================================================================
# COUNT(DISTINCT ...)
# ===================================================================

class TestCountDistinct:
    def test_parse_basic(self):
        result = parse_assertion("COUNT(DISTINCT customers.tier) >= 3")
        assert result.assertion_type == AssertionType.COUNT_DISTINCT
        assert result.table == "customers"
        assert result.column == "tier"
        assert result.sql == "SELECT COUNT(DISTINCT tier) FROM customers"

    def test_parse_gt(self):
        result = parse_assertion("COUNT(DISTINCT orders.status) > 1")
        assert result.assertion_type == AssertionType.COUNT_DISTINCT


# ===================================================================
# CUSTOM ASSERT
# ===================================================================

class TestCustomAssert:
    def test_parse_basic(self):
        custom_sql = "SELECT * FROM customers WHERE email IS NULL AND tier = 'premium'"
        result = parse_assertion(f"ASSERT {custom_sql}")
        assert result.assertion_type == AssertionType.CUSTOM_ASSERT
        assert result.sql == custom_sql
        assert result.table == "__custom__"

    def test_parse_preserves_sql(self):
        sql = "SELECT c.id FROM customers c LEFT JOIN orders o ON c.id = o.customer_id WHERE o.id IS NULL"
        result = parse_assertion(f"ASSERT {sql}")
        assert result.sql == sql


# ===================================================================
# Invalid syntax rejection
# ===================================================================

class TestInvalidSyntax:
    def test_empty_string(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("")

    def test_whitespace_only(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("   ")

    def test_unrecognized_syntax(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("SOMETHING WEIRD")

    def test_missing_table_prefix(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("email IS NOT NULL")

    def test_invalid_column_name_special_chars(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("customers.em@il IS NOT NULL")

    def test_non_numeric_comparison_value(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("orders.amount >= abc")

    def test_assert_empty(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("ASSERT ")


# ===================================================================
# SQL Injection rejection
# ===================================================================

class TestSqlInjection:
    def test_semicolon_drop_table(self):
        with pytest.raises(AssertionParseError, match="injection"):
            parse_assertion("customers.email; DROP TABLE customers")

    def test_comment_injection(self):
        with pytest.raises(AssertionParseError, match="injection"):
            parse_assertion("customers.email -- DROP TABLE customers")

    def test_drop_in_column(self):
        with pytest.raises(AssertionParseError, match="injection"):
            parse_assertion("customers.email DROP TABLE customers")

    def test_update_injection(self):
        with pytest.raises(AssertionParseError, match="injection"):
            parse_assertion("customers.email UPDATE customers SET email='x'")

    def test_delete_injection(self):
        with pytest.raises(AssertionParseError, match="injection"):
            parse_assertion("customers.email DELETE FROM customers")

    def test_insert_injection(self):
        with pytest.raises(AssertionParseError, match="injection"):
            parse_assertion("customers.email INSERT INTO customers VALUES(1)")

    def test_assert_allows_select(self):
        """ASSERT keyword should allow raw SQL (it's audited separately)."""
        result = parse_assertion("ASSERT SELECT * FROM customers WHERE id < 0")
        assert result.assertion_type == AssertionType.CUSTOM_ASSERT

    def test_column_name_with_semicolon(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("customers.ema;il IS NOT NULL")


# ===================================================================
# Column name validation
# ===================================================================

class TestColumnValidation:
    def test_valid_table_column(self):
        result = parse_assertion("my_table.my_column IS NOT NULL")
        assert result.table == "my_table"
        assert result.column == "my_column"

    def test_table_with_numbers(self):
        result = parse_assertion("table2.col3 IS NOT NULL")
        assert result.table == "table2"
        assert result.column == "col3"

    def test_underscore_prefix(self):
        result = parse_assertion("_private.col IS NOT NULL")
        assert result.table == "_private"
        assert result.column == "col"

    def test_rejects_leading_number_in_table(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("2table.col IS NOT NULL")

    def test_rejects_spaces_in_column(self):
        with pytest.raises(AssertionParseError):
            parse_assertion("table.my column IS NOT NULL")
