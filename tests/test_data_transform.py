"""
Tests for the data_transform MCP tool.

Validates:
- Delegates to transform engine correctly
- Lineage emitted
"""

import pytest
from unittest.mock import MagicMock

from quality.duckdb_executor import DuckDBExecutor
from tools.data_transform import execute


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def executor():
    """DuckDB executor with test data loaded."""
    ex = DuckDBExecutor()
    ex.load_table("customers", [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Carol", "email": "carol@example.com"},
    ])
    ex.load_table("orders", [
        {"id": 101, "customer_id": 1, "amount": 100},
        {"id": 102, "customer_id": 2, "amount": 200},
        {"id": 103, "customer_id": 1, "amount": 50},
    ])
    return ex


@pytest.fixture
def mock_emitter():
    emitter = MagicMock()
    emitter.emit.return_value = MagicMock(success=True)
    return emitter


# ---------------------------------------------------------------------------
# Delegation Tests
# ---------------------------------------------------------------------------

class TestTransformDelegation:
    """Tool should delegate to TransformEngine."""

    def test_filter_transform(self, executor, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {"operation": "filter", "input": "customers", "expression": "id > 1", "output": "customers_filtered"},
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert result["data"]["transforms_applied"] == 1
        assert "customers_filtered" in result["data"]["new_tables"]

    def test_join_transform(self, executor, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {
                    "operation": "join",
                    "left": "customers",
                    "right": "orders",
                    "on": "customers.id = orders.customer_id",
                    "type": "left",
                    "output": "joined",
                },
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert "joined" in result["data"]["new_tables"]

    def test_derive_transform(self, executor, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {
                    "operation": "derive",
                    "table": "orders",
                    "field": "doubled",
                    "expression": "amount * 2",
                    "output": "orders_derived",
                },
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert "orders_derived" in result["data"]["new_tables"]

    def test_aggregate_transform(self, executor, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {
                    "operation": "aggregate",
                    "input": "orders",
                    "group_by": "customer_id",
                    "aggregations": ["SUM(amount) AS total"],
                    "output": "order_summary",
                },
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert "order_summary" in result["data"]["new_tables"]

    def test_multiple_transforms(self, executor, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {"operation": "filter", "input": "customers", "expression": "id > 0", "output": "cf"},
                {"operation": "filter", "input": "orders", "expression": "amount > 0", "output": "of"},
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert result["data"]["transforms_applied"] == 2


# ---------------------------------------------------------------------------
# Error Tests
# ---------------------------------------------------------------------------

class TestTransformErrors:
    """Transform errors should be reported properly."""

    def test_no_transforms_returns_error(self, executor):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [],
            "executor": executor,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_TRANSFORMS"

    def test_no_executor_returns_error(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [{"operation": "filter"}],
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_EXECUTOR"

    def test_invalid_transform_returns_error(self, executor):
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {"operation": "filter"},  # Missing required fields
            ],
            "executor": executor,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "TRANSFORM_ERROR"


# ---------------------------------------------------------------------------
# Lineage Emission Tests
# ---------------------------------------------------------------------------

class TestLineageEmission:
    """Lineage events should be emitted for transforms."""

    def test_lineage_emitted(self, executor, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {"operation": "filter", "input": "customers", "expression": "id > 0", "output": "cf"},
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        assert mock_emitter.emit.called

    def test_lineage_event_operation_is_transform(self, executor, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {"operation": "filter", "input": "customers", "expression": "id > 0", "output": "cf"},
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        event = mock_emitter.emit.call_args[0][0]
        assert event["event"]["operation"] == "transform"

    def test_lineage_count_matches_transforms(self, executor, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {"operation": "filter", "input": "customers", "expression": "id > 0", "output": "cf"},
                {"operation": "filter", "input": "orders", "expression": "amount > 0", "output": "of"},
            ],
            "executor": executor,
            "lineage_emitter": mock_emitter,
        })
        assert mock_emitter.emit.call_count == 2

    def test_no_emitter_still_succeeds(self, executor):
        """Tool should work without a lineage emitter."""
        result = execute({
            "pipeline_id": "pipe-001",
            "transforms": [
                {"operation": "filter", "input": "customers", "expression": "id > 0", "output": "cf"},
            ],
            "executor": executor,
        })
        assert result["status"] == "success"
