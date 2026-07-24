# TODO-012: Integration Testing & Compliance Mapping

## Requirements Covered
- REQ-DP-043: Integration test suite with canonical pipelines on synthetic data
- REQ-DP-041: Pipeline dry-run mode via data_extract dry_run flag
- REQ-DP-044: GDPR Article 30 field mapping from lineage events

## Dependencies
- TODO-001 (JSON Schemas — test data validates against schemas)
- TODO-002 (Masking engine core — integration tests exercise masking)
- TODO-003 (NER integration — free-text PII test)
- TODO-005 (Lineage emitter — tests verify lineage captured)
- TODO-006 (Quality assertion engine — tests verify assertions)
- TODO-007 (MCP tool layer — tests call MCP tools)
- TODO-008 (Contract enforcement — tests verify contract checks)
- TODO-009 (Quality gate — tests verify gate passes/fails)
- TODO-010 (Agent definitions — tests reference agent YAML)
- TODO-011 (Docker compose — tests require running containers)

## Inputs
- All component implementations from TODO-001 through TODO-011
- Synthetic source data (created as test fixtures)
- Test pipeline definitions, contracts, and masking policies
- Running Docker compose environment

## Outputs
- `tests/integration/` directory with canonical pipeline test suite
- `tests/fixtures/` directory with synthetic test data and YAML artifacts
- `compliance/gdpr_article30.py` — GDPR Article 30 mapping module
- Test execution reports

## Implementation Scope

### Test Fixtures to Create

**`tests/fixtures/source_data/customers.json`** — Synthetic customer data
- 100 rows with: id, name, email, phone, address, ssn, created_at, tier
- Mix of PII types for masking strategy testing
- Known values for deterministic assertion (specific names, emails, etc.)

**`tests/fixtures/source_data/orders.json`** — Synthetic order data
- 500 rows with: id, customer_id (FK to customers), amount, status, created_at
- FK relationships for integrity testing
- Range of amounts for aggregate assertions

**`tests/fixtures/source_data/notes.json`** — Synthetic text data
- 50 rows with: id, customer_id, note_text
- note_text contains embedded PII (names, emails, phone numbers in prose)
- For testing NER-based detection in free-text columns

**`tests/fixtures/pipelines/single-table.pipeline.yaml`** — Single Table Test
- Extract customers only, all 4 masking strategies across columns
- Quality assertions: email NOT NULL, id UNIQUE, ROW_COUNT > 0

**`tests/fixtures/pipelines/multi-table-join.pipeline.yaml`** — Multi-Table Join Test
- Extract customers + orders, join on customer_id
- FK integrity verification across masked tables
- Derive: lifetime_value

**`tests/fixtures/pipelines/free-text-ner.pipeline.yaml`** — Free-Text NER Test
- Extract notes table with text columns
- NER scanning for embedded PII
- Cross-column consistency (name in notes = name in customers)

**`tests/fixtures/pipelines/multi-tier.pipeline.yaml`** — Multi-Tier Test
- Same source, 3 targets: production (no mask), staging (tokenize), dev (synthetic)
- Verify different masking per tier

**`tests/fixtures/contracts/`** — Matching contracts for each test pipeline
**`tests/fixtures/policies/`** — Staging and dev masking policies

### Integration Test Files

**`tests/integration/test_single_table_pipeline.py`**
- Full pipeline: extract → transform → mask → load
- Verify all 4 masking strategies applied correctly
- Verify quality assertions pass pre-mask and post-mask
- Verify lineage events emitted for each operation
- Verify POST-DATA-PIPELINE gate passes

**`tests/integration/test_multi_table_join.py`**
- Extract 2 tables, join, derive lifetime_value
- Verify FK integrity preserved after masking
- Verify tokenized customer_id matches across both tables
- Verify join count unchanged after masking

**`tests/integration/test_free_text_ner.py`**
- Extract notes with embedded PII
- Verify Presidio detects known entities
- Verify entities replaced with tokens from pipeline-scoped map
- Verify cross-column consistency (same name → same token in notes and customers)

**`tests/integration/test_multi_tier.py`**
- Execute pipeline to 3 tiers
- Production: data unchanged
- Staging: tokenized/FPE per policy
- Dev: synthetic data, matching distributions
- Verify each tier has correct masking applied

**`tests/integration/test_error_scenarios.py`**
- Connectivity failure: pipeline fails with retry, proper error
- Schema drift: missing column triggers SCHEMA_DRIFT
- Assertion failure (on_failure=block): pipeline halts
- Assertion failure (on_failure=warn): pipeline continues with warning
- Contract missing: extraction blocked with CONTRACT_REQUIRED
- Integrity violation: masking engine fails, rollback target

**`tests/integration/test_dry_run.py`**
- `data_extract` with `dry_run: true` returns:
  - Source schema (column names, types, nullable)
  - Row count estimate
  - 5-row sample
  - Contract coverage check
- No data extracted, no masking, no lineage events

### GDPR Compliance Module

**`compliance/gdpr_article30.py`** — Article 30 Processing Record Generator
- Query lineage database for pipeline execution data
- Map lineage fields to Article 30 fields per spec Section 13.5:
  - Controller → `gov_agent_id`
  - Processor → masking-engine container identity
  - Processing purposes → `pipeline.metadata.brd_refs` → BRD descriptions
  - Categories of data subjects → source table names + contract classifications
  - Categories of personal data → `contract.columns[*].pii_type` where `pii: true`
  - Recipients → `target.tier` + `target.connector` per pipeline target
  - Retention periods → `contract.governance.retention_days`
  - Technical safeguards → `masking_strategy` per column + `referential_integrity: verified`
- Output: structured JSON or formatted text suitable for compliance reporting
- Used by `conductor-compliance` agent via lineage query tool

**`compliance/__init__.py`** — Package init

### Tests for GDPR Module

**`tests/test_gdpr_article30.py`**
- Given lineage events from a complete pipeline execution:
  - All Article 30 fields populated
  - Controller maps to correct agent NHI
  - PII types extracted from contract
  - Recipients include all target tiers
  - Retention period from contract governance section
- Missing lineage data produces partial record with flagged gaps

### Test Runner Configuration

**`tests/conftest.py`** — Shared Test Configuration
- Docker compose fixture: ensure containers running before integration tests
- Synthetic data loading fixture
- Test pipeline execution helpers
- Cleanup: remove test data after suite completes

**`pytest.ini`** or **`pyproject.toml`** section — Test configuration
- Mark integration tests separately: `@pytest.mark.integration`
- Unit tests runnable without Docker
- Integration tests require running Docker compose

## Acceptance Criteria
1. Integration test suite includes all 5 canonical pipeline scenarios from spec Section 13.4
2. Single-table pipeline with all 4 masking strategies passes end-to-end
3. Multi-table join with FK integrity verification passes
4. Free-text NER pipeline detects known PII and applies consistent tokens
5. Multi-tier pipeline produces correctly masked data per tier
6. Error scenarios (connectivity, drift, assertion failure, missing contract) handled correctly
7. Dry-run returns schema + row count + sample without extracting data
8. GDPR Article 30 mapping produces complete processing records from lineage
9. All Article 30 fields populated from lineage data per spec Section 13.5
10. Integration tests run on every masking engine build and policy change
11. All tests pass: `pytest tests/integration/ tests/test_gdpr_article30.py`

## Estimated Complexity
L (Large — 500+ lines; 6 integration test files + fixtures + GDPR module + test configuration)
