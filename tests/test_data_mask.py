"""
Tests for the data_mask MCP tool.

Validates:
- Delegates to masking engine
- Confidential data triggers human gate
- Lineage emitted
"""

import pytest
from unittest.mock import MagicMock

from tools.data_mask import execute


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_public_contract():
    """Contract with only public data."""
    return {
        "columns": {
            "reports.id": {"classification": "public", "pii": False},
            "reports.title": {"classification": "public", "pii": False},
        },
    }


def _make_confidential_contract():
    """Contract with confidential data."""
    return {
        "columns": {
            "customers.id": {"classification": "internal", "pii": False},
            "customers.name": {"classification": "confidential", "pii": True, "pii_type": "PERSON"},
            "customers.email": {"classification": "confidential", "pii": True, "pii_type": "EMAIL"},
        },
    }


def _make_restricted_contract():
    """Contract with restricted data."""
    return {
        "columns": {
            "patients.id": {"classification": "internal", "pii": False},
            "patients.ssn": {"classification": "restricted", "pii": True, "pii_type": "SSN"},
        },
    }


def _make_policy():
    """Standard masking policy."""
    return {
        "defaults": {"strategy": "tokenize"},
        "rules": [
            {"classification": "restricted", "strategy": "redact"},
            {"classification": "confidential", "strategy": "tokenize"},
            {"classification": "public", "strategy": "passthrough"},
        ],
    }


@pytest.fixture
def mock_emitter():
    emitter = MagicMock()
    emitter.emit.return_value = MagicMock(success=True)
    return emitter


# ---------------------------------------------------------------------------
# Masking Delegation Tests
# ---------------------------------------------------------------------------

class TestMaskingDelegation:
    """Tool should delegate to simulated masking engine."""

    def test_public_data_masked_successfully(self, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"reports": [{"id": 1, "title": "Q1 Report"}]},
            "contract": _make_public_contract(),
            "policy": _make_policy(),
            "target_tier": "staging",
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert "masked_dataset" in result["data"]
        assert "strategy_map" in result["data"]

    def test_masked_values_differ_from_original(self, mock_emitter):
        """Confidential data should be transformed."""
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"customers": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
            ]},
            "contract": _make_confidential_contract(),
            "policy": _make_policy(),
            "target_tier": "staging",
            "approval_token": "a" * 64,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        masked_row = result["data"]["masked_dataset"]["customers"][0]
        # Tokenized values should start with TOKEN_
        assert masked_row["name"].startswith("TOKEN_")
        assert masked_row["email"].startswith("TOKEN_")

    def test_redacted_values(self, mock_emitter):
        """Restricted data should be redacted."""
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"patients": [
                {"id": 1, "ssn": "123-45-6789"},
            ]},
            "contract": _make_restricted_contract(),
            "policy": _make_policy(),
            "target_tier": "staging",
            "approval_token": "a" * 64,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        masked_row = result["data"]["masked_dataset"]["patients"][0]
        assert masked_row["ssn"] == "[REDACTED]"

    def test_passthrough_values_unchanged(self, mock_emitter):
        """Public data with passthrough strategy should be unchanged."""
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"reports": [{"id": 1, "title": "Q1"}]},
            "contract": _make_public_contract(),
            "policy": _make_policy(),
            "target_tier": "staging",
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        masked_row = result["data"]["masked_dataset"]["reports"][0]
        assert masked_row["id"] == 1
        assert masked_row["title"] == "Q1"


# ---------------------------------------------------------------------------
# Human Gate Tests
# ---------------------------------------------------------------------------

class TestHumanGate:
    """Confidential+ data must trigger human approval gate."""

    def test_confidential_requires_gate(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"customers": [{"id": 1, "name": "Alice", "email": "a@b.com"}]},
            "contract": _make_confidential_contract(),
            "policy": _make_policy(),
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"
        assert result["data"]["requires_approval"] is True
        assert result["data"]["classification"] == "confidential"

    def test_restricted_requires_gate(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"patients": [{"id": 1, "ssn": "123-45-6789"}]},
            "contract": _make_restricted_contract(),
            "policy": _make_policy(),
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"
        assert result["data"]["classification"] == "restricted"

    def test_public_no_gate(self, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"reports": [{"id": 1, "title": "test"}]},
            "contract": _make_public_contract(),
            "policy": _make_policy(),
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"

    def test_confidential_approved_succeeds(self, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"customers": [{"id": 1, "name": "Alice", "email": "a@b.com"}]},
            "contract": _make_confidential_contract(),
            "policy": _make_policy(),
            "approval_token": "a" * 64,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Lineage Emission Tests
# ---------------------------------------------------------------------------

class TestLineageEmission:
    """Lineage events should be emitted for mask operations."""

    def test_lineage_emitted(self, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "dataset": {"reports": [{"id": 1, "title": "test"}]},
            "contract": _make_public_contract(),
            "policy": _make_policy(),
            "lineage_emitter": mock_emitter,
        })
        assert mock_emitter.emit.called

    def test_lineage_event_operation_is_mask(self, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "dataset": {"reports": [{"id": 1, "title": "test"}]},
            "contract": _make_public_contract(),
            "policy": _make_policy(),
            "lineage_emitter": mock_emitter,
        })
        event = mock_emitter.emit.call_args[0][0]
        assert event["event"]["operation"] == "mask"

    def test_lineage_includes_strategy_map(self, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "dataset": {"reports": [{"id": 1, "title": "test"}]},
            "contract": _make_public_contract(),
            "policy": _make_policy(),
            "lineage_emitter": mock_emitter,
        })
        event = mock_emitter.emit.call_args[0][0]
        assert "strategy_map" in event["event"]["transformation"]


# ---------------------------------------------------------------------------
# Error Tests
# ---------------------------------------------------------------------------

class TestMaskErrors:
    """Error conditions should be handled properly."""

    def test_no_dataset_returns_error(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "contract": _make_public_contract(),
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_DATASET"

    def test_no_contract_returns_error(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "dataset": {"t": [{"a": 1}]},
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_CONTRACT"
