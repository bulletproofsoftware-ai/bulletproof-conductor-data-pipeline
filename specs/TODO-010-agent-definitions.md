# TODO-010: Agent Definitions & Handoff Protocol

## Requirements Covered
- REQ-DP-017: conductor-data-engineer agent with pipeline design/execution
- REQ-DP-018: conductor-data-steward agent with classification/governance
- REQ-DP-029: BRD data requirements flow to data-engineer via existing handoff protocol
- REQ-DP-030: Existing agents gain read access to data contracts and lineage

## Dependencies
- TODO-001 (JSON Schema definitions — agents produce/consume YAML artifacts)
- TODO-007 (MCP tool layer — agents use MCP tools)
- TODO-008 (Contract enforcement — steward review is mandatory gate)
- TODO-009 (Quality gate — both agents participate in POST-DATA-PIPELINE gate)

## Inputs
- Existing conductor agent definition format (from conductor orchestration system)
- Existing handoff protocol specification
- BRD-tracker.json structure (agents read BRD requirements)
- conductor-state.json structure (agents update pipeline state)

## Outputs
- `agents/conductor-data-engineer.yaml` — Agent 15 definition
- `agents/conductor-data-steward.yaml` — Agent 16 definition
- `agents/handoff-protocol.yaml` — Handoff routes between data agents and existing roster
- Updated handoff validation rules for new artifact types
- conductor-state.json workflow phase definitions for data pipeline phases

## Implementation Scope

### Files to Create

**`agents/conductor-data-engineer.yaml`** — Agent 15 Definition
- Match spec Section 4.1 exactly:
  - name: `conductor-data-engineer`
  - model: `opus[1m]`
  - role: "Designs and executes data pipelines for conductor workflows"
  - accepts: `data-requirements`, `schema-analysis-request`, `pipeline-revision`
  - produces: `pipeline-definition`, `schema-profile`, `extraction-report`
  - requires: `BRD-tracker.json`, `source-connection-config`
  - constraints: 4 hard constraints (no credentials in artifacts, no extraction without contract, prefer incremental, assertions must pass)
  - intent_constraints: 2 soft preferences (minimize data surface, prefer narrow filters)
- Tools available: all 8 MCP tools
- Gate participation: produces artifacts for POST-DATA-PIPELINE, receives gate results

**`agents/conductor-data-steward.yaml`** — Agent 16 Definition
- Match spec Section 4.2 exactly:
  - name: `conductor-data-steward`
  - model: `opus[1m]`
  - role: "Classifies data, governs masking policies, validates lineage"
  - accepts: `pipeline-definition`, `classification-request`, `lineage-query`
  - produces: `data-contract`, `masking-recommendation`, `lineage-report`, `classification-audit`
  - requires: `pipeline-definition`, `classification-patterns.yaml`, `masking-policies/`
  - constraints: 4 hard constraints (every column classified, restricted triggers human gate, classification reasoning, integrity preservation)
  - intent_constraints: 2 soft preferences (escalate uncertain classification, prefer tokenization over redaction)
- Tools available: `data_profile`, `data_mask`, `data_contract_validate`, `data_lineage_query`
- Gate agent for: POST-DATA-PIPELINE

**`agents/handoff-protocol.yaml`** — Handoff Routes
- Define handoff routes per spec Section 4.3:
  1. `conductor-architect` --produces: data-requirements--> `conductor-data-engineer`
  2. `conductor-data-engineer` --produces: pipeline-definition--> `conductor-data-steward`
  3. `conductor-data-steward` --produces: data-contract--> `conductor-data-engineer` (execution)
  4. `conductor-data-engineer` --produces: extraction-report--> `conductor-builder` (consumption)
  5. `conductor-builder` --calls: data_extract MCP tool--> (direct data access for simple queries)
- Handoff validation: source.produces must contain target.accepts artifact type
- Artifact type registry: add pipeline-definition, data-contract, schema-profile, extraction-report, masking-recommendation, lineage-report, classification-audit

**`agents/workflow-phases.yaml`** — New Conductor Workflow Phases
- Define 3 new phases per spec Section 8.1:
  1. `data-pipeline-design`: agent=conductor-data-engineer, gate=none, produces=pipeline-definition
  2. `data-governance-review`: agent=conductor-data-steward, gate=POST-DATA-PIPELINE (BLOCKING), human_gate=true (if Confidential+)
  3. `data-pipeline-execute`: agent=conductor-data-engineer, gate=POST-DATA-PIPELINE (validates results)
- Phase ordering: after `architecture`, before `implementation`
- Conditional: only activated for STANDARD+ tier tasks requiring data

**`agents/existing-agent-updates.yaml`** — Existing Agent Data Awareness (REQ-DP-030)
- Document which existing agents gain access to new artifact types:
  - `conductor-ciso`: reviews data contracts during security review
  - `conductor-qa`: verifies test data exists and is correctly masked
  - `conductor-compliance`: generates data processing records from lineage events
  - `conductor-architect`: references pipeline definitions in TODO specs
- No code changes to existing agents — they inspect new artifacts through existing handoff patterns
- Add `data-contract`, `lineage-report` to readable artifact types for these agents

**`agents/classification-patterns.yaml`** — Default Classification Patterns
- Pattern-based initial classification suggestions for data-steward:
  - `*.email`, `*.mail` → confidential, pii=true, pii_type=EMAIL
  - `*.phone`, `*.mobile`, `*.tel` → confidential, pii=true, pii_type=PHONE
  - `*.ssn`, `*.social_security*` → restricted, pii=true, pii_type=SSN
  - `*.name`, `*.first_name`, `*.last_name` → confidential, pii=true, pii_type=PERSON
  - `*.address*`, `*.street*`, `*.city`, `*.zip*` → confidential, pii=true, pii_type=ADDRESS
  - `*.credit_card*`, `*.card_number*` → restricted, pii=true, pii_type=CREDIT_CARD
  - `*.dob`, `*.birth*` → confidential, pii=true, pii_type=DATE_OF_BIRTH
  - `*.id`, `*.key`, `*_id` → internal, pii=false
  - `*.status`, `*.type`, `*.category` → public, pii=false
  - `*.created_at`, `*.updated_at`, `*.timestamp` → internal, pii=false
- Patterns are SUGGESTIONS — steward makes final classification decision
- Steward must provide reasoning when overriding pattern suggestion

### Tests to Write

**`tests/test_agent_definitions.py`**
- data-engineer YAML validates against agent definition schema
- data-steward YAML validates against agent definition schema
- All required fields present (name, model, role, accepts, produces, requires, constraints)
- Intent constraints present

**`tests/test_handoff_protocol.py`**
- All 5 handoff routes defined
- Handoff validation: source.produces contains required artifact type
- No circular dependencies in handoff chain
- All artifact types in registry

**`tests/test_workflow_phases.py`**
- 3 new phases defined with correct agents and gates
- Phase ordering: design → review → execute
- Conditional activation for data-requiring tasks

**`tests/test_classification_patterns.py`**
- Email pattern matches *.email, *.mail
- SSN pattern matches *.ssn, *.social_security_number
- Default patterns cover common PII column names
- Non-PII patterns (*.id, *.status) classified correctly

## Acceptance Criteria
1. conductor-data-engineer agent definition YAML matches spec Section 4.1 exactly
2. conductor-data-steward agent definition YAML matches spec Section 4.2 exactly
3. Both agents dispatchable via existing conductor Task tool
4. Handoff protocol defines all 5 routes from spec Section 4.3
5. Handoff validation confirms source.produces matches target.accepts
6. 3 new workflow phases defined with correct ordering (after architecture, before implementation)
7. Phases conditional on STANDARD+ tier tasks requiring data
8. Existing agents (ciso, qa, compliance, architect) can read data contracts and lineage via MCP tools
9. Classification patterns provide sensible defaults for common PII column names
10. All tests pass: `pytest tests/test_agent_*.py tests/test_handoff_*.py tests/test_workflow_*.py tests/test_classification_*.py`

## Estimated Complexity
M (Medium — 100-500 lines; mostly YAML definitions + handoff logic + pattern matching)
