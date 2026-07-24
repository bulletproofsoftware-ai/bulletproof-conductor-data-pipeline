"""
Tests for the data_lineage_query MCP tool.

Validates:
- Provenance trace returns results
- Impact analysis returns targets
- PII audit returns events
- Pipeline history returns executions
"""

import pytest
from unittest.mock import MagicMock

from tools.data_lineage_query import execute


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mock_query_engine():
    """Create a mock LineageQueryEngine with canned responses."""
    engine = MagicMock()

    # Provenance result
    provenance_result = MagicMock()
    provenance_result.target_table = "customers"
    provenance_result.target_tier = "staging"
    provenance_result.lineage_chain = [
        {
            "id": "evt-001",
            "operation": "extract",
            "source_table": "customers",
            "gov_timestamp": "2026-03-18T14:00:00Z",
        },
        {
            "id": "evt-002",
            "operation": "mask",
            "source_table": "customers",
            "gov_timestamp": "2026-03-18T14:01:00Z",
        },
    ]
    provenance_result.total_events = 2
    engine.trace_provenance.return_value = provenance_result

    # Impact analysis result
    impact_result = MagicMock()
    impact_result.source_table = "customers"
    impact_result.affected_targets = [
        {"table": "customers_staging", "tier": "staging", "connector": "pg"},
        {"table": "customers_dev", "tier": "development", "connector": "pg"},
    ]
    impact_result.total_affected = 2
    engine.impact_analysis.return_value = impact_result

    # PII audit result
    pii_result = MagicMock()
    pii_result.start_time = "2026-03-18T00:00:00Z"
    pii_result.end_time = "2026-03-18T23:59:59Z"
    pii_result.events = [
        {"id": "evt-001", "gov_classification": "confidential"},
        {"id": "evt-002", "gov_classification": "restricted"},
    ]
    pii_result.total_events = 2
    pii_result.classifications_found = {"confidential": 1, "restricted": 1}
    engine.pii_audit.return_value = pii_result

    # Pipeline history result
    history_result = MagicMock()
    history_result.pipeline_id = "pipe-001"
    history_result.executions = [
        {"id": "exec-001", "timestamp": "2026-03-18T14:00:00Z", "status": "success"},
        {"id": "exec-002", "timestamp": "2026-03-18T15:00:00Z", "status": "success"},
    ]
    history_result.total_executions = 2
    engine.pipeline_history.return_value = history_result

    return engine


@pytest.fixture
def query_engine():
    return _make_mock_query_engine()


# ---------------------------------------------------------------------------
# Provenance Tests
# ---------------------------------------------------------------------------

class TestProvenanceTrace:
    """Provenance trace should return lineage chain."""

    def test_provenance_returns_results(self, query_engine):
        result = execute({
            "query_type": "provenance",
            "query_engine": query_engine,
            "target_table": "customers",
            "target_tier": "staging",
        })
        assert result["status"] == "success"
        assert result["data"]["query_type"] == "provenance"
        assert result["data"]["target_table"] == "customers"
        assert result["data"]["total_events"] == 2
        assert len(result["data"]["lineage_chain"]) == 2

    def test_provenance_calls_engine(self, query_engine):
        execute({
            "query_type": "provenance",
            "query_engine": query_engine,
            "target_table": "customers",
            "target_tier": "staging",
        })
        query_engine.trace_provenance.assert_called_once_with("customers", "staging")

    def test_provenance_missing_table_returns_error(self, query_engine):
        result = execute({
            "query_type": "provenance",
            "query_engine": query_engine,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "MISSING_PARAM"


# ---------------------------------------------------------------------------
# Impact Analysis Tests
# ---------------------------------------------------------------------------

class TestImpactAnalysis:
    """Impact analysis should return affected targets."""

    def test_impact_returns_targets(self, query_engine):
        result = execute({
            "query_type": "impact_analysis",
            "query_engine": query_engine,
            "source_table": "customers",
        })
        assert result["status"] == "success"
        assert result["data"]["query_type"] == "impact_analysis"
        assert result["data"]["source_table"] == "customers"
        assert result["data"]["total_affected"] == 2
        assert len(result["data"]["affected_targets"]) == 2

    def test_impact_calls_engine(self, query_engine):
        execute({
            "query_type": "impact_analysis",
            "query_engine": query_engine,
            "source_table": "customers",
        })
        query_engine.impact_analysis.assert_called_once_with("customers")

    def test_impact_missing_source_returns_error(self, query_engine):
        result = execute({
            "query_type": "impact_analysis",
            "query_engine": query_engine,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "MISSING_PARAM"


# ---------------------------------------------------------------------------
# PII Audit Tests
# ---------------------------------------------------------------------------

class TestPIIAudit:
    """PII audit should return classified events."""

    def test_pii_audit_returns_events(self, query_engine):
        result = execute({
            "query_type": "pii_audit",
            "query_engine": query_engine,
            "start_time": "2026-03-18T00:00:00Z",
            "end_time": "2026-03-18T23:59:59Z",
        })
        assert result["status"] == "success"
        assert result["data"]["query_type"] == "pii_audit"
        assert result["data"]["total_events"] == 2
        assert "confidential" in result["data"]["classifications_found"]

    def test_pii_audit_missing_times_returns_error(self, query_engine):
        result = execute({
            "query_type": "pii_audit",
            "query_engine": query_engine,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "MISSING_PARAM"


# ---------------------------------------------------------------------------
# Pipeline History Tests
# ---------------------------------------------------------------------------

class TestPipelineHistory:
    """Pipeline history should return executions."""

    def test_history_returns_executions(self, query_engine):
        result = execute({
            "query_type": "pipeline_history",
            "query_engine": query_engine,
            "pipeline_id": "pipe-001",
        })
        assert result["status"] == "success"
        assert result["data"]["query_type"] == "pipeline_history"
        assert result["data"]["pipeline_id"] == "pipe-001"
        assert result["data"]["total_executions"] == 2

    def test_history_missing_pipeline_id_returns_error(self, query_engine):
        result = execute({
            "query_type": "pipeline_history",
            "query_engine": query_engine,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "MISSING_PARAM"


# ---------------------------------------------------------------------------
# Error Tests
# ---------------------------------------------------------------------------

class TestQueryErrors:
    """Error conditions should be handled properly."""

    def test_no_query_type_returns_error(self, query_engine):
        result = execute({
            "query_engine": query_engine,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_QUERY_TYPE"

    def test_invalid_query_type_returns_error(self, query_engine):
        result = execute({
            "query_type": "nonexistent",
            "query_engine": query_engine,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "INVALID_QUERY_TYPE"

    def test_no_query_engine_returns_error(self):
        result = execute({
            "query_type": "provenance",
            "target_table": "customers",
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_QUERY_ENGINE"

    def test_engine_exception_handled(self, query_engine):
        query_engine.trace_provenance.side_effect = Exception("DB connection failed")
        result = execute({
            "query_type": "provenance",
            "query_engine": query_engine,
            "target_table": "customers",
            "target_tier": "staging",
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "QUERY_ERROR"
        assert "DB connection failed" in result["data"]["message"]
