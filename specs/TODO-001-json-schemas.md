# TODO-001: JSON Schema Definitions

## Requirements Covered
- REQ-DP-004: Pipeline definitions in declarative YAML with JSON Schema validation
- REQ-DP-005: Data contracts with per-column classification and PII tagging
- REQ-DP-006: Masking policies per environment tier in declarative YAML
- REQ-DP-024: Extend conductor-state.json with data_pipelines section

## Dependencies
- None (foundation layer — must be built first)

## Inputs
- SPEC.md Sections 3.1, 3.2, 3.3, 8.3 — the canonical YAML examples
- Existing conductor-state.json schema (from conductor orchestration system)
- Governance framework's 4-tier classification model (Public/Internal/Confidential/Restricted)

## Outputs
- `schemas/pipeline.schema.json` — JSON Schema for pipeline definition YAML (Section 3.1)
- `schemas/contract.schema.json` — JSON Schema for data contract YAML (Section 3.3)
- `schemas/masking-policy.schema.json` — JSON Schema for masking policy YAML (Section 3.2)
- `schemas/lineage-event.schema.json` — JSON Schema for lineage events (Section 7.1)
- `schemas/conductor-state-data.schema.json` — JSON Schema for the `data_pipelines` extension to conductor-state.json (Section 8.3)
- `schemas/README.md` — brief usage doc for schema validation

## Implementation Scope

### Files to Create

**`schemas/pipeline.schema.json`**
- Validate `apiVersion: conductor-data/v1`, `kind: Pipeline`
- Required: `metadata` (id, name, created_by), `source` (connector, connection, extraction), `targets` (array with tier, connector, connection, masking)
- Optional: `transform` (array of operations), `lineage`, `quality`
- `source.extraction.mode` enum: `full`, `incremental`, `cdc`
- `source.extraction.tables` array with name (required), columns (array), filter (string)
- `targets[].masking` references a masking policy name or `none`
- `quality.assertions` array of strings
- `quality.on_failure` enum: `block`, `warn`
- All `${VARIABLE}` placeholders must be strings (no validation of resolved values at schema level)

**`schemas/contract.schema.json`**
- Validate `apiVersion: conductor-data/v1`, `kind: DataContract`
- Required: `metadata` (pipeline_ref, steward, reviewed_at, classification_version)
- `columns` map: key is dotted column name, value has `classification` (enum: public/internal/confidential/restricted), `pii` (boolean), optional `pii_type` (enum: PERSON/EMAIL/PHONE/SSN/CREDIT_CARD/ADDRESS/DATE_OF_BIRTH)
- `governance` object: `human_review_required` (boolean), `retention_days` (integer), `audit_frequency` (enum: daily/weekly/monthly)
- `quality_signoff` boolean

**`schemas/masking-policy.schema.json`**
- Validate `apiVersion: conductor-data/v1`, `kind: MaskingPolicy`
- Required: `metadata` (name, tier, description)
- `defaults` object: `strategy` (enum: tokenize/format_preserve_encrypt/redact/synthetic/passthrough), `deterministic` (boolean), `seed` (string)
- `rules` array: each has `classification` (enum) and either `action`/`strategy` or `fields` array
- `fields[].pattern` is a glob string, `fields[].strategy` is the strategy enum, optional `fields[].format`
- `unstructured_rules`: `enabled` (boolean), `ner_model` (string), `entities` (array of entity type enums), `replacement` (strategy enum), optional `thresholds` per classification
- `referential_integrity`: `enabled` (boolean), `consistency_scope` (enum: pipeline/table)

**`schemas/lineage-event.schema.json`**
- Inherited governance fields: `gov_agent_id`, `gov_session_id`, `gov_classification`, `gov_timestamp`
- Pipeline extensions: `pipeline_id`, `operation` (enum: extract/transform/mask/load)
- `source` object, `target` object, `transformation` object, `quality` object
- `content_hash` string with `sha256:` prefix pattern

**`schemas/conductor-state-data.schema.json`**
- `data_pipelines` array of objects
- Each: `id`, `definition` (path), `contract` (path), `status` (enum: pending/designing/reviewing/approved/executing/executed/failed), `last_run` (ISO 8601), `targets_ready` (array of tier names), `quality_gate` (enum: pending/passed/failed)

### Tests to Write

- `tests/test_schemas.py` — for each schema:
  - Validate the canonical YAML example from SPEC.md passes
  - Validate at least 3 invalid variants are rejected (missing required fields, wrong enum values, type mismatches)
  - Validate edge cases: empty arrays, optional fields omitted, `${VARIABLE}` placeholder strings
- Use `jsonschema` Python library for validation tests

## Acceptance Criteria
1. All 5 JSON Schema files exist and are valid JSON Schema (draft 2020-12)
2. The pipeline YAML example from SPEC.md Section 3.1 passes validation against `pipeline.schema.json`
3. The contract YAML example from SPEC.md Section 3.3 passes validation against `contract.schema.json`
4. The masking policy YAML example from SPEC.md Section 3.2 passes validation against `masking-policy.schema.json`
5. The lineage event example from SPEC.md Section 7.1 passes validation against `lineage-event.schema.json`
6. Invalid YAML (missing required fields, wrong types, invalid enums) is rejected with clear error paths
7. `conductor-state-data.schema.json` validates the data_pipelines example from Section 8.3
8. Test suite passes: `pytest tests/test_schemas.py`

## Estimated Complexity
M (Medium — 100-500 lines; 5 schemas + validation tests)
