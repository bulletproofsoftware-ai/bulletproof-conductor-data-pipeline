# TODO-007: MCP Tool Layer

## Requirements Covered
- REQ-DP-020: 8 MCP tools (connect, extract, transform, mask, load, profile, validate, lineage)
- REQ-DP-023: Tool classification (standard/elevated/elevated+human)
- REQ-DP-031: Credential management via Docker secrets or HashiCorp Vault
- REQ-DP-033: Incremental extraction cursor state persisted in Airbyte DB
- REQ-DP-039: Atomic load via staging tables — no partial masked data in targets
- REQ-DP-041: Pipeline dry-run mode via data_extract dry_run flag

## Dependencies
- TODO-001 (JSON Schema definitions — for validating tool inputs/outputs)
- TODO-002 (Masking engine core — `data_mask` tool delegates to masking engine API)
- TODO-005 (Lineage emitter — all elevated tools emit lineage events)
- TODO-006 (Quality assertion engine — `data_transform` uses DuckDB transform engine)

## Inputs
- Pipeline definition YAML (for `data_extract`, `data_transform`, `data_load`)
- Data contract YAML (for `data_contract_validate`, `data_mask`)
- Masking policy YAML (for `data_mask`)
- Source/target connection configs with `${VARIABLE}` placeholders
- Credential store (Docker secrets or Vault) for placeholder resolution

## Outputs
- 8 MCP tool definitions registered with conductor MCP server
- JSON responses from each tool with structured data + metadata
- Lineage events for elevated tools
- Audit trail entries for all tool invocations

## Implementation Scope

### Files to Create

**`tools/data_connect.py`** — Test Connectivity Tool (Standard)
- Input: connector type + connection config (with placeholders)
- Resolve credential placeholders from secret store
- Call Airbyte API to test connection and retrieve schema catalog
- Return: connection_status, schema (tables, columns, types), catalog metadata
- Credentials exist in memory only for the duration of the API call
- Classification: Standard (no gate required)

**`tools/data_extract.py`** — Data Extraction Tool (Elevated)
- Input: pipeline_ref (or table/column list), extraction mode (full/incremental), optional `dry_run: true`
- **Contract enforcement (CISO-CRITICAL-001)**:
  1. Resolve data contract for pipeline
  2. No contract → reject with `CONTRACT_REQUIRED`
  3. Contract doesn't cover all requested columns → reject with `CONTRACT_INCOMPLETE`
  4. Contract hash validated against conductor-state.json
  5. Exception: `dry_run: true` returns schema + row count + 5-row sample WITHOUT contract
- **Schema drift detection (REQ-DP-040)**:
  1. Compare current source schema to contract column list
  2. New column in source → warning, column ignored
  3. Missing column in source → `SCHEMA_DRIFT` error, pipeline fails
  4. Type change → `SCHEMA_DRIFT` error, pipeline fails
- Call Airbyte API for extraction (full or incremental via cursor)
- Incremental: Airbyte persists cursor state in airbyte-db automatically
- `reset_cursor: true` flag resets cursor to epoch for backfill
- Return: extracted dataset (JSON), row_count, extraction_metadata
- Emit lineage event for extraction
- Classification: Elevated (audit trail required)

**`tools/data_transform.py`** — Data Transformation Tool (Elevated)
- Input: dataset + transform operations array from pipeline YAML
- Delegate to quality/transform_engine.py (DuckDB)
- Operations: join, filter, derive, aggregate (per Section 12.6)
- Return: transformed dataset, transformation_metadata
- Emit lineage event for each transform operation
- Classification: Elevated (audit trail required)

**`tools/data_mask.py`** — Data Masking Tool (Elevated + Human Gate)
- Input: dataset + pipeline_ref + target_tier
- Call masking engine API (`POST /mask`)
- Return: masked dataset, masking_audit (which strategy per column), lineage_metadata
- For Confidential+ data: trigger human approval gate before returning
- Classification: Elevated + Human Gate for Confidential+

**`tools/data_load.py`** — Data Loading Tool (Elevated + Human Gate)
- Input: masked dataset + target connection config + target tier
- **Atomic load (REQ-DP-039)**:
  1. Create staging/temp tables at target
  2. Load masked data to staging tables
  3. Run post-load assertions if defined
  4. On success: atomic swap (RENAME/ALTER) staging → target
  5. On failure: drop staging tables, target unchanged
- Resolve credential placeholders for target connection
- Call Airbyte API or direct SQL for loading
- Return: load_status, row_count_loaded, target_metadata
- Emit lineage event for load operation
- Classification: Elevated + Human Gate for Confidential+

**`tools/data_profile.py`** — Data Profiling Tool (Elevated)
- Input: dataset (or source reference)
- Analyze: column types, cardinality, null rates, min/max/mean, PII detection (via Presidio), value distributions
- Return: profile report JSON with per-column statistics
- Used by data-steward for classification decisions
- Classification: Elevated (audit trail — profile reveals data characteristics)

**`tools/data_contract_validate.py`** — Contract Validation Tool (Standard)
- Input: pipeline definition YAML + data contract YAML + masking policy YAML
- Validate:
  1. Pipeline YAML passes schema validation
  2. Contract covers all columns in pipeline's extraction list
  3. Masking policy referenced by pipeline exists and is valid
  4. Contract classifications are consistent with masking policy rules
  5. All quality assertions are syntactically valid
- Return: validation_result (pass/fail), issues array, coverage_report
- Classification: Standard (no gate — read-only validation)

**`tools/data_lineage_query.py`** — Lineage Query Tool (Standard)
- Input: query type (provenance/impact/pii_audit/history) + parameters
- Delegate to lineage/query.py
- Return: lineage graph (nodes + edges) or filtered event list
- Classification: Standard (no gate — read-only query)

**`tools/credential_resolver.py`** — Shared Credential Resolution (Internal, not MCP-exposed)
- Resolve `${VARIABLE}` placeholders from Docker secrets or Vault
- Docker secrets: read from `/run/secrets/{variable_name}`
- Vault: use `hvac` client with AppRole authentication
- Credential lifetime: in-memory only, cleared after use
- All credential access logged (which variable, when, which tool)
- Vault AppRole auth (per CISO-HIGH-005 recommendation)

**`tools/tool_registry.py`** — Tool Registration and Classification
- Register all 8 tools with MCP server
- Assign governance classification per tool:
  - Standard: `data_connect`, `data_lineage_query`, `data_contract_validate`
  - Elevated: `data_profile`, `data_extract`, `data_transform`
  - Elevated + Human Gate: `data_mask`, `data_load`
- Middleware: for Elevated tools, automatically create audit trail entry
- Middleware: for Elevated + Human Gate tools, check data classification and trigger gate if Confidential+

**`tools/__init__.py`** — Package init

### Tests to Write

**`tests/test_data_connect.py`**
- Successful connection returns schema catalog
- Invalid credentials return clear error
- Credential placeholders resolved from store

**`tests/test_data_extract.py`**
- Extraction with valid contract succeeds
- Extraction without contract returns CONTRACT_REQUIRED
- Extraction with incomplete contract returns CONTRACT_INCOMPLETE
- dry_run returns schema without contract
- Schema drift: missing column returns SCHEMA_DRIFT
- Schema drift: new column returns warning
- Incremental extraction uses cursor from airbyte-db
- reset_cursor triggers full extraction

**`tests/test_data_transform.py`**
- Each transform type produces correct output
- Invalid transform operation returns error

**`tests/test_data_mask.py`**
- Masking request delegates to masking engine API
- Confidential data triggers human gate

**`tests/test_data_load.py`**
- Atomic load: success swaps staging to target
- Atomic load: failure leaves target unchanged
- Credentials resolved for target connection

**`tests/test_data_profile.py`**
- Profile returns column statistics
- PII detection flagged in profile

**`tests/test_data_contract_validate.py`**
- Valid pipeline + contract + policy passes
- Missing column coverage fails
- Invalid assertion syntax fails

**`tests/test_data_lineage_query.py`**
- Provenance trace returns lineage chain
- Impact analysis returns downstream targets

**`tests/test_credential_resolver.py`**
- Docker secrets read correctly
- Vault credentials read correctly
- Missing credential returns clear error
- Credential access logged

**`tests/test_tool_registry.py`**
- All 8 tools registered
- Governance classification applied correctly
- Elevated tool creates audit trail
- Human gate triggered for Confidential+ data on data_mask/data_load

## Acceptance Criteria
1. All 8 MCP tools registered and callable via MCP protocol
2. Each tool returns structured JSON responses with metadata
3. Tool governance classification enforced: Standard (no gate), Elevated (audit), Elevated+Human (gate for Confidential+)
4. `data_extract` enforces contract requirement (CISO-CRITICAL-001)
5. `data_extract` detects schema drift (missing/changed columns fail, new columns warn)
6. `data_extract` supports `dry_run: true` returning schema without data
7. `data_extract` supports incremental extraction via Airbyte cursor state
8. `data_load` implements atomic staging table swap
9. All credential placeholders resolved at runtime from Docker secrets or Vault
10. Credentials exist in memory only for API call duration
11. All tool invocations audited (elevated tools in lineage, standard tools in access log)
12. All tests pass: `pytest tests/test_data_*.py tests/test_credential_resolver.py tests/test_tool_registry.py`

## Estimated Complexity
L (Large — 500+ lines; 8 tools + credential resolver + registry + governance middleware)
