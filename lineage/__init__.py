"""
Conductor Data Pipeline — Lineage & Observability Module.

Provides dual-write lineage event storage (Qdrant + PostgreSQL),
OpenTelemetry span emission, and a query engine for provenance
tracing, impact analysis, PII auditing, and pipeline history.
"""

from lineage.emitter import LineageEmitter, EmitResult, LineageWriteError
from lineage.qdrant_writer import QdrantLineageWriter
from lineage.pg_writer import PgLineageWriter
from lineage.otel_emitter import OtelEmitter
from lineage.query import LineageQueryEngine

__all__ = [
    "LineageEmitter",
    "EmitResult",
    "LineageWriteError",
    "QdrantLineageWriter",
    "PgLineageWriter",
    "OtelEmitter",
    "LineageQueryEngine",
]
