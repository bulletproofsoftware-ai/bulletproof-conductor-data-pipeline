"""
Tests for the PostgreSQL relational lineage writer.
Uses the in-memory dict-based store — no external PostgreSQL needed.
"""

import pytest

from lineage.pg_writer import PgLineageWriter, PgWriteResult, ContractVersion


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
                "masking_applied": True,
            },
            "transformation": {
                "type": "mask",
                "strategy_map": {"name": "tokenize"},
                "referential_integrity": "verified",
            },
            "quality": {
                "assertions_run": 4,
                "assertions_passed": 4,
            },
            "content_hash": content_hash,
        }
    }


@pytest.fixture
def pg():
    """Fresh in-memory PG writer per test."""
    return PgLineageWriter()


# ---------------------------------------------------------------------------
# Event Write Tests
# ---------------------------------------------------------------------------

class TestEventWrite:
    """Test writing lineage events."""

    def test_write_returns_success(self, pg):
        event = _make_event()
        result = pg.write_event(event)
        assert isinstance(result, PgWriteResult)
        assert result.success is True
        assert result.event_id is not None

    def test_write_stores_event(self, pg):
        event = _make_event()
        result = pg.write_event(event)
        stored = pg.get_event(result.event_id)
        assert stored is not None
        assert stored["pipeline_id"] == "pipe-001"
        assert stored["operation"] == "extract"
        assert stored["gov_classification"] == "confidential"
        assert stored["content_hash"] == "sha256:aabbccdd0011"

    def test_write_stores_json_fields(self, pg):
        event = _make_event()
        result = pg.write_event(event)
        stored = pg.get_event(result.event_id)
        assert stored["source_json"]["table"] == "customers"
        assert stored["target_json"]["tier"] == "staging"
        assert stored["transformation_json"]["type"] == "mask"
        assert stored["quality_json"]["assertions_run"] == 4

    def test_write_generates_unique_ids(self, pg):
        e1 = _make_event(content_hash="sha256:aaaa00000001")
        e2 = _make_event(content_hash="sha256:bbbb00000002")
        r1 = pg.write_event(e1)
        r2 = pg.write_event(e2)
        assert r1.event_id != r2.event_id

    def test_get_nonexistent_event_returns_none(self, pg):
        result = pg.get_event("nonexistent-id")
        assert result is None


# ---------------------------------------------------------------------------
# DAG Edge Tests
# ---------------------------------------------------------------------------

class TestDagEdge:
    """Test DAG edge creation and traversal."""

    def _seed_two_events(self, pg):
        """Create parent and child events, return their IDs."""
        r1 = pg.write_event(_make_event(
            operation="extract",
            content_hash="sha256:parent000001",
        ))
        r2 = pg.write_event(_make_event(
            operation="mask",
            content_hash="sha256:child0000001",
        ))
        return r1.event_id, r2.event_id

    def test_add_dag_edge(self, pg):
        parent_id, child_id = self._seed_two_events(pg)
        edge_id = pg.add_dag_edge(parent_id, child_id, "derived_from")
        assert edge_id is not None

    def test_get_children(self, pg):
        parent_id, child_id = self._seed_two_events(pg)
        pg.add_dag_edge(parent_id, child_id, "derived_from")
        children = pg.get_children(parent_id)
        assert len(children) == 1
        assert children[0].child_event_id == child_id
        assert children[0].relationship_type == "derived_from"

    def test_get_parents(self, pg):
        parent_id, child_id = self._seed_two_events(pg)
        pg.add_dag_edge(parent_id, child_id, "masked_from")
        parents = pg.get_parents(child_id)
        assert len(parents) == 1
        assert parents[0].parent_event_id == parent_id
        assert parents[0].relationship_type == "masked_from"

    def test_all_relationship_types(self, pg):
        """All three relationship types should be accepted."""
        for rtype in ["derived_from", "masked_from", "loaded_to"]:
            parent_id, child_id = self._seed_two_events(pg)
            edge_id = pg.add_dag_edge(parent_id, child_id, rtype)
            assert edge_id is not None

    def test_invalid_relationship_type_rejected(self, pg):
        parent_id, child_id = self._seed_two_events(pg)
        with pytest.raises(ValueError, match="Invalid relationship_type"):
            pg.add_dag_edge(parent_id, child_id, "depends_on")

    def test_nonexistent_parent_rejected(self, pg):
        r = pg.write_event(_make_event(content_hash="sha256:child0000001"))
        with pytest.raises(ValueError, match="Parent event not found"):
            pg.add_dag_edge("nonexistent", r.event_id, "derived_from")

    def test_nonexistent_child_rejected(self, pg):
        r = pg.write_event(_make_event(content_hash="sha256:parent000001"))
        with pytest.raises(ValueError, match="Child event not found"):
            pg.add_dag_edge(r.event_id, "nonexistent", "derived_from")


# ---------------------------------------------------------------------------
# DAG Traversal Tests
# ---------------------------------------------------------------------------

class TestDagTraversal:
    """Test DAG traversal (ancestry and descendants)."""

    def _seed_chain(self, pg):
        """
        Create a 3-event chain: extract -> transform -> load.
        Returns (extract_id, transform_id, load_id).
        """
        r_extract = pg.write_event(_make_event(
            operation="extract",
            content_hash="sha256:chain_extract",
            timestamp="2026-03-18T14:00:00Z",
        ))
        r_transform = pg.write_event(_make_event(
            operation="transform",
            content_hash="sha256:chain_transform",
            timestamp="2026-03-18T14:10:00Z",
        ))
        r_load = pg.write_event(_make_event(
            operation="load",
            content_hash="sha256:chain_load",
            timestamp="2026-03-18T14:20:00Z",
        ))
        pg.add_dag_edge(r_extract.event_id, r_transform.event_id, "derived_from")
        pg.add_dag_edge(r_transform.event_id, r_load.event_id, "loaded_to")
        return r_extract.event_id, r_transform.event_id, r_load.event_id

    def test_trace_ancestry_from_load(self, pg):
        extract_id, transform_id, load_id = self._seed_chain(pg)
        ancestors = pg.trace_ancestry(load_id)
        ancestor_ids = {a["id"] for a in ancestors}
        # Should include load itself, transform, and extract
        assert load_id in ancestor_ids
        assert transform_id in ancestor_ids
        assert extract_id in ancestor_ids

    def test_trace_descendants_from_extract(self, pg):
        extract_id, transform_id, load_id = self._seed_chain(pg)
        descendants = pg.trace_descendants(extract_id)
        desc_ids = {d["id"] for d in descendants}
        # Should include extract itself, transform, and load
        assert extract_id in desc_ids
        assert transform_id in desc_ids
        assert load_id in desc_ids

    def test_trace_ancestry_single_node(self, pg):
        r = pg.write_event(_make_event(content_hash="sha256:isolated"))
        ancestors = pg.trace_ancestry(r.event_id)
        assert len(ancestors) == 1
        assert ancestors[0]["id"] == r.event_id


# ---------------------------------------------------------------------------
# Query Tests
# ---------------------------------------------------------------------------

class TestQueries:
    """Test query methods."""

    def test_get_events_by_pipeline(self, pg):
        pg.write_event(_make_event(pipeline_id="pipe-A", content_hash="sha256:a001"))
        pg.write_event(_make_event(pipeline_id="pipe-A", content_hash="sha256:a002"))
        pg.write_event(_make_event(pipeline_id="pipe-B", content_hash="sha256:b001"))
        results = pg.get_events_by_pipeline("pipe-A")
        assert len(results) == 2

    def test_get_events_by_pipeline_sorted(self, pg):
        pg.write_event(_make_event(
            pipeline_id="pipe-A",
            content_hash="sha256:a002",
            timestamp="2026-03-18T15:00:00Z",
        ))
        pg.write_event(_make_event(
            pipeline_id="pipe-A",
            content_hash="sha256:a001",
            timestamp="2026-03-18T14:00:00Z",
        ))
        results = pg.get_events_by_pipeline("pipe-A")
        assert results[0]["gov_timestamp"] <= results[1]["gov_timestamp"]

    def test_get_events_by_classification(self, pg):
        pg.write_event(_make_event(classification="confidential", content_hash="sha256:c001"))
        pg.write_event(_make_event(classification="public", content_hash="sha256:p001"))
        pg.write_event(_make_event(classification="restricted", content_hash="sha256:r001"))
        results = pg.get_events_by_classification(["confidential", "restricted"])
        assert len(results) == 2

    def test_get_events_by_classification_with_time_range(self, pg):
        pg.write_event(_make_event(
            classification="confidential",
            content_hash="sha256:t001",
            timestamp="2026-03-18T10:00:00Z",
        ))
        pg.write_event(_make_event(
            classification="confidential",
            content_hash="sha256:t002",
            timestamp="2026-03-18T20:00:00Z",
        ))
        results = pg.get_events_by_classification(
            ["confidential"],
            start_time="2026-03-18T09:00:00Z",
            end_time="2026-03-18T15:00:00Z",
        )
        assert len(results) == 1

    def test_get_events_by_source_table(self, pg):
        pg.write_event(_make_event(source_table="customers", content_hash="sha256:s001"))
        pg.write_event(_make_event(source_table="orders", content_hash="sha256:s002"))
        results = pg.get_events_by_source_table("customers")
        assert len(results) == 1
        assert results[0]["source_json"]["table"] == "customers"

    def test_get_events_by_target(self, pg):
        pg.write_event(_make_event(target_table="customers", target_tier="staging", content_hash="sha256:tt01"))
        pg.write_event(_make_event(target_table="customers", target_tier="dev", content_hash="sha256:tt02"))
        pg.write_event(_make_event(target_table="orders", target_tier="staging", content_hash="sha256:tt03"))
        results = pg.get_events_by_target(target_table="customers", target_tier="staging")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Contract Version Tests
# ---------------------------------------------------------------------------

class TestContractVersions:
    """Test data contract version storage."""

    def test_store_contract_version(self, pg):
        cid = pg.store_contract_version(
            pipeline_ref="pipe-001",
            version=1,
            contract_yaml="columns:\n  id: internal",
            contract_hash="sha256:contract001",
        )
        assert cid is not None

    def test_get_contract_versions(self, pg):
        pg.store_contract_version("pipe-001", 1, "v1 yaml", "sha256:v1hash")
        pg.store_contract_version("pipe-001", 2, "v2 yaml", "sha256:v2hash")
        pg.store_contract_version("pipe-002", 1, "other yaml", "sha256:otherhash")
        versions = pg.get_contract_versions("pipe-001")
        assert len(versions) == 2
        assert versions[0].version == 1
        assert versions[1].version == 2

    def test_get_latest_contract(self, pg):
        pg.store_contract_version("pipe-001", 1, "v1", "sha256:v1h")
        pg.store_contract_version("pipe-001", 2, "v2", "sha256:v2h")
        latest = pg.get_latest_contract("pipe-001")
        assert latest is not None
        assert latest.version == 2
        assert latest.contract_yaml == "v2"

    def test_get_latest_contract_nonexistent(self, pg):
        result = pg.get_latest_contract("nonexistent")
        assert result is None

    def test_contract_version_immutable_fields(self, pg):
        pg.store_contract_version("pipe-001", 1, "yaml content", "sha256:hash1")
        versions = pg.get_contract_versions("pipe-001")
        cv = versions[0]
        assert isinstance(cv, ContractVersion)
        assert cv.pipeline_ref == "pipe-001"
        assert cv.version == 1
        assert cv.contract_yaml == "yaml content"
        assert cv.contract_hash == "sha256:hash1"
        assert cv.created_at is not None
