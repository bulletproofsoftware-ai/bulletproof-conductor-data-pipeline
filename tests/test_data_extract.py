"""
Tests for the data_extract MCP tool.

Validates:
- Contract enforcement (CISO-CRITICAL-001):
  - No contract -> CONTRACT_REQUIRED error
  - Incomplete contract -> CONTRACT_INCOMPLETE error
  - Valid contract -> success
- dry_run without contract
- Schema drift (missing column -> error, new column -> warning)
- Lineage emitted
"""

import hashlib
import json
import pytest
from unittest.mock import MagicMock

from tools.data_extract import execute


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_contract(
    pipeline_ref: str = "pipe-001",
    columns: dict = None,
) -> dict:
    """Build a test data contract."""
    if columns is None:
        columns = {
            "customers.id": {"classification": "internal", "pii": False},
            "customers.name": {"classification": "confidential", "pii": True, "pii_type": "PERSON"},
            "customers.email": {"classification": "confidential", "pii": True, "pii_type": "EMAIL"},
            "customers.phone": {"classification": "confidential", "pii": True, "pii_type": "PHONE"},
            "customers.address": {"classification": "restricted", "pii": True, "pii_type": "ADDRESS"},
            "customers.created_at": {"classification": "internal", "pii": False},
            "customers.tier": {"classification": "public", "pii": False},
        }
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "DataContract",
        "metadata": {
            "pipeline_ref": pipeline_ref,
            "steward": "test-steward",
            "reviewed_at": "2026-03-18T14:30:00Z",
            "classification_version": 1,
        },
        "columns": columns,
        "governance": {
            "human_review_required": True,
            "retention_days": 90,
            "audit_frequency": "weekly",
        },
        "quality_signoff": True,
    }


@pytest.fixture
def contract():
    return _make_contract()


@pytest.fixture
def mock_emitter():
    emitter = MagicMock()
    emitter.emit.return_value = MagicMock(success=True)
    return emitter


# ---------------------------------------------------------------------------
# Contract Enforcement Tests (CISO-CRITICAL-001)
# ---------------------------------------------------------------------------

class TestContractEnforcement:
    """CISO-CRITICAL-001: No extraction without contract."""

    def test_no_contract_returns_contract_required(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers"}],
            # No contract provided
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "CONTRACT_REQUIRED"

    def test_incomplete_contract_returns_error(self):
        """Contract missing columns that are being extracted."""
        contract = _make_contract(columns={
            "customers.id": {"classification": "internal", "pii": False},
            # Missing customers.name, customers.email, etc.
        })
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id", "name"]}],
            "contract": contract,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "CONTRACT_INCOMPLETE"
        assert "customers.name" in result["data"]["message"]

    def test_valid_contract_succeeds(self, contract, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id", "name", "email"]}],
            "contract": contract,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert "customers" in result["data"]["tables"]

    def test_contract_hash_validation_passes(self, contract):
        """Valid contract hash should pass."""
        contract_hash = hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()
        ).hexdigest()
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id"]}],
            "contract": contract,
            "contract_hash": f"sha256:{contract_hash}",
        })
        assert result["status"] == "success"

    def test_contract_hash_validation_fails_on_tamper(self, contract):
        """Tampered contract hash should fail."""
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id"]}],
            "contract": contract,
            "contract_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "CONTRACT_TAMPERED"


# ---------------------------------------------------------------------------
# Dry Run Tests
# ---------------------------------------------------------------------------

class TestDryRun:
    """dry_run=true should return schema info without requiring a contract."""

    def test_dry_run_without_contract_succeeds(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers"}],
            "dry_run": True,
        })
        assert result["status"] == "success"
        assert result["data"]["dry_run"] is True
        assert "customers" in result["data"]["tables"]

    def test_dry_run_returns_schema(self):
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers"}],
            "dry_run": True,
        })
        table_info = result["data"]["tables"]["customers"]
        assert "columns" in table_info
        assert "row_count" in table_info
        assert table_info["row_count"] > 0

    def test_dry_run_without_contract_omits_sample(self):
        """Without a contract, dry_run must NOT return sample rows (PII leak prevention)."""
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers"}],
            "dry_run": True,
        })
        assert "sample" not in result["data"]["tables"]["customers"]

    def test_dry_run_with_contract_returns_sample(self):
        """With a contract present, dry_run returns sample rows."""
        contract = _make_contract()
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers"}],
            "dry_run": True,
            "contract": contract,
        })
        sample = result["data"]["tables"]["customers"]["sample"]
        assert len(sample) <= 5
        assert len(sample) > 0


# ---------------------------------------------------------------------------
# Schema Drift Tests
# ---------------------------------------------------------------------------

class TestSchemaDrift:
    """Schema drift detection per spec Section 12.10."""

    def test_missing_column_in_source_returns_schema_drift(self, contract):
        """Requesting a column not in source -> SCHEMA_DRIFT."""
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id", "nonexistent_column"]}],
            "contract": _make_contract(columns={
                "customers.id": {"classification": "internal", "pii": False},
                "customers.nonexistent_column": {"classification": "internal", "pii": False},
            }),
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "SCHEMA_DRIFT"
        assert "nonexistent_column" in result["data"]["message"]

    def test_new_column_in_source_generates_warning(self, mock_emitter):
        """Source has columns not in contract -> warning, not error."""
        # Contract covers only 'id', but source has more columns
        contract = _make_contract(columns={
            "customers.id": {"classification": "internal", "pii": False},
        })
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id"]}],
            "contract": contract,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        # Warnings about extra columns in source
        assert "warnings" in result["data"]
        assert len(result["data"]["warnings"]) > 0


# ---------------------------------------------------------------------------
# Lineage Emission Tests
# ---------------------------------------------------------------------------

class TestLineageEmission:
    """Lineage events should be emitted for each extracted table."""

    def test_lineage_emitted_for_extraction(self, contract, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id", "name"]}],
            "contract": contract,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert mock_emitter.emit.called
        assert result["metadata"]["lineage_events_emitted"] >= 1

    def test_lineage_event_has_correct_operation(self, contract, mock_emitter):
        execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id"]}],
            "contract": contract,
            "lineage_emitter": mock_emitter,
        })
        call_args = mock_emitter.emit.call_args[0][0]
        assert call_args["event"]["operation"] == "extract"
        assert call_args["event"]["pipeline_id"] == "pipe-001"

    def test_multiple_tables_emit_multiple_events(self, mock_emitter):
        contract = _make_contract(columns={
            "customers.id": {"classification": "internal", "pii": False},
            "orders.id": {"classification": "internal", "pii": False},
        })
        execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [
                {"name": "customers", "columns": ["id"]},
                {"name": "orders", "columns": ["id"]},
            ],
            "contract": contract,
            "lineage_emitter": mock_emitter,
        })
        assert mock_emitter.emit.call_count == 2


# ---------------------------------------------------------------------------
# Cursor Reset Tests
# ---------------------------------------------------------------------------

class TestCursorReset:
    """reset_cursor should be reflected in the result."""

    def test_reset_cursor_flag_in_result(self, contract, mock_emitter):
        result = execute({
            "pipeline_id": "pipe-001",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers", "columns": ["id"]}],
            "contract": contract,
            "reset_cursor": True,
            "lineage_emitter": mock_emitter,
        })
        assert result["status"] == "success"
        assert result["data"]["reset_cursor"] is True
