"""
Tests for the OpenTelemetry span emitter.
Uses InMemorySpanExporter — no external OTLP collector needed.
"""

import json
import pytest

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from lineage.otel_emitter import OtelEmitter, JsonStdoutExporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_exporter():
    """In-memory span exporter for test assertions."""
    return InMemorySpanExporter()


@pytest.fixture
def otel(memory_exporter):
    """OTel emitter with in-memory exporter."""
    return OtelEmitter(exporter=memory_exporter)


def _get_spans(memory_exporter):
    """Get all finished spans from the exporter."""
    return memory_exporter.get_finished_spans()


# ---------------------------------------------------------------------------
# Pipeline Trace Tests
# ---------------------------------------------------------------------------

class TestPipelineTrace:
    """Test root span creation for pipeline executions."""

    def test_creates_root_span(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318T143200"):
            pass
        spans = _get_spans(memory_exporter)
        assert len(spans) == 1
        assert "pipe-001" in spans[0].name
        assert "20260318T143200" in spans[0].name

    def test_root_span_has_pipeline_attributes(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318T143200"):
            pass
        span = _get_spans(memory_exporter)[0]
        assert span.attributes["pipeline.id"] == "pipe-001"
        assert span.attributes["pipeline.execution_timestamp"] == "20260318T143200"

    def test_child_spans_under_root(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            with otel.operation_span("extract", {"row_count": 1000}):
                pass
            with otel.operation_span("transform.join", {"left": "a", "right": "b"}):
                pass
        spans = _get_spans(memory_exporter)
        # Root + 2 children = 3 spans
        assert len(spans) == 3
        names = [s.name for s in spans]
        assert "extract" in names
        assert "transform.join" in names


# ---------------------------------------------------------------------------
# Operation Span Tests
# ---------------------------------------------------------------------------

class TestOperationSpan:
    """Test individual operation span creation."""

    def test_extract_span(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_extract(
                source_connector="airbyte/source-postgres",
                source_table="customers",
                row_count=45230,
                duration_ms=12300.0,
                filter_applied="status = 'active'",
            )
        spans = _get_spans(memory_exporter)
        extract_spans = [s for s in spans if s.name == "extract"]
        assert len(extract_spans) == 1
        attrs = dict(extract_spans[0].attributes)
        assert attrs["source.connector"] == "airbyte/source-postgres"
        assert attrs["source.table"] == "customers"
        assert attrs["row_count"] == 45230
        assert attrs["duration_ms"] == 12300.0
        assert attrs["filter_applied"] == "status = 'active'"

    def test_transform_span(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_transform(
                transform_type="join",
                details={"left": "customers", "right": "orders"},
                result_row_count=45230,
                duration_ms=5000.0,
            )
        spans = _get_spans(memory_exporter)
        join_spans = [s for s in spans if s.name == "transform.join"]
        assert len(join_spans) == 1
        attrs = dict(join_spans[0].attributes)
        assert attrs["transform.type"] == "join"
        assert attrs["result_row_count"] == 45230

    def test_classify_span(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_classify(
                column_count=13,
                classification_counts={
                    "public": 2,
                    "internal": 5,
                    "confidential": 4,
                    "restricted": 1,
                },
                duration_ms=100.0,
            )
        spans = _get_spans(memory_exporter)
        classify_spans = [s for s in spans if s.name == "classify"]
        assert len(classify_spans) == 1
        attrs = dict(classify_spans[0].attributes)
        assert attrs["column_count"] == 13
        assert attrs["classification.confidential"] == 4
        assert attrs["classification.restricted"] == 1

    def test_mask_span(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_mask(
                target_tier="staging",
                strategy_map={"name": "tokenize", "email": "fpe"},
                referential_integrity="verified",
                row_count=45230,
                duration_ms=8000.0,
            )
        spans = _get_spans(memory_exporter)
        mask_spans = [s for s in spans if s.name == "mask.staging"]
        assert len(mask_spans) == 1
        attrs = dict(mask_spans[0].attributes)
        assert attrs["target.tier"] == "staging"
        assert attrs["referential_integrity"] == "verified"
        strategy = json.loads(attrs["strategy_map"])
        assert strategy["name"] == "tokenize"
        assert strategy["email"] == "fpe"

    def test_quality_gate_span_passed(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_quality_gate(
                assertions_run=4,
                assertions_passed=4,
                passed=True,
                duration_ms=50.0,
            )
        spans = _get_spans(memory_exporter)
        qg_spans = [s for s in spans if s.name == "quality_gate"]
        assert len(qg_spans) == 1
        attrs = dict(qg_spans[0].attributes)
        assert attrs["assertions_run"] == 4
        assert attrs["assertions_passed"] == 4
        assert attrs["assertions_result"] == "passed"

    def test_quality_gate_span_failed(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_quality_gate(
                assertions_run=4,
                assertions_passed=2,
                passed=False,
            )
        spans = _get_spans(memory_exporter)
        qg_spans = [s for s in spans if s.name == "quality_gate"]
        assert len(qg_spans) == 1
        assert qg_spans[0].status.status_code == StatusCode.ERROR

    def test_load_span(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_load(
                target_connector="airbyte/destination-postgres",
                target_table="customers",
                target_tier="staging",
                row_count=45230,
                duration_ms=8700.0,
            )
        spans = _get_spans(memory_exporter)
        load_spans = [s for s in spans if s.name == "load"]
        assert len(load_spans) == 1
        attrs = dict(load_spans[0].attributes)
        assert attrs["target.connector"] == "airbyte/destination-postgres"
        assert attrs["target.table"] == "customers"
        assert attrs["target.tier"] == "staging"
        assert attrs["row_count"] == 45230
        assert attrs["duration_ms"] == 8700.0


# ---------------------------------------------------------------------------
# Full Pipeline Trace Tests
# ---------------------------------------------------------------------------

class TestFullPipelineTrace:
    """Test a full pipeline execution trace matching SPEC section 7.3."""

    def test_full_pipeline_execution(self, otel, memory_exporter):
        """Reproduce the trace from SPEC section 7.3."""
        with otel.pipeline_trace("pipe-001", "20260318"):
            otel.record_extract("airbyte/source-postgres", "customers", 45230, 12300.0)
            otel.record_extract("airbyte/source-postgres", "orders", 128450, 34100.0)
            otel.record_transform("join", {"left": "customers", "right": "orders"}, 45230)
            otel.record_transform("derive", {"field": "lifetime_value"})
            otel.record_classify(13, {"public": 2, "internal": 5, "confidential": 4, "restricted": 1})
            otel.record_mask("staging", {"name": "tokenize", "email": "fpe"}, "verified", 45230)
            otel.record_quality_gate(4, 4, True)
            otel.record_load("airbyte/destination-postgres", "customers", "staging", 45230, 8700.0)

        spans = _get_spans(memory_exporter)
        # Root + 8 operations = 9 spans
        assert len(spans) == 9

        names = [s.name for s in spans]
        assert sum(1 for n in names if n == "extract") == 2
        assert "transform.join" in names
        assert "transform.derive" in names
        assert "classify" in names
        assert "mask.staging" in names
        assert "quality_gate" in names
        assert "load" in names

    def test_span_parent_relationships(self, otel, memory_exporter):
        """Child spans should reference the root span as parent."""
        with otel.pipeline_trace("pipe-001", "20260318"):
            with otel.operation_span("extract"):
                pass
        spans = _get_spans(memory_exporter)
        root = [s for s in spans if "pipe-001" in s.name][0]
        child = [s for s in spans if s.name == "extract"][0]
        # Child's parent should be the root span's context
        assert child.parent is not None
        assert child.parent.span_id == root.context.span_id


# ---------------------------------------------------------------------------
# Fallback / Stdout Exporter Tests
# ---------------------------------------------------------------------------

class TestFallbackExporter:
    """Test that missing OTLP endpoint falls back to JSON stdout."""

    def test_no_otlp_uses_json_stdout(self):
        otel = OtelEmitter()  # No endpoint, no exporter
        assert isinstance(otel.exporter, JsonStdoutExporter)

    def test_json_stdout_exports_spans(self):
        exporter = JsonStdoutExporter()
        otel = OtelEmitter(exporter=exporter)
        with otel.pipeline_trace("pipe-test", "20260318"):
            with otel.operation_span("extract"):
                pass
        otel.shutdown()
        assert len(exporter.exported_spans) >= 1

    def test_json_stdout_span_has_required_fields(self):
        exporter = JsonStdoutExporter()
        otel = OtelEmitter(exporter=exporter)
        with otel.pipeline_trace("pipe-test", "20260318"):
            with otel.operation_span("extract", {"row_count": 100}):
                pass
        otel.shutdown()
        # Find the extract span
        extract_spans = [s for s in exporter.exported_spans if s["name"] == "extract"]
        assert len(extract_spans) == 1
        span = extract_spans[0]
        assert "trace_id" in span
        assert "span_id" in span
        assert "name" in span
        assert "attributes" in span
        assert span["attributes"]["row_count"] == 100


# ---------------------------------------------------------------------------
# Shutdown Tests
# ---------------------------------------------------------------------------

class TestShutdown:
    """Test clean shutdown."""

    def test_shutdown_does_not_raise(self, otel):
        otel.shutdown()

    def test_shutdown_flushes_spans(self, otel, memory_exporter):
        with otel.pipeline_trace("pipe-001", "20260318"):
            pass
        otel.shutdown()
        spans = _get_spans(memory_exporter)
        assert len(spans) >= 1
