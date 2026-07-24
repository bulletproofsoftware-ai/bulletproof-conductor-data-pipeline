# TODO-005: Lineage & Observability Emitter

## Requirements Covered
- REQ-DP-014: PROV-AGENT events for every data operation
- REQ-DP-015: Dual-write to Qdrant (semantic) and PostgreSQL (relational)
- REQ-DP-016: OpenTelemetry span emission for observability

## Dependencies
- TODO-001 (JSON Schema definitions — lineage event schema must exist)

## Inputs
- Lineage events from all pipeline operations (extract, transform, mask, load)
- Existing 9-field governance provenance model (gov_agent_id, gov_session_id, etc.)
- Qdrant connection config (existing conductor memory system)
- PostgreSQL connection config (existing conductor database)
- OTLP collector endpoint (for OpenTelemetry spans)

## Outputs
- Lineage events stored in Qdrant with vector embeddings for semantic queries
- Lineage events stored in PostgreSQL in relational tables for DAG traversal
- OpenTelemetry traces with spans per pipeline operation
- Query API for lineage traversal (consumed by `data_lineage_query` MCP tool)

## Implementation Scope

### Files to Create

**`lineage/emitter.py`** — Core Lineage Emitter
- Accept lineage event conforming to `lineage-event.schema.json`
- Validate event against schema before writing
- Dual-write: Qdrant + PostgreSQL (both must succeed for Confidential/Restricted data)
- For Public/Internal: if one store fails, emit `LINEAGE_GAP` warning and continue
- For Confidential/Restricted: both writes must succeed or pipeline blocks (per Section 12.9)
- Thread-safe: multiple pipeline operations may emit concurrently

**`lineage/qdrant_writer.py`** — Qdrant Semantic Storage
- Connect to existing Qdrant instance (used by conductor memory system)
- Collection: `data_lineage` (separate from memory collections)
- Vector embedding: generate embedding from event description text using existing embedding model
- Payload: full lineage event JSON
- Enable semantic queries: "show everything derived from customer table", "pipelines touching PII this week"
- Handle Qdrant connection failures with retry (3 attempts, exponential backoff)

**`lineage/pg_writer.py`** — PostgreSQL Relational Storage
- Connect to existing PostgreSQL instance
- Tables to create (via migration):
  - `data_lineage_events`: id, pipeline_id, operation, gov_agent_id, gov_session_id, gov_classification, gov_timestamp, source_json, target_json, transformation_json, quality_json, content_hash, created_at
  - `data_lineage_dag`: id, parent_event_id, child_event_id, relationship_type (derived_from/masked_from/loaded_to)
  - `data_contract_versions`: id, pipeline_ref, version, contract_yaml, contract_hash, created_at
- Joins with existing `memory_audit` and `memory_links` tables via `gov_session_id`
- Support relational DAG traversal: given a target row, trace back to production source
- Index on: pipeline_id, gov_timestamp, gov_classification, content_hash

**`lineage/otel_emitter.py`** — OpenTelemetry Span Emitter
- Create trace per pipeline execution: `pipe-{id}-execution-{timestamp}`
- Spans per operation: extract, transform.join, transform.derive, classify, mask.{tier}, quality_gate, load
- Span attributes: row counts, durations, strategy maps, assertion results
- Export to OTLP collector endpoint (configurable, optional)
- If OTLP endpoint not configured, spans logged to structured JSON stdout

**`lineage/query.py`** — Lineage Query Engine
- `trace_provenance(target_table, target_tier)` — return full DAG from target back to source
- `impact_analysis(source_table)` — return all downstream targets affected
- `pii_audit(time_range)` — return all operations on Confidential/Restricted data in range
- `pipeline_history(pipeline_id)` — return all executions with quality gate results
- Queries route to PostgreSQL for relational traversal, Qdrant for semantic search

**`lineage/migrations/001_create_lineage_tables.sql`** — Database Migration
- CREATE TABLE statements for `data_lineage_events`, `data_lineage_dag`, `data_contract_versions`
- Indexes
- Foreign keys to existing tables where applicable

**`lineage/__init__.py`** — Package init with convenience imports

### Tests to Write

**`tests/test_emitter.py`**
- Valid event writes to both stores
- Invalid event (fails schema) rejected before write
- Confidential data: both stores must succeed
- Public data: one store failure = warning, not block

**`tests/test_qdrant_writer.py`**
- Event stored with vector embedding
- Semantic query returns relevant results
- Connection failure handled with retry

**`tests/test_pg_writer.py`**
- Event stored in relational table
- DAG relationships created
- Contract version stored
- DAG traversal returns correct lineage chain

**`tests/test_otel_emitter.py`**
- Pipeline execution creates trace with correct span hierarchy
- Span attributes contain expected metadata
- Missing OTLP endpoint falls back to stdout logging

**`tests/test_query.py`**
- Provenance trace returns full path from target to source
- Impact analysis returns all downstream targets
- PII audit filters by classification and time range

## Acceptance Criteria
1. Every data operation (extract, transform, mask, load) emits a PROV-AGENT lineage event with all fields from Section 7.1
2. Events dual-written to Qdrant and PostgreSQL
3. Qdrant supports semantic lineage queries (e.g., "everything derived from customer table")
4. PostgreSQL supports relational DAG traversal (trace masked target back to production source)
5. For Confidential/Restricted data: pipeline blocks if either lineage store write fails
6. For Public/Internal data: pipeline continues with `LINEAGE_GAP` warning on store failure
7. OpenTelemetry traces created per pipeline execution with spans per operation
8. OTel span attributes include row counts, durations, strategy maps
9. Lineage query engine supports provenance tracing, impact analysis, PII audit, pipeline history
10. Database migration creates all required tables with indexes
11. All tests pass: `pytest tests/test_emitter.py tests/test_qdrant_writer.py tests/test_pg_writer.py tests/test_otel_emitter.py tests/test_query.py`

## Estimated Complexity
L (Large — 500+ lines; dual-write with Qdrant + PostgreSQL + OTel + query engine + migration)
