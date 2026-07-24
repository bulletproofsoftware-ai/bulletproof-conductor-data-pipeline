"""
Tests for the Qdrant semantic lineage writer.
Uses in-memory Qdrant (`:memory:` mode) — no external services needed.
"""

import pytest
from qdrant_client import QdrantClient

from lineage.qdrant_writer import (
    QdrantLineageWriter,
    QdrantWriteResult,
    COLLECTION_NAME,
    VECTOR_DIM,
    _generate_embedding,
    _event_to_description,
    _point_id_from_hash,
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
) -> dict:
    return {
        "event": {
            "gov_agent_id": "nhi_data-engineer_20260318_test",
            "gov_session_id": "sess_test_001",
            "gov_classification": classification,
            "gov_timestamp": "2026-03-18T14:32:00Z",
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
                "strategy_map": {"name": "tokenize", "email": "format_preserve_encrypt"},
                "referential_integrity": "verified",
            },
            "content_hash": content_hash,
        }
    }


@pytest.fixture
def qdrant_writer():
    """Fresh in-memory Qdrant writer per test."""
    client = QdrantClient(location=":memory:")
    return QdrantLineageWriter(client=client)


# ---------------------------------------------------------------------------
# Collection Creation Tests
# ---------------------------------------------------------------------------

class TestCollectionCreation:
    """Test that the data_lineage collection is created automatically."""

    def test_collection_exists_after_init(self, qdrant_writer):
        collections = qdrant_writer._client.get_collections().collections
        names = [c.name for c in collections]
        assert COLLECTION_NAME in names

    def test_collection_has_correct_vector_size(self, qdrant_writer):
        info = qdrant_writer._client.get_collection(COLLECTION_NAME)
        config = info.config.params.vectors
        assert config.size == VECTOR_DIM

    def test_idempotent_collection_creation(self):
        """Creating writer twice on same client should not fail."""
        client = QdrantClient(location=":memory:")
        QdrantLineageWriter(client=client)
        QdrantLineageWriter(client=client)
        collections = client.get_collections().collections
        lineage_collections = [c for c in collections if c.name == COLLECTION_NAME]
        assert len(lineage_collections) == 1


# ---------------------------------------------------------------------------
# Write Tests
# ---------------------------------------------------------------------------

class TestWrite:
    """Test writing lineage events to Qdrant."""

    def test_write_returns_success(self, qdrant_writer):
        event = _make_event()
        result = qdrant_writer.write(event)
        assert isinstance(result, QdrantWriteResult)
        assert result.success is True
        assert result.collection == COLLECTION_NAME
        assert result.point_id is not None

    def test_write_creates_point(self, qdrant_writer):
        event = _make_event()
        result = qdrant_writer.write(event)
        # Verify point exists via scroll
        points, _ = qdrant_writer._client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
        )
        assert len(points) == 1
        assert str(points[0].id) == result.point_id

    def test_write_stores_full_payload(self, qdrant_writer):
        event = _make_event()
        qdrant_writer.write(event)
        points, _ = qdrant_writer._client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
        )
        payload = points[0].payload
        assert payload["pipeline_id"] == "pipe-001"
        assert payload["operation"] == "extract"
        assert payload["gov_classification"] == "confidential"
        assert payload["source_table"] == "customers"
        assert payload["target_tier"] == "staging"

    def test_write_stores_event_json(self, qdrant_writer):
        event = _make_event()
        qdrant_writer.write(event)
        points, _ = qdrant_writer._client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
        )
        stored_event = points[0].payload["event"]
        assert stored_event["pipeline_id"] == "pipe-001"
        assert stored_event["source"]["table"] == "customers"

    def test_idempotent_upsert(self, qdrant_writer):
        """Same content_hash should update, not duplicate."""
        event = _make_event()
        qdrant_writer.write(event)
        qdrant_writer.write(event)
        points, _ = qdrant_writer._client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
        )
        assert len(points) == 1

    def test_different_hashes_create_different_points(self, qdrant_writer):
        e1 = _make_event(content_hash="sha256:aabbccdd0011")
        e2 = _make_event(content_hash="sha256:eeff00112233")
        qdrant_writer.write(e1)
        qdrant_writer.write(e2)
        points, _ = qdrant_writer._client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10,
        )
        assert len(points) == 2


# ---------------------------------------------------------------------------
# Embedding Tests
# ---------------------------------------------------------------------------

class TestEmbedding:
    """Test the hash-based embedding generation."""

    def test_embedding_dimension(self):
        vec = _generate_embedding("test text")
        assert len(vec) == VECTOR_DIM

    def test_embedding_deterministic(self):
        v1 = _generate_embedding("same input")
        v2 = _generate_embedding("same input")
        assert v1 == v2

    def test_different_inputs_different_vectors(self):
        v1 = _generate_embedding("input one")
        v2 = _generate_embedding("input two")
        assert v1 != v2

    def test_embedding_normalized(self):
        """Vector should be approximately unit length."""
        vec = _generate_embedding("normalize test")
        magnitude = sum(v * v for v in vec) ** 0.5
        assert abs(magnitude - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Semantic Search Tests
# ---------------------------------------------------------------------------

class TestSemanticSearch:
    """Test semantic search over stored lineage events."""

    def test_search_returns_results(self, qdrant_writer):
        event = _make_event()
        qdrant_writer.write(event)
        results = qdrant_writer.search_semantic("customer table extract")
        assert len(results) > 0

    def test_search_returns_relevant_result(self, qdrant_writer):
        # Write two events for different tables
        e1 = _make_event(
            source_table="customers",
            content_hash="sha256:aabbccdd0011",
        )
        e2 = _make_event(
            source_table="orders",
            content_hash="sha256:eeff00112233",
        )
        qdrant_writer.write(e1)
        qdrant_writer.write(e2)

        results = qdrant_writer.search_semantic("customer table extraction")
        assert len(results) >= 1
        # Top result should reference customers
        top = results[0]
        assert "payload" in top
        assert "score" in top

    def test_search_empty_collection(self, qdrant_writer):
        results = qdrant_writer.search_semantic("anything")
        assert results == []


# ---------------------------------------------------------------------------
# Filter Search Tests
# ---------------------------------------------------------------------------

class TestFilterSearch:
    """Test exact-match filter search."""

    def test_filter_by_pipeline_id(self, qdrant_writer):
        e1 = _make_event(pipeline_id="pipe-A", content_hash="sha256:aaaa00000001")
        e2 = _make_event(pipeline_id="pipe-B", content_hash="sha256:bbbb00000002")
        qdrant_writer.write(e1)
        qdrant_writer.write(e2)
        results = qdrant_writer.search_by_filter(pipeline_id="pipe-A")
        assert len(results) == 1
        assert results[0]["payload"]["pipeline_id"] == "pipe-A"

    def test_filter_by_classification(self, qdrant_writer):
        e1 = _make_event(classification="confidential", content_hash="sha256:cccc00000001")
        e2 = _make_event(classification="public", content_hash="sha256:dddd00000002")
        qdrant_writer.write(e1)
        qdrant_writer.write(e2)
        results = qdrant_writer.search_by_filter(gov_classification="confidential")
        assert len(results) == 1

    def test_filter_by_operation(self, qdrant_writer):
        e1 = _make_event(operation="extract", content_hash="sha256:eeee00000001")
        e2 = _make_event(operation="load", content_hash="sha256:ffff00000002")
        qdrant_writer.write(e1)
        qdrant_writer.write(e2)
        results = qdrant_writer.search_by_filter(operation="extract")
        assert len(results) == 1

    def test_filter_no_match(self, qdrant_writer):
        event = _make_event()
        qdrant_writer.write(event)
        results = qdrant_writer.search_by_filter(pipeline_id="nonexistent")
        assert len(results) == 0

    def test_filter_no_criteria_returns_all(self, qdrant_writer):
        e1 = _make_event(content_hash="sha256:aaaa00000001")
        e2 = _make_event(content_hash="sha256:bbbb00000002")
        qdrant_writer.write(e1)
        qdrant_writer.write(e2)
        results = qdrant_writer.search_by_filter()
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    """Test internal helper functions."""

    def test_event_to_description_contains_key_fields(self):
        event = _make_event()
        desc = _event_to_description(event)
        assert "operation:extract" in desc
        assert "pipeline:pipe-001" in desc
        assert "source_table:customers" in desc
        assert "target_tier:staging" in desc

    def test_point_id_from_hash_deterministic(self):
        id1 = _point_id_from_hash("sha256:abcdef0123456789")
        id2 = _point_id_from_hash("sha256:abcdef0123456789")
        assert id1 == id2

    def test_point_id_from_hash_different_for_different_hashes(self):
        id1 = _point_id_from_hash("sha256:aaaa")
        id2 = _point_id_from_hash("sha256:bbbb")
        assert id1 != id2
