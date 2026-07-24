"""
OpenTelemetry Span Emitter for Conductor Data Pipeline.

Creates traces and spans per pipeline execution. Each pipeline
operation (extract, transform, classify, mask, quality_gate, load)
gets its own span with relevant attributes.

If OTLP endpoint is configured, exports to collector.
Otherwise, logs spans as structured JSON to stdout.
"""

import json
import logging
from contextlib import contextmanager
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import StatusCode

logger = logging.getLogger(__name__)


class JsonStdoutExporter(SpanExporter):
    """
    Exports spans as structured JSON to stdout.
    Used when no OTLP endpoint is configured.
    """

    def __init__(self):
        self.exported_spans: list[dict] = []

    def export(self, spans) -> SpanExportResult:
        for span in spans:
            span_data = {
                "trace_id": format(span.context.trace_id, "032x"),
                "span_id": format(span.context.span_id, "016x"),
                "parent_span_id": (
                    format(span.parent.span_id, "016x")
                    if span.parent
                    else None
                ),
                "name": span.name,
                "kind": str(span.kind),
                "start_time": span.start_time,
                "end_time": span.end_time,
                "status": str(span.status.status_code),
                "attributes": dict(span.attributes) if span.attributes else {},
            }
            self.exported_spans.append(span_data)
            logger.info("OTel span: %s", json.dumps(span_data, default=str))
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 0) -> bool:
        return True


class OtelEmitter:
    """
    Creates and manages OpenTelemetry traces/spans for pipeline executions.
    """

    def __init__(
        self,
        otlp_endpoint: Optional[str] = None,
        exporter: Optional[SpanExporter] = None,
        service_name: str = "conductor-data-pipeline",
    ):
        """
        Initialize the OTel emitter.

        Args:
            otlp_endpoint: OTLP collector endpoint URL. If None and no
                          exporter provided, falls back to JSON stdout.
            exporter: Pre-configured span exporter (used in tests with
                     InMemorySpanExporter).
            service_name: OpenTelemetry service name.
        """
        resource = Resource.create({"service.name": service_name})

        self._provider = TracerProvider(resource=resource)

        if exporter is not None:
            self._exporter = exporter
        elif otlp_endpoint:
            # Lazy import — only needed when OTLP endpoint is configured
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            self._exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        else:
            self._exporter = JsonStdoutExporter()

        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        self._tracer = self._provider.get_tracer(service_name)

    @property
    def exporter(self) -> SpanExporter:
        """Access the underlying exporter (for testing)."""
        return self._exporter

    @property
    def tracer(self) -> trace.Tracer:
        """Access the underlying tracer."""
        return self._tracer

    @contextmanager
    def pipeline_trace(self, pipeline_id: str, execution_timestamp: str):
        """
        Context manager that creates a root span for a pipeline execution.

        Usage:
            with otel.pipeline_trace("pipe-001", "20260318T143200") as root_span:
                with otel.operation_span(root_span, "extract", {...}) as span:
                    ... do extraction ...

        Args:
            pipeline_id: Pipeline identifier.
            execution_timestamp: Execution timestamp string.

        Yields:
            The root span.
        """
        span_name = f"{pipeline_id}-execution-{execution_timestamp}"
        with self._tracer.start_as_current_span(
            span_name,
            attributes={
                "pipeline.id": pipeline_id,
                "pipeline.execution_timestamp": execution_timestamp,
            },
        ) as root_span:
            yield root_span

    @contextmanager
    def operation_span(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
    ):
        """
        Context manager that creates a child span for a pipeline operation.

        Span names follow the convention from SPEC section 7.3:
        extract, transform.join, transform.derive, classify,
        mask.{tier}, quality_gate, load.

        Args:
            name: Span name (e.g. "extract", "mask.staging").
            attributes: Span attributes (row_count, duration_ms, etc.).

        Yields:
            The operation span.
        """
        attrs = {}
        if attributes:
            # Convert all values to OTel-compatible types
            for k, v in attributes.items():
                if isinstance(v, (str, int, float, bool)):
                    attrs[k] = v
                elif isinstance(v, dict):
                    attrs[k] = json.dumps(v)
                elif isinstance(v, list):
                    attrs[k] = json.dumps(v)
                else:
                    attrs[k] = str(v)

        with self._tracer.start_as_current_span(name, attributes=attrs) as span:
            yield span

    def record_extract(
        self,
        source_connector: str,
        source_table: str,
        row_count: int,
        duration_ms: float,
        filter_applied: Optional[str] = None,
    ):
        """
        Record an extraction operation as a completed span.

        Args:
            source_connector: Source connector identifier.
            source_table: Table being extracted.
            row_count: Number of rows extracted.
            duration_ms: Duration in milliseconds.
            filter_applied: Optional filter expression.
        """
        attrs = {
            "source.connector": source_connector,
            "source.table": source_table,
            "row_count": row_count,
            "duration_ms": duration_ms,
        }
        if filter_applied:
            attrs["filter_applied"] = filter_applied

        with self.operation_span("extract", attrs):
            pass  # Span is recorded on exit

    def record_transform(
        self,
        transform_type: str,
        details: dict[str, Any],
        result_row_count: Optional[int] = None,
        duration_ms: Optional[float] = None,
    ):
        """
        Record a transformation operation as a completed span.

        Args:
            transform_type: Type of transform (join, derive, etc.).
            details: Transform details (left/right tables, field, etc.).
            result_row_count: Number of resulting rows.
            duration_ms: Duration in milliseconds.
        """
        attrs: dict[str, Any] = {"transform.type": transform_type}
        attrs.update({f"transform.{k}": v for k, v in details.items()
                      if isinstance(v, (str, int, float, bool))})
        if result_row_count is not None:
            attrs["result_row_count"] = result_row_count
        if duration_ms is not None:
            attrs["duration_ms"] = duration_ms

        span_name = f"transform.{transform_type}"
        with self.operation_span(span_name, attrs):
            pass

    def record_classify(
        self,
        column_count: int,
        classification_counts: dict[str, int],
        duration_ms: Optional[float] = None,
    ):
        """
        Record a classification operation as a completed span.

        Args:
            column_count: Total columns classified.
            classification_counts: Count per classification level.
            duration_ms: Duration in milliseconds.
        """
        attrs: dict[str, Any] = {
            "column_count": column_count,
        }
        for level, count in classification_counts.items():
            attrs[f"classification.{level}"] = count
        if duration_ms is not None:
            attrs["duration_ms"] = duration_ms

        with self.operation_span("classify", attrs):
            pass

    def record_mask(
        self,
        target_tier: str,
        strategy_map: dict[str, str],
        referential_integrity: str,
        row_count: Optional[int] = None,
        duration_ms: Optional[float] = None,
    ):
        """
        Record a masking operation as a completed span.

        Args:
            target_tier: Target tier (staging, development, etc.).
            strategy_map: Map of column to masking strategy.
            referential_integrity: "verified", "failed", or "not_applicable".
            row_count: Number of rows masked.
            duration_ms: Duration in milliseconds.
        """
        attrs: dict[str, Any] = {
            "target.tier": target_tier,
            "strategy_map": json.dumps(strategy_map),
            "referential_integrity": referential_integrity,
        }
        if row_count is not None:
            attrs["row_count"] = row_count
        if duration_ms is not None:
            attrs["duration_ms"] = duration_ms

        span_name = f"mask.{target_tier}"
        with self.operation_span(span_name, attrs):
            pass

    def record_quality_gate(
        self,
        assertions_run: int,
        assertions_passed: int,
        passed: bool,
        duration_ms: Optional[float] = None,
    ):
        """
        Record a quality gate check as a completed span.

        Args:
            assertions_run: Total assertions executed.
            assertions_passed: Number that passed.
            passed: Overall gate result.
            duration_ms: Duration in milliseconds.
        """
        attrs: dict[str, Any] = {
            "assertions_run": assertions_run,
            "assertions_passed": assertions_passed,
            "assertions_result": "passed" if passed else "failed",
        }
        if duration_ms is not None:
            attrs["duration_ms"] = duration_ms

        with self.operation_span("quality_gate", attrs) as span:
            if not passed:
                span.set_status(StatusCode.ERROR, "Quality gate failed")

    def record_load(
        self,
        target_connector: str,
        target_table: str,
        target_tier: str,
        row_count: int,
        duration_ms: float,
    ):
        """
        Record a load operation as a completed span.

        Args:
            target_connector: Target connector identifier.
            target_table: Target table name.
            target_tier: Target tier.
            row_count: Number of rows loaded.
            duration_ms: Duration in milliseconds.
        """
        attrs = {
            "target.connector": target_connector,
            "target.table": target_table,
            "target.tier": target_tier,
            "row_count": row_count,
            "duration_ms": duration_ms,
        }
        with self.operation_span("load", attrs):
            pass

    def shutdown(self) -> None:
        """Flush and shut down the tracer provider."""
        self._provider.shutdown()
