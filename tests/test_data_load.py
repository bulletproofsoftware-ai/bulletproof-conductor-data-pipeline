"""
Tests for the data_load MCP tool.

Validates:
- Atomic load success (staging -> swap)
- Atomic load failure (target unchanged)
- Lineage emitted
"""

import pytest
from unittest.mock import MagicMock

from tools.data_load import execute, SimulatedTargetStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def target_store():
    """Simulated target store."""
    return SimulatedTargetStore()


@pytest.fixture
def target_store_with_data():
    """Target store with pre-existing data."""
    store = SimulatedTargetStore()
    store.set_table("customers", [
        {"id": 1, "name": "Original Alice"},
        {"id": 2, "name": "Original Bob"},
    ])
    return store


@pytest.fixture
def mock_emitter():
    emitter = MagicMock()
    emitter.emit.return_value = MagicMock(success=True)
    return emitter


# ---------------------------------------------------------------------------
# Atomic Load Success Tests
# ---------------------------------------------------------------------------

class TestAtomicLoadSuccess:
    """Successful loads should swap staging tables into targets."""

    def test_single_table_load(self, target_store, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"customers": [{"id": 1, "name": "Alice"}]},
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert "customers" in result["data"]["loaded_tables"]
        assert target_store.get_table("customers") == [{"id": 1, "name": "Alice"}]

    def test_multi_table_load(self, target_store, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {
                "customers": [{"id": 1, "name": "Alice"}],
                "orders": [{"id": 101, "amount": 100}],
            },
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert set(result["data"]["loaded_tables"]) == {"customers", "orders"}
        assert target_store.get_table("customers") is not None
        assert target_store.get_table("orders") is not None

    def test_rows_loaded_counts(self, target_store, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {
                "customers": [{"id": 1}, {"id": 2}, {"id": 3}],
                "orders": [{"id": 101}],
            },
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
        })
        assert result["data"]["rows_loaded"]["customers"] == 3
        assert result["data"]["rows_loaded"]["orders"] == 1


# ---------------------------------------------------------------------------
# Atomic Load Failure Tests
# ---------------------------------------------------------------------------

class TestAtomicLoadFailure:
    """Failed loads must leave target unchanged."""

    def test_failure_leaves_target_unchanged(self, target_store_with_data, mock_emitter):
        """If load fails mid-way, original data stays."""
        original = target_store_with_data.get_table("customers")

        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {
                "customers": [{"id": 99, "name": "New Data"}],
            },
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store_with_data,
            "lineage_emitter": mock_emitter,
            "simulate_failure": "customers",
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "LOAD_FAILED"
        assert result["data"]["target_unchanged"] is True

        # Original data should be intact
        assert target_store_with_data.get_table("customers") == original

    def test_multi_table_failure_rolls_back_all(self, target_store, mock_emitter):
        """If one table fails, no tables should be loaded."""
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {
                "table_a": [{"id": 1}],
                "table_b": [{"id": 2}],
            },
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
            "simulate_failure": "table_b",
        })
        assert result["status"] == "error"
        # Neither table should exist in target
        assert target_store.get_table("table_a") is None
        assert target_store.get_table("table_b") is None


# ---------------------------------------------------------------------------
# Human Gate Tests
# ---------------------------------------------------------------------------

class TestHumanGate:
    """Confidential+ data must require human approval for loading."""

    def test_confidential_requires_gate(self, target_store):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "confidential",
            "target_store": target_store,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"

    def test_restricted_requires_gate(self, target_store):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "restricted",
            "target_store": target_store,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"

    def test_internal_no_gate(self, target_store, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"

    def test_approved_gate_succeeds(self, target_store, mock_emitter):
        # Valid approval token: 64+ lowercase hex characters
        token = "a" * 64
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "confidential",
            "approval_token": token,
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"

    def test_boolean_true_rejected_as_token(self, target_store):
        """A boolean True must NOT bypass the human gate."""
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "confidential",
            "approval_token": True,  # nosec B105 — test fixture deliberately testing bypass attempt
            "target_store": target_store,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"

    def test_short_token_rejected(self, target_store):
        """A short hex string must NOT bypass the human gate."""
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "confidential",
            "approval_token": "abcd1234",  # nosec B105 — test fixture, not a real credential
            "target_store": target_store,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"


# ---------------------------------------------------------------------------
# Lineage Emission Tests
# ---------------------------------------------------------------------------

class TestLineageEmission:
    """Lineage events should be emitted for load operations."""

    def test_lineage_emitted(self, target_store, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
        })
        assert mock_emitter.emit.called

    def test_lineage_event_operation_is_load(self, target_store, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
        })
        event = mock_emitter.emit.call_args[0][0]
        assert event["event"]["operation"] == "load"

    def test_no_lineage_on_failure(self, target_store, mock_emitter):
        """Lineage should not be emitted on load failure."""
        execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "internal",
            "target_store": target_store,
            "lineage_emitter": mock_emitter,
            "simulate_failure": "t",
        })
        assert not mock_emitter.emit.called


# ---------------------------------------------------------------------------
# Error Tests
# ---------------------------------------------------------------------------

class TestLoadErrors:
    """Error conditions should be handled properly."""

    def test_no_dataset_returns_error(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "target_tier": "staging",
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_DATASET"
