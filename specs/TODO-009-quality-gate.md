# TODO-009: POST-DATA-PIPELINE Quality Gate & Human Approval

## Requirements Covered
- REQ-DP-021: POST-DATA-PIPELINE quality gate (BLOCKING)
- REQ-DP-022: Human approval gate for Confidential+ data in load operations
- REQ-DP-035: Human approval workflow with notification, payload, timeout
- REQ-DP-042: Post-mask PII validation (100-row sample scan) in quality gate
- REQ-DP-032: Masking key rotation (quarterly default) with version tracking

## Dependencies
- TODO-002 (Masking engine core — gate validates masking output)
- TODO-003 (NER integration — gate uses Presidio for post-mask PII scan)
- TODO-005 (Lineage emitter — gate validates lineage events exist)
- TODO-006 (Quality assertion engine — gate runs post-mask assertions)
- TODO-008 (Contract enforcement — gate validates contract coverage)

## Inputs
- Pipeline execution results (extracted, transformed, masked datasets)
- Data contract for the pipeline
- Masking policy applied
- Lineage events emitted during execution
- Quality assertion results (pre-mask and post-mask)
- Approval configuration (timeout, notification channel)

## Outputs
- Gate verdict: PASS / FAIL with detailed results
- Human approval decision (approve/reject/request-changes) for Confidential+ data
- Gate audit record in lineage database
- Pipeline status update in conductor-state.json

## Implementation Scope

### Files to Create

**`gates/post_data_pipeline.py`** — POST-DATA-PIPELINE Gate Implementation
- Execute all 6 validation checks from Section 8.2:
  1. **Contract coverage**: Data contract exists and covers all extracted columns
  2. **Quality assertions**: All assertions pass (both pre-mask and post-mask results)
  3. **Masking correctness**: Masking applied correctly for target tier
  4. **Lineage completeness**: Lineage events emitted for every extraction and transformation
  5. **Restricted data check**: No restricted data present in non-production targets
  6. **Referential integrity**: FK relationships preserved across masked tables
- Gate mode: BLOCKING — pipeline cannot progress until gate passes
- Gate agent: conductor-data-steward evaluates results
- Return: `GateResult` with per-check pass/fail, details, overall verdict

**`gates/pii_validator.py`** — Post-Mask PII Validation (REQ-DP-042)
- Sample 100 random rows from each masked target dataset
- Run Presidio analyzer on all Confidential and Restricted columns in sample
- If ANY unmasked PII detected:
  - FPE-masked values: verify format validation passes (not original value)
  - Tokenized values: verify they match token format (e.g., `NAME_` prefix)
  - Redacted values: verify only NULL or `[REDACTED]`
- Return: pii_scan_result per column (clean/violation), violating entity types if any

**`gates/human_approval.py`** — Human Approval Workflow
- Trigger conditions: Confidential+ data in `data_mask` or `data_load` operations
- **Approval endpoint** (`/approve` on masking engine — CISO-CRITICAL-002):
  - HTTPS only (TLS termination at service or reverse proxy)
  - Generate 256-bit cryptographically random approval token
  - Token bound to: pipeline_execution_id + contract_version
  - Token single-use, expires after `governance.approval_timeout_hours` (default 24hr)
  - Minimal web page showing approval payload
- **Notification**: webhook to configured channel (Slack/email/n8n) with approval link
- **Approval payload presented to human**:
  - Pipeline summary (source, target tier, row count)
  - Data contract (all column classifications)
  - Masking strategy map (per column)
  - Sample of 5 masked rows (before/after for Confidential fields)
  - Risk assessment (count of Restricted/Confidential columns)
- **Workflow options**: Approve, Reject (with reason), Request Changes (with feedback)
- **Timeout**: configurable, default 24hr. Timeout = automatic rejection
- **Audit**: all `/approve` access logged (IP, timestamp, token ID, decision)

**`gates/key_rotation.py`** — Masking Key Version Tracking (REQ-DP-032)
- Track FPE key versions in Vault
- Quarterly rotation schedule (configurable per policy)
- Old key versions retained for 1 rotation cycle
- On rotation: all downstream targets must be fully refreshed (new tokens)
- Lineage records key version used per execution
- Gate check: warn if key is due for rotation within 7 days

**`gates/gate_registry.py`** — Gate Registration
- Register POST-DATA-PIPELINE gate with conductor quality gate system
- Define gate trigger: after pipeline execution completes
- Define gate mode: BLOCKING
- Define gate agent: conductor-data-steward
- Integration with conductor-state.json: update pipeline `quality_gate` field

### Modifications to Existing Files

**`masking-engine/app/main.py`** — Add `/approve` endpoint
- Serve approval web page for human reviewers
- Validate approval token on access
- Process approval/rejection/change-request decisions
- Expire tokens after use or timeout

### Tests to Write

**`tests/test_post_data_pipeline_gate.py`**
- All 6 checks pass: gate returns PASS
- Contract missing: gate returns FAIL with CHECK_1_FAILED
- Quality assertion fails: gate returns FAIL with CHECK_2_FAILED
- Unmasked PII found: gate returns FAIL with CHECK_3_FAILED
- Missing lineage event: gate returns FAIL with CHECK_4_FAILED
- Restricted data in non-prod: gate returns FAIL with CHECK_5_FAILED
- Broken FK: gate returns FAIL with CHECK_6_FAILED

**`tests/test_pii_validator.py`**
- Clean masked data passes PII scan
- Unmasked name in Confidential column detected
- Properly tokenized values pass (not flagged as PII)
- Redacted columns with only [REDACTED] pass

**`tests/test_human_approval.py`**
- Approval token generated (256-bit, cryptographically random)
- Token bound to pipeline + contract version
- Token single-use (second use rejected)
- Token expires after timeout
- Approval payload includes all required fields
- Approve action: gate passes
- Reject action: gate fails with rejection reason
- Timeout: automatic rejection

**`tests/test_key_rotation.py`**
- Key version tracked in lineage
- Rotation warning emitted when key due within 7 days
- Old key version accessible during retention window
- Key version mismatch between executions detected

## Acceptance Criteria
1. POST-DATA-PIPELINE gate runs all 6 validation checks from Section 8.2
2. Gate is BLOCKING — pipeline cannot progress on failure
3. Post-mask PII validation scans 100 random rows per target
4. Unmasked PII in Confidential/Restricted columns fails the gate
5. Human approval triggered for Confidential+ data in mask/load operations
6. Approval tokens are 256-bit cryptographically random, single-use, time-limited
7. Approval endpoint is HTTPS with token-based authentication
8. Human sees: pipeline summary, contract, strategy map, sample rows, risk assessment
9. Timeout (default 24hr) results in automatic rejection
10. All approval actions audited in lineage (IP, timestamp, decision)
11. Key rotation tracked and warned before expiry
12. Gate results update conductor-state.json pipeline status
13. All tests pass: `pytest tests/test_post_data_pipeline_gate.py tests/test_pii_validator.py tests/test_human_approval.py tests/test_key_rotation.py`

## Estimated Complexity
L (Large — 500+ lines; gate engine + PII validator + human approval workflow + key rotation + approval endpoint)
