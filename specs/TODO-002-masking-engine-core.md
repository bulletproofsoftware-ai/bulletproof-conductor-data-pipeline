# TODO-002: Masking Engine Core

## Requirements Covered
- REQ-DP-007: Format-preserving encryption (AES-FF1) for structured fields
- REQ-DP-008: Deterministic tokenization with pipeline-scoped token maps
- REQ-DP-009: Redaction for restricted-classified data
- REQ-DP-012: Referential integrity preservation across joined tables
- REQ-DP-013: Configurable N-tier environment masking
- REQ-DP-037: Deterministic token generation from pipeline_id + seed + input (no persisted map)

## Dependencies
- TODO-001 (JSON Schema definitions — masking policy schema, contract schema, lineage event schema)

## Inputs
- Masking policy YAML (validated against `masking-policy.schema.json`)
- Data contract YAML (validated against `contract.schema.json`)
- Dataset as JSON array or CSV (from MCP tool layer via HTTP)
- Pipeline ID + masking seed (from environment/Vault)
- Master seed from HashiCorp Vault (for HMAC-SHA256 token derivation)

## Outputs
- Masked dataset (same format as input — JSON array or CSV)
- Lineage metadata (JSON conforming to `lineage-event.schema.json`)
- Masking audit record (which rule applied to which column, per Section 12.7 precedence)
- Error responses with typed codes: `POLICY_NOT_FOUND`, `CONTRACT_MISSING`, `INTEGRITY_VIOLATION`, `SEED_UNAVAILABLE`

## Implementation Scope

### Files to Create

**`masking-engine/app/__init__.py`** — package init

**`masking-engine/app/main.py`** — FastAPI application
- `POST /mask` — main masking endpoint, accepts dataset + pipeline_ref + target_tier
- `GET /health` — health check
- `GET /strategies` — list available masking strategies
- Startup: load masking policies from mounted volume, initialize Vault client
- Error handling: all exceptions return structured JSON with error code

**`masking-engine/app/policy_resolver.py`** — Policy Resolver (Step 1)
- Load tier-specific masking policy YAML
- For each column in the dataset, resolve which masking rule applies using the precedence order from Section 12.7:
  1. Field pattern rules (highest — `*.email` matches `customers.email`)
  2. Classification rules (middle — `classification: confidential`)
  3. Defaults block (lowest — `defaults.strategy: tokenize`)
- Return a `column -> strategy` map with audit trail of which rule matched
- Log rule resolution decisions for lineage

**`masking-engine/app/contract_mapper.py`** — Contract Mapper (Step 2)
- Load data contract for the referenced pipeline
- Map each dataset column to its classification and PII metadata
- Validate all columns in the dataset are covered by the contract
- Return classification map: `column -> {classification, pii, pii_type}`

**`masking-engine/app/strategy_router.py`** — Strategy Router (Step 3)
- Given a column + resolved strategy, delegate to the correct transformer
- Strategy enum: `format_preserve_encrypt`, `tokenize`, `redact`, `synthetic`, `passthrough`
- Validate strategy compatibility with data type (e.g., FPE requires structured format)

**`masking-engine/app/transformers/fpe.py`** — Format-Preserving Encryption
- AES-FF1 implementation using `ff3` Python library (or `pyffx`)
- Accept key from Vault, tweak from pipeline context
- Preserve input format: credit cards pass Luhn, phones match pattern, SSNs match `\d{3}-\d{2}-\d{4}`
- Deterministic: same key + tweak + input = same output
- Key version tracking for rotation support

**`masking-engine/app/transformers/tokenizer.py`** — Deterministic Tokenization
- HMAC-SHA256 construction per Section 12.5:
  - `pipeline_derived_seed = HMAC-SHA256(master_seed, pipeline_id)`
  - `token = HMAC-SHA256(pipeline_derived_seed, input_value)`
- Truncate token hash to configurable length with optional prefix (e.g., `NAME_a7f3b2`)
- Pipeline-scoped: all tables in one pipeline share the same derived seed
- No token map persisted — fully recomputable from inputs

**`masking-engine/app/transformers/redactor.py`** — Redaction
- Replace value with NULL or `[REDACTED]` (configurable per policy)
- For string columns: `[REDACTED]`
- For numeric columns: NULL
- For date columns: NULL
- Verify no residual data after redaction

**`masking-engine/app/integrity_checker.py`** — Referential Integrity Checker (Step 5)
- Accept FK relationships from pipeline definition (join operations)
- After masking, verify that FK columns across tables have matching token/FPE values
- Run join count assertions: `COUNT(left JOIN right ON fk) == pre_mask_count`
- Return integrity report: pass/fail per FK relationship

**`masking-engine/app/vault_client.py`** — Vault Integration
- Connect to HashiCorp Vault via `hvac` Python library
- Read master seed, FPE keys, and key versions
- Support Docker secrets as fallback (read from `/run/secrets/`)
- Key version resolution: read current + previous version for rotation window
- All access logged to stdout for lineage capture

**`masking-engine/app/models.py`** — Pydantic Models
- `MaskRequest`: pipeline_ref, target_tier, dataset, options
- `MaskResponse`: masked_dataset, lineage_metadata, audit_record
- `PolicyResolution`: column_name, matched_rule, strategy, precedence_level
- `IntegrityReport`: fk_relationships checked, pass/fail per relationship

**`masking-engine/requirements.txt`** — Python dependencies
- fastapi, uvicorn, pyyaml, jsonschema, hvac, pyffx (or ff3), pydantic, httpx

**`masking-engine/Dockerfile`** — Container definition
- Python 3.11-slim base
- Install requirements
- Copy app code
- Expose port 8080
- Health check: `curl -f http://localhost:8080/health`
- Run with uvicorn

### Tests to Write

**`masking-engine/tests/test_fpe.py`**
- Credit card: input passes Luhn, output passes Luhn, input != output
- Phone: format preserved (`+1-555-XXXX` pattern maintained)
- Determinism: same key + tweak + input = same output across calls

**`masking-engine/tests/test_tokenizer.py`**
- Same input + seed = same token
- Different inputs = different tokens
- Different pipeline IDs = different tokens for same input
- Token has correct prefix when configured

**`masking-engine/tests/test_redactor.py`**
- String → `[REDACTED]`
- Number → NULL
- No residual data in output

**`masking-engine/tests/test_policy_resolver.py`**
- Field pattern rule takes precedence over classification rule
- Classification rule takes precedence over defaults
- Unmatched column falls to defaults
- Missing policy returns error

**`masking-engine/tests/test_integrity_checker.py`**
- FK values match across tables after tokenization
- FK mismatch detected and reported
- Single-table pipeline (no FK) passes trivially

**`masking-engine/tests/test_api.py`**
- `POST /mask` with valid input returns masked data
- `POST /mask` with missing contract returns `CONTRACT_MISSING`
- `GET /health` returns 200
- Invalid tier returns error

## Acceptance Criteria
1. `POST /mask` accepts a dataset + pipeline_ref + target_tier and returns masked data
2. FPE-masked credit card numbers pass Luhn validation; phone numbers preserve format
3. Tokenization is deterministic: identical inputs with same seed produce identical tokens across separate API calls
4. Redacted columns contain only NULL or `[REDACTED]` — zero residual data
5. Referential integrity verified: FK join count unchanged after masking
6. Policy resolver applies correct precedence (field pattern > classification > defaults)
7. Multiple tiers produce different masking behavior for the same dataset (e.g., staging=tokenize, dev=synthetic)
8. Vault client reads master seed and FPE keys; falls back to Docker secrets
9. All error responses use typed error codes
10. `GET /health` returns 200 when service is ready
11. All tests pass: `pytest masking-engine/tests/`

## Estimated Complexity
L (Large — 500+ lines; core service with 4 transformers, resolver, integrity checker, API layer)
