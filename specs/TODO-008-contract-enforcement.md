# TODO-008: Contract Enforcement & Versioning

## Requirements Covered
- REQ-DP-019: Mandatory steward review before pipeline execution
- REQ-DP-034: Data contract versioning with lineage retention of all versions
- REQ-DP-040: Schema drift detection (missing/changed columns fail pipeline)

## Dependencies
- TODO-001 (JSON Schema definitions — contract and pipeline schemas)
- TODO-005 (Lineage emitter — contract versions stored in lineage DB)
- TODO-007 (MCP tool layer — contract enforcement hooks into data_extract)

## Inputs
- Pipeline definition YAML
- Data contract YAML (current and historical versions)
- Source schema (from data_extract connection)
- conductor-state.json (pipeline status tracking)

## Outputs
- Contract validation results (pass/fail with typed errors)
- Contract version management (increment, store, retrieve)
- Schema drift detection results
- Artifact integrity hashes in conductor-state.json

## Implementation Scope

### Files to Create

**`contracts/contract_manager.py`** — Contract Lifecycle Manager
- `create_contract(pipeline_ref, steward_id, columns)` — create new contract, compute SHA-256 hash, store hash in conductor-state.json
- `update_contract(pipeline_ref, changes)` — increment `classification_version`, recompute hash, store old version in lineage DB
- `get_contract(pipeline_ref, version=None)` — retrieve current or specific version
- `get_all_versions(pipeline_ref)` — retrieve all historical versions for audit
- Version increment triggers:
  - Column added or removed from contract
  - Column classification changed
  - PII tagging changed
- Old versions never deleted — required for audit trail

**`contracts/contract_validator.py`** — Contract Validation Logic
- `validate_against_pipeline(contract, pipeline)` — verify contract covers all columns in pipeline extraction list
- `validate_against_schema(contract, source_schema)` — verify contract columns exist in source with matching types
- `validate_integrity(contract, state_hash)` — verify contract YAML hash matches conductor-state.json entry
- Returns typed errors:
  - `CONTRACT_REQUIRED` — no contract exists for pipeline
  - `CONTRACT_INCOMPLETE` — contract doesn't cover all requested columns
  - `CONTRACT_TAMPERED` — hash mismatch (INTEGRITY_VIOLATION)
  - `CONTRACT_EXPIRED` — contract version predates latest schema change

**`contracts/schema_drift_detector.py`** — Schema Drift Detection (Section 12.10)
- Compare source schema (from Airbyte catalog) to data contract column list
- Detection rules:
  - **New column in source, not in contract**: Warning logged, column NOT extracted
  - **Column in contract, missing from source**: `SCHEMA_DRIFT` error, pipeline fails
  - **Type change** (e.g., VARCHAR→INTEGER): `SCHEMA_DRIFT` error, pipeline fails
- Return drift report: added_columns, removed_columns, type_changes
- On SCHEMA_DRIFT: data-engineer must update pipeline definition + request new contract

**`contracts/artifact_integrity.py`** — Artifact Integrity Verification (CISO-HIGH)
- `hash_artifact(yaml_path)` — compute SHA-256 of YAML file content
- `register_hash(artifact_type, artifact_id, hash)` — store in conductor-state.json
- `verify_hash(artifact_type, artifact_id, yaml_path)` — compare current file hash to stored hash
- Artifact types: pipeline, contract, masking_policy
- On mismatch: `INTEGRITY_VIOLATION` error, pipeline blocked, alert emitted
- Hash computed on raw YAML content (not parsed — catches formatting changes that might hide modifications)

**`contracts/steward_gate.py`** — Steward Review Enforcement
- Before pipeline execution:
  1. Check conductor-state.json for pipeline entry
  2. Verify `contract` field is populated (steward has reviewed)
  3. Verify contract `steward` field is a valid data-steward NHI
  4. Verify contract `reviewed_at` is not stale (configurable, default 30 days)
  5. Verify contract hash is valid (integrity check)
- Rejection returns structured error with which check failed
- No bypass mechanism — steward review is architecturally mandatory

### Tests to Write

**`tests/test_contract_manager.py`**
- Create contract, hash stored in state
- Update contract increments version
- Old version retrievable after update
- All versions listed for audit

**`tests/test_contract_validator.py`**
- Valid contract + pipeline passes
- Missing column coverage returns CONTRACT_INCOMPLETE
- No contract returns CONTRACT_REQUIRED
- Tampered hash returns INTEGRITY_VIOLATION

**`tests/test_schema_drift_detector.py`**
- New column in source: warning, column excluded
- Missing column from source: SCHEMA_DRIFT error
- Type change: SCHEMA_DRIFT error
- No drift: clean pass

**`tests/test_artifact_integrity.py`**
- Hash computed correctly (SHA-256 of file content)
- Matching hash passes verification
- Modified file fails verification
- Hash registered in conductor-state.json

**`tests/test_steward_gate.py`**
- Pipeline with valid contract passes
- Pipeline without contract blocked
- Pipeline with stale contract (>30 days) blocked
- Pipeline with invalid steward NHI blocked

## Acceptance Criteria
1. No pipeline executes without a data contract (steward review mandatory)
2. Contract version increments on schema or classification changes
3. All historical contract versions stored in lineage DB (never deleted)
4. Schema drift detection catches missing columns and type changes
5. New columns in source logged as warnings but not extracted
6. Artifact integrity verified via SHA-256 hash before every use
7. Hash mismatch produces `INTEGRITY_VIOLATION` and blocks pipeline
8. conductor-state.json tracks contract hashes for all active pipelines
9. Stale contracts (>30 days since review) require re-review
10. All tests pass: `pytest tests/test_contract_*.py tests/test_schema_drift_*.py tests/test_artifact_*.py tests/test_steward_gate.py`

## Estimated Complexity
M (Medium — 100-500 lines; 5 modules focused on validation logic, no heavy computation)
