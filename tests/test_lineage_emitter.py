"""
Tests for the core lineage emitter (dual-write with classification-aware error handling).
"""

import threading
import pytest

from jsonschema import ValidationError

from lineage.emitter import LineageEmitter, LineageWriteError
from lineage.qdrant_writer import QdrantLineageWriter
from lineage.pg_writer import PgLineageWriter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_event(
    classification: str = "internal",
    operation: str = "extract",
    pipeline_id: str = "pipe-test-001",
    content_hash: str = "sha256:aabbccdd0011",
) -> dict:
    """Build a minimal valid lineage event."""
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
                "table": "customers",
                "columns": ["id", "name", "email"],
                "row_count": 1000,
            },
            "target": {
                "connector": "airbyte/destination-postgres",
                "tier": "staging",
                "table": "customers",
                "masking_applied": True,
            },
            "content_hash": content_hash,
        }
    }


@pytest.fixture
def qdrant_writer():
    """In-memory Qdrant writer."""
    from qdrant_client import QdrantClient
    client = QdrantClient(location=":memory:")
    return QdrantLineageWriter(client=client)


@pytest.fixture
def pg_writer():
    """In-memory PG writer."""
    return PgLineageWriter()


@pytest.fixture
def emitter(qdrant_writer, pg_writer):
    """Standard emitter with both writers."""
    return LineageEmitter(qdrant_writer=qdrant_writer, pg_writer=pg_writer)


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------

class TestEventValidation:
    """Test that events are validated against the schema before writing."""

    def test_valid_event_passes_validation(self, emitter):
        event = _make_event()
        result = emitter.emit(event)
        assert result.success is True

    def test_missing_event_wrapper_rejected(self, emitter):
        bad = {"gov_agent_id": "test", "pipeline_id": "p1"}
        with pytest.raises(ValidationError):
            emitter.emit(bad)

    def test_missing_required_field_rejected(self, emitter):
        event = _make_event()
        del event["event"]["pipeline_id"]
        with pytest.raises(ValidationError):
            emitter.emit(event)

    def test_invalid_operation_rejected(self, emitter):
        event = _make_event()
        event["event"]["operation"] = "delete"
        with pytest.raises(ValidationError):
            emitter.emit(event)

    def test_invalid_classification_rejected(self, emitter):
        event = _make_event()
        event["event"]["gov_classification"] = "secret"
        with pytest.raises(ValidationError):
            emitter.emit(event)

    def test_invalid_content_hash_pattern_rejected(self, emitter):
        event = _make_event()
        event["event"]["content_hash"] = "md5:abc123"
        with pytest.raises(ValidationError):
            emitter.emit(event)

    def test_missing_source_rejected(self, emitter):
        event = _make_event()
        del event["event"]["source"]
        with pytest.raises(ValidationError):
            emitter.emit(event)

    def test_missing_target_rejected(self, emitter):
        event = _make_event()
        del event["event"]["target"]
        with pytest.raises(ValidationError):
            emitter.emit(event)


# ---------------------------------------------------------------------------
# Dual-Write Tests
# ---------------------------------------------------------------------------

class TestDualWrite:
    """Test that valid events are written to both stores."""

    def test_writes_to_both_stores(self, emitter):
        event = _make_event()
        result = emitter.emit(event)
        assert result.success is True
        assert result.qdrant_result is not None
        assert result.qdrant_result.success is True
        assert result.pg_result is not None
        assert result.pg_result.success is True

    def test_event_id_returned_from_pg(self, emitter):
        event = _make_event()
        result = emitter.emit(event)
        assert result.pg_result.event_id is not None

    def test_point_id_returned_from_qdrant(self, emitter):
        event = _make_event()
        result = emitter.emit(event)
        assert result.qdrant_result.point_id is not None

    def test_no_warnings_on_success(self, emitter):
        event = _make_event()
        result = emitter.emit(event)
        assert result.has_warnings is False
        assert result.warnings == []


# ---------------------------------------------------------------------------
# Classification-Aware Error Handling Tests
# ---------------------------------------------------------------------------

class _FailingQdrantWriter(QdrantLineageWriter):
    """Qdrant writer that always fails."""

    def write(self, event):
        raise ConnectionError("Qdrant connection refused")


class _FailingPgWriter(PgLineageWriter):
    """PG writer that always fails."""

    def write_event(self, event):
        raise ConnectionError("PostgreSQL connection refused")


class TestClassificationErrorHandling:
    """Test classification-aware error handling per SPEC section 12.9."""

    def test_confidential_qdrant_fail_raises(self, pg_writer):
        """Confidential data: Qdrant failure raises LineageWriteError."""
        failing_qdrant = _FailingQdrantWriter.__new__(_FailingQdrantWriter)
        failing_qdrant.write = lambda event: (_ for _ in ()).throw(
            ConnectionError("Qdrant connection refused")
        )
        emitter = LineageEmitter(
            qdrant_writer=failing_qdrant,
            pg_writer=pg_writer,
            skip_validation=True,
        )
        event = _make_event(classification="confidential")
        with pytest.raises(LineageWriteError) as exc_info:
            emitter.emit(event)
        assert exc_info.value.classification == "confidential"
        assert exc_info.value.failed_store == "qdrant"

    def test_restricted_pg_fail_raises(self, qdrant_writer):
        """Restricted data: PG failure raises LineageWriteError."""
        failing_pg = _FailingPgWriter()
        emitter = LineageEmitter(
            qdrant_writer=qdrant_writer,
            pg_writer=failing_pg,
            skip_validation=True,
        )
        event = _make_event(classification="restricted")
        with pytest.raises(LineageWriteError) as exc_info:
            emitter.emit(event)
        assert exc_info.value.classification == "restricted"
        assert exc_info.value.failed_store == "postgresql"

    def test_public_qdrant_fail_continues_with_warning(self, pg_writer):
        """Public data: Qdrant failure logs LINEAGE_GAP warning."""
        failing_qdrant = _FailingQdrantWriter.__new__(_FailingQdrantWriter)
        failing_qdrant.write = lambda event: (_ for _ in ()).throw(
            ConnectionError("Qdrant connection refused")
        )
        emitter = LineageEmitter(
            qdrant_writer=failing_qdrant,
            pg_writer=pg_writer,
            skip_validation=True,
        )
        event = _make_event(classification="public")
        result = emitter.emit(event)
        # Should not raise, but should have warnings
        assert result.success is False
        assert result.has_warnings is True
        assert any("LINEAGE_GAP" in w for w in result.warnings)

    def test_internal_pg_fail_continues_with_warning(self, qdrant_writer):
        """Internal data: PG failure logs LINEAGE_GAP warning."""
        failing_pg = _FailingPgWriter()
        emitter = LineageEmitter(
            qdrant_writer=qdrant_writer,
            pg_writer=failing_pg,
            skip_validation=True,
        )
        event = _make_event(classification="internal")
        result = emitter.emit(event)
        assert result.success is False
        assert result.has_warnings is True
        assert any("LINEAGE_GAP" in w for w in result.warnings)

    def test_public_both_fail_continues_with_warning(self):
        """Public data: both stores fail = two LINEAGE_GAP warnings."""
        failing_qdrant = _FailingQdrantWriter.__new__(_FailingQdrantWriter)
        failing_qdrant.write = lambda event: (_ for _ in ()).throw(
            ConnectionError("Qdrant fail")
        )
        failing_pg = _FailingPgWriter()
        emitter = LineageEmitter(
            qdrant_writer=failing_qdrant,
            pg_writer=failing_pg,
            skip_validation=True,
        )
        event = _make_event(classification="public")
        result = emitter.emit(event)
        assert result.success is False
        assert result.has_warnings is True
        assert any("LINEAGE_GAP" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Thread Safety Tests
# ---------------------------------------------------------------------------

class TestThreadSafety:
    """Test that concurrent emits are handled safely."""

    def test_concurrent_emits(self, emitter):
        """Multiple threads can emit without data corruption."""
        errors = []
        results = []

        def emit_event(idx):
            try:
                event = _make_event(
                    content_hash=f"sha256:{idx:012x}",
                    pipeline_id=f"pipe-concurrent-{idx}",
                )
                result = emitter.emit(event)
                results.append(result)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=emit_event, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        assert all(r.success for r in results)


# ---------------------------------------------------------------------------
# Optional Fields Tests
# ---------------------------------------------------------------------------

class TestOptionalFields:
    """Test events with optional fields present/absent."""

    def test_event_with_transformation(self, emitter):
        event = _make_event()
        event["event"]["transformation"] = {
            "type": "mask",
            "strategy_map": {"name": "tokenize", "email": "format_preserve_encrypt"},
            "referential_integrity": "verified",
        }
        result = emitter.emit(event)
        assert result.success is True

    def test_event_with_quality(self, emitter):
        event = _make_event()
        event["event"]["quality"] = {
            "assertions_run": 4,
            "assertions_passed": 4,
        }
        result = emitter.emit(event)
        assert result.success is True

    def test_event_with_all_operations(self, emitter):
        """All four valid operations should succeed."""
        for op in ["extract", "transform", "mask", "load"]:
            event = _make_event(
                operation=op,
                content_hash=f"sha256:{hash(op) & 0xFFFFFFFFFFFF:012x}",
            )
            result = emitter.emit(event)
            assert result.success is True, f"Failed for operation={op}"

    def test_event_with_filter_applied(self, emitter):
        event = _make_event()
        event["event"]["source"]["filter_applied"] = "status = 'active'"
        result = emitter.emit(event)
        assert result.success is True
