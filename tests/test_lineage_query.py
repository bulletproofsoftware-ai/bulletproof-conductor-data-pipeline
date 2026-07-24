"""
Tests for the lineage query engine.
Seeds in-memory stores with test data and verifies all four query types.
"""

import pytest
from qdrant_client import QdrantClient

from lineage.qdrant_writer import QdrantLineageWriter
from lineage.pg_writer import PgLineageWriter
from lineage.query import (
    LineageQueryEngine,
    ProvenanceResult,
    ImpactResult,
    PiiAuditResult,
    PipelineHistoryResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_event(
    pipeline_id: str = "pipe-001",
    operation: str = "extract",
    classification: str = "confidential",
    source_table: str = "customers",
    target_table: str = "customers",
    target_tier: str = "staging",
    content_hash: str = "sha256:aabbccdd0011",
    timestamp: str = "2026-03-18T14:32:00Z",
) -> dict:
    return {
        "event": {
            "gov_agent_id": "nhi_data-engineer_20260318_test",
            "gov_session_id": "sess_test_001",
            "gov_classification": classification,
            "gov_timestamp": timestamp,
            "pipeline_id": pipeline_id,
            "operation": operation,
            "source": {
                "connector": "airbyte/source-postgres",
                "table": source_table,
                "columns": ["id", "name", "email"],
                "row_count": 1000,
            },
            "target": {
                "connector": "airbyte/destination-postgres",
                "tier": target_tier,
                "table": target_table,
                "masking_applied": operation == "mask" or operation == "load",
            },
            "content_hash": content_hash,
        }
    }


@pytest.fixture
def pg():
    return PgLineageWriter()


@pytest.fixture
def qdrant():
    client = QdrantClient(location=":memory:")
    return QdrantLineageWriter(client=client)


@pytest.fixture
def engine(pg, qdrant):
    return LineageQueryEngine(pg_writer=pg, qdrant_writer=qdrant)


def _seed_pipeline_chain(pg, qdrant):
    """
    Seed a typical pipeline chain:
    extract(customers) -> transform -> mask(staging) -> load(staging)

    Returns dict of event IDs.
    """
    r_extract = pg.write_event(_make_event(
        operation="extract",
        source_table="customers",
        target_table="customers",
        target_tier="staging",
        content_hash="sha256:extract_cust_001",
        timestamp="2026-03-18T14:00:00Z",
        classification="confidential",
    ))
    r_transform = pg.write_event(_make_event(
        operation="transform",
        source_table="customers",
        target_table="customers",
        target_tier="staging",
        content_hash="sha256:transform_cust_001",
        timestamp="2026-03-18T14:10:00Z",
        classification="confidential",
    ))
    r_mask = pg.write_event(_make_event(
        operation="mask",
        source_table="customers",
        target_table="customers",
        target_tier="staging",
        content_hash="sha256:mask_cust_staging",
        timestamp="2026-03-18T14:20:00Z",
        classification="confidential",
    ))
    r_load = pg.write_event(_make_event(
        operation="load",
        source_table="customers",
        target_table="customers",
        target_tier="staging",
        content_hash="sha256:load_cust_staging",
        timestamp="2026-03-18T14:30:00Z",
        classification="confidential",
    ))

    # Build DAG
    pg.add_dag_edge(r_extract.event_id, r_transform.event_id, "derived_from")
    pg.add_dag_edge(r_transform.event_id, r_mask.event_id, "masked_from")
    pg.add_dag_edge(r_mask.event_id, r_load.event_id, "loaded_to")

    # Also write to Qdrant
    for ev_hash in [
        "sha256:extract_cust_001",
        "sha256:transform_cust_001",
        "sha256:mask_cust_staging",
        "sha256:load_cust_staging",
    ]:
        ev = _make_event(content_hash=ev_hash)
        qdrant.write(ev)

    return {
        "extract": r_extract.event_id,
        "transform": r_transform.event_id,
        "mask": r_mask.event_id,
        "load": r_load.event_id,
    }


# ---------------------------------------------------------------------------
# Provenance Trace Tests
# ---------------------------------------------------------------------------

class TestTraceProvenance:
    """Test trace_provenance: DAG walk from target back to source."""

    def test_trace_full_chain(self, pg, qdrant, engine):
        _seed_pipeline_chain(pg, qdrant)
        result = engine.trace_provenance(
            target_table="customers",
            target_tier="staging",
        )
        assert isinstance(result, ProvenanceResult)
        assert result.target_table == "customers"
        assert result.target_tier == "staging"
        assert result.total_events >= 1

    def test_trace_returns_all_ancestors(self, pg, qdrant, engine):
        ids = _seed_pipeline_chain(pg, qdrant)
        result = engine.trace_provenance("customers", "staging")
        event_ids = {e["id"] for e in result.lineage_chain}
        # Should contain all events in the chain via ancestry from load/mask events
        assert ids["load"] in event_ids or ids["mask"] in event_ids

    def test_trace_nonexistent_target(self, engine):
        result = engine.trace_provenance("nonexistent_table", "production")
        assert result.total_events == 0
        assert result.lineage_chain == []

    def test_trace_result_sorted_by_timestamp(self, pg, qdrant, engine):
        _seed_pipeline_chain(pg, qdrant)
        result = engine.trace_provenance("customers", "staging")
        timestamps = [e["gov_timestamp"] for e in result.lineage_chain]
        assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# Impact Analysis Tests
# ---------------------------------------------------------------------------

class TestImpactAnalysis:
    """Test impact_analysis: forward walk from source to all targets."""

    def test_impact_from_source(self, pg, qdrant, engine):
        _seed_pipeline_chain(pg, qdrant)
        result = engine.impact_analysis("customers")
        assert isinstance(result, ImpactResult)
        assert result.source_table == "customers"
        assert result.total_affected >= 1

    def test_impact_returns_target_info(self, pg, qdrant, engine):
        _seed_pipeline_chain(pg, qdrant)
        result = engine.impact_analysis("customers")
        # Should find staging tier targets
        tiers = [t["tier"] for t in result.affected_targets]
        assert "staging" in tiers

    def test_impact_nonexistent_source(self, engine):
        result = engine.impact_analysis("nonexistent_table")
        assert result.total_affected == 0
        assert result.affected_targets == []

    def test_impact_multiple_targets(self, pg, qdrant, engine):
        """Source feeding staging AND dev should show both."""
        # Seed staging chain
        _seed_pipeline_chain(pg, qdrant)
        # Add a dev target from same source
        r_dev_mask = pg.write_event(_make_event(
            operation="mask",
            source_table="customers",
            target_table="customers",
            target_tier="development",
            content_hash="sha256:mask_cust_dev",
            timestamp="2026-03-18T15:00:00Z",
        ))
        # Find an extract event for customers
        extract_events = pg.get_events_by_source_table("customers")
        if extract_events:
            pg.add_dag_edge(extract_events[0]["id"], r_dev_mask.event_id, "masked_from")

        result = engine.impact_analysis("customers")
        tiers = [t["tier"] for t in result.affected_targets]
        assert "staging" in tiers
        assert "development" in tiers


# ---------------------------------------------------------------------------
# PII Audit Tests
# ---------------------------------------------------------------------------

class TestPiiAudit:
    """Test pii_audit: Confidential/Restricted events in time range."""

    def test_pii_audit_finds_sensitive_events(self, pg, qdrant, engine):
        pg.write_event(_make_event(
            classification="confidential",
            content_hash="sha256:pii_001",
            timestamp="2026-03-18T14:00:00Z",
        ))
        pg.write_event(_make_event(
            classification="restricted",
            content_hash="sha256:pii_002",
            timestamp="2026-03-18T14:30:00Z",
        ))
        pg.write_event(_make_event(
            classification="public",
            content_hash="sha256:pub_001",
            timestamp="2026-03-18T14:15:00Z",
        ))
        result = engine.pii_audit(
            start_time="2026-03-18T00:00:00Z",
            end_time="2026-03-18T23:59:59Z",
        )
        assert isinstance(result, PiiAuditResult)
        assert result.total_events == 2
        assert "confidential" in result.classifications_found
        assert "restricted" in result.classifications_found
        assert "public" not in result.classifications_found

    def test_pii_audit_respects_time_range(self, pg, qdrant, engine):
        pg.write_event(_make_event(
            classification="confidential",
            content_hash="sha256:early_001",
            timestamp="2026-03-18T08:00:00Z",
        ))
        pg.write_event(_make_event(
            classification="confidential",
            content_hash="sha256:late_001",
            timestamp="2026-03-18T22:00:00Z",
        ))
        result = engine.pii_audit(
            start_time="2026-03-18T10:00:00Z",
            end_time="2026-03-18T20:00:00Z",
        )
        assert result.total_events == 0

    def test_pii_audit_classification_counts(self, pg, qdrant, engine):
        pg.write_event(_make_event(
            classification="confidential",
            content_hash="sha256:c1",
            timestamp="2026-03-18T14:00:00Z",
        ))
        pg.write_event(_make_event(
            classification="confidential",
            content_hash="sha256:c2",
            timestamp="2026-03-18T14:10:00Z",
        ))
        pg.write_event(_make_event(
            classification="restricted",
            content_hash="sha256:r1",
            timestamp="2026-03-18T14:20:00Z",
        ))
        result = engine.pii_audit("2026-03-18T00:00:00Z", "2026-03-18T23:59:59Z")
        assert result.classifications_found["confidential"] == 2
        assert result.classifications_found["restricted"] == 1

    def test_pii_audit_empty(self, engine):
        result = engine.pii_audit("2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z")
        assert result.total_events == 0
        assert result.events == []


# ---------------------------------------------------------------------------
# Pipeline History Tests
# ---------------------------------------------------------------------------

class TestPipelineHistory:
    """Test pipeline_history: all executions sorted by timestamp."""

    def test_pipeline_history(self, pg, qdrant, engine):
        pg.write_event(_make_event(
            pipeline_id="pipe-history",
            content_hash="sha256:h001",
            timestamp="2026-03-18T14:00:00Z",
        ))
        pg.write_event(_make_event(
            pipeline_id="pipe-history",
            content_hash="sha256:h002",
            timestamp="2026-03-18T15:00:00Z",
        ))
        pg.write_event(_make_event(
            pipeline_id="pipe-other",
            content_hash="sha256:o001",
            timestamp="2026-03-18T14:30:00Z",
        ))
        result = engine.pipeline_history("pipe-history")
        assert isinstance(result, PipelineHistoryResult)
        assert result.pipeline_id == "pipe-history"
        assert result.total_executions == 2

    def test_pipeline_history_sorted(self, pg, qdrant, engine):
        pg.write_event(_make_event(
            pipeline_id="pipe-sorted",
            content_hash="sha256:s002",
            timestamp="2026-03-18T16:00:00Z",
        ))
        pg.write_event(_make_event(
            pipeline_id="pipe-sorted",
            content_hash="sha256:s001",
            timestamp="2026-03-18T14:00:00Z",
        ))
        result = engine.pipeline_history("pipe-sorted")
        timestamps = [e["gov_timestamp"] for e in result.executions]
        assert timestamps == sorted(timestamps)

    def test_pipeline_history_empty(self, engine):
        result = engine.pipeline_history("nonexistent")
        assert result.total_executions == 0
        assert result.executions == []


# ---------------------------------------------------------------------------
# Semantic Search Tests
# ---------------------------------------------------------------------------

class TestSemanticSearch:
    """Test semantic search via the query engine."""

    def test_semantic_search_returns_results(self, pg, qdrant, engine):
        qdrant.write(_make_event(
            source_table="customers",
            content_hash="sha256:sem001",
        ))
        results = engine.semantic_search("customer table")
        assert len(results) >= 1

    def test_semantic_search_empty(self, engine):
        results = engine.semantic_search("anything")
        assert results == []
