# TODO-003: Masking Engine NER Integration

## Requirements Covered
- REQ-DP-011: NER-based PII detection in free-text via Presidio
- REQ-DP-036: NER scans database text columns (VARCHAR/TEXT/CLOB), not just documents

## Dependencies
- TODO-002 (Masking engine core — tokenizer, strategy router, API layer must exist)

## Inputs
- Dataset containing text/string columns (from masking engine pipeline)
- Data contract with column classifications
- Masking policy with `unstructured_rules` configuration
- Presidio analyzer API endpoint (Docker container)
- Pipeline-scoped token map seed (from TODO-002 tokenizer)

## Outputs
- Text columns with PII entities replaced by tokens from the pipeline-scoped token map
- `CLASSIFICATION_ESCALATION` events when PII found in Public/Internal classified columns
- NER detection report: entities found, confidence scores, replacement tokens
- Lineage metadata for NER operations

## Implementation Scope

### Files to Create

**`masking-engine/app/ner/presidio_client.py`** — Presidio API Client
- HTTP client to call Presidio analyzer API (`http://presidio-analyzer:5002/analyze`)
- Submit text content for entity detection
- Parse response: entity type, start/end positions, confidence score
- Handle Presidio errors gracefully (timeout, unavailable)
- Configurable timeout (default 30s per column batch)

**`masking-engine/app/ner/text_scanner.py`** — Text Column Scanner
- Identify text columns in dataset (VARCHAR, TEXT, CLOB, string types)
- Schema profile integration: use column types from data contract or inferred from data
- Batch text values for efficient Presidio calls (batch by column, not row-by-row)
- Apply confidence thresholds per classification tier (Section 12.4):
  - Restricted: 0.70 (aggressive)
  - Confidential: 0.85 (balanced)
  - Internal: 0.90 (conservative)
- Thresholds overridable via `unstructured_rules.thresholds` in masking policy

**`masking-engine/app/ner/entity_replacer.py`** — Entity Replacement
- Replace detected entities with tokens from the SAME pipeline-scoped token map used for structured columns
- Ensure cross-column consistency: `Jane Doe` in a `notes` TEXT column maps to the same token as `Jane Doe` in a structured `name` column
- Supported entity types: PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, ADDRESS, DATE_OF_BIRTH
- Replacement preserves surrounding text (only the entity span is replaced)

**`masking-engine/app/ner/escalation.py`** — Classification Escalation Handler
- When Presidio detects PII in a column classified as Public or Internal:
  - Emit `CLASSIFICATION_ESCALATION` event
  - Include: column name, detected entity types, confidence scores, current classification
  - Event routed to POST-DATA-PIPELINE gate for data-steward review
- Escalation does NOT block the masking operation — it flags for post-execution review
- Multiple escalations per pipeline aggregated into single report

### Modifications to Existing Files

**`masking-engine/app/strategy_router.py`** — Add NER strategy path
- When column is a text type AND `unstructured_rules.enabled: true` in policy, route through NER scanner before applying column-level masking
- NER scanning happens BEFORE column-level strategy application

**`masking-engine/app/main.py`** — Add NER health check
- Health check validates Presidio analyzer is reachable
- Degrade gracefully: if Presidio unavailable, text columns masked using column-level strategy only (log warning)

### Tests to Write

**`masking-engine/tests/test_presidio_client.py`**
- Detect known PII in sample text (name, email, phone embedded in paragraph)
- Handle Presidio timeout gracefully
- Handle empty text input

**`masking-engine/tests/test_text_scanner.py`**
- Identify text columns correctly from mixed dataset
- Apply correct confidence threshold per classification tier
- Batch processing produces same results as row-by-row

**`masking-engine/tests/test_entity_replacer.py`**
- Entity replaced with correct token
- Cross-column consistency: same entity in different columns = same token
- Surrounding text preserved
- Multiple entities in single text field all replaced

**`masking-engine/tests/test_escalation.py`**
- PII in Public column triggers CLASSIFICATION_ESCALATION
- PII in Confidential column does NOT trigger escalation (expected)
- Multiple PII types in one column produce single escalation with all types listed

## Acceptance Criteria
1. Presidio Docker container reachable from masking engine via HTTP
2. Text columns (VARCHAR/TEXT/CLOB) automatically scanned for PII when `unstructured_rules.enabled: true`
3. Detected entities replaced with tokens from the pipeline-scoped token map (same map as structured columns)
4. Cross-column consistency: `Jane Doe` in a text column maps to the same token as in a structured name column
5. Confidence thresholds respected per classification tier (0.70/0.85/0.90 defaults)
6. PII detected in Public/Internal columns triggers `CLASSIFICATION_ESCALATION` event
7. Masking engine degrades gracefully when Presidio is unavailable (warning, not failure)
8. All entity types from spec detected: PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, ADDRESS, DATE_OF_BIRTH
9. All tests pass: `pytest masking-engine/tests/test_presidio_*.py masking-engine/tests/test_text_*.py masking-engine/tests/test_entity_*.py masking-engine/tests/test_escalation.py`

## Estimated Complexity
M (Medium — 100-500 lines; 4 modules + Presidio client + tests)
