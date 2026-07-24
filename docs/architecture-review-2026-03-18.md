# Architecture Review — Conductor Data Pipeline (PRD 9)

**Date**: 2026-03-18
**Reviewer**: conductor-architect (Opus 4.6)
**Input Documents**: SPEC.md, BRD-tracker.json (44 requirements), CISO review (PASS WITH NOTES)
**Verdict**: PASS WITH NOTES

---

## 1. Component Boundary Analysis

### 1.1 Agent Layer

| Concern | Assessment | Status |
|---------|-----------|--------|
| Clear I/O interfaces | Accepts/produces defined per agent YAML. data-engineer accepts 3 artifact types, produces 3. data-steward accepts 3, produces 4. | PASS |
| No circular dependencies | Linear flow: engineer -> steward -> engineer (execution). Steward never calls back to engineer for design. | PASS |
| Independent testability | Each agent's YAML testable in isolation. Agent logic exercised via MCP tool calls, testable with mocked tool layer. | PASS |
| Failure isolation | Agent failure (crash, bad output) does not affect masking engine or lineage. Quality gate catches bad artifacts. | PASS |

### 1.2 MCP Tool Layer

| Concern | Assessment | Status |
|---------|-----------|--------|
| Clear I/O interfaces | 8 tools with documented parameters and JSON return types. Governance classification (Standard/Elevated/Elevated+Human) well-defined. | PASS |
| No circular dependencies | Tools are stateless functions. No tool calls another tool. Agents compose tool calls. | PASS |
| Independent testability | Each tool testable with mocked connectors (Airbyte API, masking engine API, Qdrant, PostgreSQL). | PASS |
| Failure isolation | Tool failure returns typed error to calling agent. Agent decides retry/abort. No cascading to other tools. | PASS |

### 1.3 Connector Layer

| Concern | Assessment | Status |
|---------|-----------|--------|
| Clear I/O interfaces | Airbyte: REST API with well-defined endpoints. Unstructured.io: POST with file upload, JSON return. HTTP connector: configurable request/response. | PASS |
| No circular dependencies | Connectors are leaf nodes. Called by MCP tools, never call up. | PASS |
| Independent testability | Each connector is a separate Docker container, testable via API. Airbyte has extensive test framework. | PASS |
| Failure isolation | Connector failure (timeout, auth) handled by MCP tool layer with typed errors and retry logic. | PASS |

### 1.4 Masking Engine

| Concern | Assessment | Status |
|---------|-----------|--------|
| Clear I/O interfaces | FastAPI with typed endpoints. `POST /mask` accepts dataset + config, returns masked data + lineage. `GET /health` for readiness. | PASS |
| No circular dependencies | Masking engine depends on Presidio (downstream), never on tool layer or agents (upstream). | PASS |
| Independent testability | Fully testable via HTTP API. Mock Presidio for unit tests. Real Presidio for integration tests. | PASS |
| Failure isolation | Engine crash mid-pipeline: rollback target writes (staging table cleanup). Container auto-restart. Pipeline re-run. | PASS |

**NOTE**: The masking engine serves BOTH the masking API (`POST /mask`) AND the human approval endpoint (`/approve`). These are distinct concerns. For v1 this is acceptable (single service, simpler deployment). For v2, consider separating the approval UI into its own lightweight service to reduce attack surface on the masking engine.

### 1.5 Lineage & Governance Layer

| Concern | Assessment | Status |
|---------|-----------|--------|
| Clear I/O interfaces | Emitter accepts lineage events (JSON). Writers push to Qdrant + PostgreSQL. Query engine exposes 4 query types. | PASS |
| No circular dependencies | Lineage is a sink — receives events from all upper layers, never pushes up. Query engine is read-only from consumer perspective. | PASS |
| Independent testability | Qdrant writer testable against local Qdrant. PG writer testable against local PostgreSQL. Query engine testable with seeded data. | PASS |
| Failure isolation | Lineage write failure: For Public/Internal data, pipeline continues with LINEAGE_GAP warning. For Confidential/Restricted, pipeline blocks. Appropriate risk-proportional response. | PASS |

**Overall boundary assessment**: All 5 layers have clean boundaries. No circular dependencies. Each layer can be tested independently. Failure modes are well-defined with appropriate escalation per data classification tier.

---

## 2. Data Flow Validation

### 2.1 Flow A: Database Pipeline (Core ETL)

```
Source DB → data_connect → data_extract → data_transform → data_mask → data_load → Target DB
              │                │                │               │              │
              ▼                ▼                ▼               ▼              ▼
          Connection     Extracted data    Transformed     Masked data    Loaded data
          + schema       (JSON/CSV)        dataset         + lineage      + lineage
                              │                                │
                              ▼                                ▼
                    Contract validation             Integrity check
                    Schema drift check              Quality assertions
```

**Input at each step**: Defined (connection config, dataset, pipeline YAML, contract, policy)
**Output at each step**: Defined (schema, data, transformed data, masked data, load status)
**Error path at each step**: Defined in Section 12.9 (connectivity failure, credential failure, transform error, masking crash, partial load rollback)

**Verdict**: COMPLETE — no gaps in data flow.

### 2.2 Flow B: Document Pipeline (Unstructured Path)

```
Document → Unstructured.io → data_extract → data_profile → data_mask (NER) → data_load
              │                   │               │               │               │
              ▼                   ▼               ▼               ▼               ▼
          Parsed JSON       Extracted        Column stats    Masked text      Loaded
          (elements)        text data        + PII flags     + lineage        + lineage
```

**NOTE (ARCH-001)**: The routing from `data_extract` to Unstructured.io (for documents) vs Airbyte (for databases) is implicit in the spec. The connector type in the pipeline YAML determines routing, but the `data_extract` tool interface doesn't explicitly document this branching. TODO-007 must specify: if `source.connector` starts with `unstructured/`, route to Unstructured.io API; if `airbyte/`, route to Airbyte API; if `http/`, route to HTTP connector.

**Verdict**: COMPLETE WITH NOTE — routing logic needs explicit documentation in tool spec (captured in TODO-007).

### 2.3 Flow C: Governance Pipeline

```
Pipeline YAML → data_contract_validate → steward_gate → POST-DATA-PIPELINE → Execution
      │                  │                    │                  │
      ▼                  ▼                    ▼                  ▼
  Schema valid      Contract covers       Steward has         6 checks pass
                    all columns           reviewed            (blocking)
                                                                  │
                                                                  ▼
                                                          Human approval
                                                          (if Confidential+)
```

**Input at each step**: Defined (YAML, contract, steward NHI, execution results)
**Output at each step**: Defined (validation result, gate verdict, approval decision)
**Error path at each step**: Defined (schema invalid, contract incomplete, steward missing, gate fails, timeout=reject)

**Verdict**: COMPLETE — no gaps in governance flow.

---

## 3. Interface Contracts

### 3.1 Agent ↔ MCP Tool Layer

| Interface | Format | Validator | Malformed Input |
|-----------|--------|-----------|-----------------|
| Tool call parameters | JSON (MCP protocol) | MCP schema validation | MCP error response with parameter error |
| Tool return values | JSON | Pydantic model validation | Typed error in response body |

### 3.2 MCP Tool Layer ↔ Connector Layer

| Interface | Format | Validator | Malformed Input |
|-----------|--------|-----------|-----------------|
| Airbyte API calls | REST/JSON | Airbyte API validation | HTTP 400 with error detail |
| Unstructured.io calls | REST/multipart | Unstructured API validation | HTTP 422 with error detail |
| HTTP connector calls | REST/JSON or XML | Response schema validation | Typed parse error |

### 3.3 MCP Tool Layer ↔ Masking Engine

| Interface | Format | Validator | Malformed Input |
|-----------|--------|-----------|-----------------|
| `POST /mask` request | JSON (Pydantic) | FastAPI request validation | HTTP 422 with field-level errors |
| `POST /mask` response | JSON (Pydantic) | Response model validation | Internal server error + lineage alert |
| `GET /approve` | HTML page | Token validation | HTTP 403 (invalid token) or 410 (expired) |

### 3.4 All Components ↔ Lineage Layer

| Interface | Format | Validator | Malformed Input |
|-----------|--------|-----------|-----------------|
| Lineage event emission | JSON | `lineage-event.schema.json` | Event rejected pre-write, warning logged |
| Lineage query | Query parameters (JSON) | Parameter validation | Typed error with invalid parameter detail |

### 3.5 Masking Engine ↔ Presidio

| Interface | Format | Validator | Malformed Input |
|-----------|--------|-----------|-----------------|
| Analyze request | JSON (text + language) | Presidio API validation | HTTP 400 |
| Analyze response | JSON (entities array) | Response parsing | Degrade gracefully (skip NER, log warning) |

### 3.6 All Components ↔ Credential Store

| Interface | Format | Validator | Malformed Input |
|-----------|--------|-----------|-----------------|
| Secret read | Vault API / file read | Key exists check | `CREDENTIAL_RESOLUTION_FAILURE` error, no retry |

**Verdict**: All inter-component interfaces have defined formats, validators, and malformed-input behaviors.

---

## 4. Build Dependency Graph

```
            ┌────────────┐
            │  TODO-001   │  JSON Schemas (FOUNDATION)
            │  Schemas    │
            └──────┬──────┘
          ┌────────┼────────┬──────────┐
          ▼        ▼        ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ TODO-002 │ │ TODO-005 │ │ TODO-006 │
    │ Masking  │ │ Lineage  │ │ Quality  │
    │ Core     │ │ Emitter  │ │ Asserts  │
    └────┬─────┘ └────┬─────┘ └────┬─────┘
    ┌────┴────┐       │            │
    ▼         ▼       │            │
┌────────┐┌────────┐  │            │
│TODO-003││TODO-004│  │            │
│  NER   ││Synth.  │  │            │
└───┬────┘└────────┘  │            │
    │                 │            │
    │    ┌────────────┴────────────┘
    │    ▼
    │  ┌──────────┐
    │  │ TODO-007 │ ◀── TODO-002 + TODO-005 + TODO-006
    │  │ MCP Tools│
    │  └────┬─────┘
    │       │
    │  ┌────┴─────┐
    │  ▼          ▼
    │┌──────────┐┌──────────┐
    ││ TODO-008 ││ TODO-009 │ ◀── TODO-002 + TODO-003 + TODO-005 + TODO-006 + TODO-008
    ││ Contract ││  Gate    │
    │└────┬─────┘└────┬─────┘
    │     │           │
    │     ▼           │
    │ ┌──────────┐    │
    │ │ TODO-010 │ ◀──┘
    │ │  Agents  │
    │ └────┬─────┘
    │      │
    ▼      ▼
  ┌──────────┐  ┌──────────┐
  │ TODO-011 │  │ TODO-012 │ ◀── ALL
  │  Docker  │  │  Tests   │
  └──────────┘  └──────────┘
```

**Critical path**: TODO-001 → TODO-002 → TODO-007 → TODO-009 → TODO-012

See `specs/build-sequence.md` for detailed phasing, parallel builder assignments, and risk hotspots.

---

## 5. Risks & Gaps Identified

### 5.1 Architecture Notes (address during implementation)

| ID | Severity | Finding | Mitigation |
|----|----------|---------|-----------|
| ARCH-001 | MEDIUM | Document/DB routing in `data_extract` is implicit — connector type prefix determines path but not documented in tool interface | TODO-007 must explicitly specify routing logic based on connector prefix |
| ARCH-002 | LOW | Masking engine serves both masking API and approval UI — mixed concerns | Acceptable for v1. Separate for v2 to reduce attack surface. |
| ARCH-003 | MEDIUM | HTTP connector (REQ-DP-003) is not an Airbyte connector — needs custom implementation | Implement as lightweight Python module within MCP tool layer, not a separate container. Documented in TODO-011. |
| ARCH-004 | LOW | Presidio false negative rate (5-15%) means some PII may not be detected in free text | Mitigated by tiered thresholds + CLASSIFICATION_ESCALATION + 100-row post-mask PII scan. Acceptable per CISO assessment. |
| ARCH-005 | MEDIUM | DuckDB memory pressure with large datasets during transform + assertion | TODO-006 includes configurable memory cap. Batch processing (100K chunks from TODO-002) limits per-batch DuckDB load. |

### 5.2 CISO Findings Status

| CISO Finding | Status | Addressed In |
|--------------|--------|-------------|
| CISO-CRITICAL-001: Contract enforcement on extraction | Fixed in SPEC | TODO-007 (data_extract), TODO-008 (contract validator) |
| CISO-CRITICAL-002: Secure approval endpoint | Fixed in SPEC | TODO-009 (human_approval.py) |
| HIGH-001: data_profile reclassified to Elevated | Fixed in SPEC | TODO-007 (tool_registry.py) |
| HIGH-002: HMAC-SHA256 for token generation | Fixed in SPEC | TODO-002 (tokenizer.py) |
| HIGH-003: Artifact integrity via SHA-256 | Fixed in SPEC | TODO-008 (artifact_integrity.py) |
| HIGH-004: MCP tool caller authentication | Deferred to impl | TODO-007 should implement signed session tokens |
| HIGH-005: Vault AppRole vs static token | Deferred to impl | TODO-007 (credential_resolver.py) notes AppRole |

### 5.3 Requirement Conflicts

No conflicts found between the 44 requirements. Two areas of potential tension:

1. **REQ-DP-039 (atomic load) vs REQ-DP-028 (RAM under 6GB)**: Atomic staging table swap requires temporary doubling of target table size. For very large datasets, this could pressure the 6GB limit. Mitigation: batch processing in 100K chunks limits staging table size at any point.

2. **REQ-DP-037 (no persisted token map) vs REQ-DP-012 (referential integrity)**: Deterministic HMAC-based tokens solve this — same input always produces same token without persistence. No actual conflict, but implementation must ensure HMAC seed management is correct.

---

## 6. Requirement Coverage Matrix

All 44 requirements mapped to TODO specs:

| REQ | TODO(s) | Category |
|-----|---------|----------|
| REQ-DP-001 | 011 | Connector |
| REQ-DP-002 | 011 | Connector |
| REQ-DP-003 | 011 | Connector |
| REQ-DP-004 | 001 | Contract |
| REQ-DP-005 | 001 | Contract |
| REQ-DP-006 | 001 | Contract |
| REQ-DP-007 | 002 | Masking |
| REQ-DP-008 | 002 | Masking |
| REQ-DP-009 | 002 | Masking |
| REQ-DP-010 | 004 | Masking |
| REQ-DP-011 | 003 | Masking |
| REQ-DP-012 | 002 | Masking |
| REQ-DP-013 | 002 | Masking |
| REQ-DP-014 | 005 | Lineage |
| REQ-DP-015 | 005 | Lineage |
| REQ-DP-016 | 005 | Lineage |
| REQ-DP-017 | 010 | Agent |
| REQ-DP-018 | 010 | Agent |
| REQ-DP-019 | 008 | Agent |
| REQ-DP-020 | 007 | Tool |
| REQ-DP-021 | 009 | Gate |
| REQ-DP-022 | 009 | Gate |
| REQ-DP-023 | 007 | Governance |
| REQ-DP-024 | 001 | Governance |
| REQ-DP-025 | 006 | Transform |
| REQ-DP-026 | 006 | Quality |
| REQ-DP-027 | 011 | Deploy |
| REQ-DP-028 | 011 | Deploy |
| REQ-DP-029 | 010 | Integration |
| REQ-DP-030 | 010 | Integration |
| REQ-DP-031 | 007 | Security |
| REQ-DP-032 | 009 | Security |
| REQ-DP-033 | 007 | State |
| REQ-DP-034 | 008 | Contract |
| REQ-DP-035 | 009 | Gate |
| REQ-DP-036 | 003 | Masking |
| REQ-DP-037 | 002 | Masking |
| REQ-DP-038 | 006 | Quality |
| REQ-DP-039 | 007 | Resilience |
| REQ-DP-040 | 008 | Resilience |
| REQ-DP-041 | 007, 012 | Testing |
| REQ-DP-042 | 009 | Testing |
| REQ-DP-043 | 012 | Testing |
| REQ-DP-044 | 012 | Compliance |

**Coverage**: 44/44 requirements mapped. Zero orphans.

Security requirements REQ-DP-031 and REQ-DP-032 are woven into TODO-007 and TODO-009 respectively, not isolated into a separate security TODO. This ensures security is implemented alongside the components that need it, not bolted on afterwards.

---

## 7. TODO Spec Summary

| TODO | Component | Requirements | Complexity | Dependencies |
|------|-----------|-------------|-----------|--------------|
| 001 | JSON Schemas | 004, 005, 006, 024 | M | None |
| 002 | Masking Engine Core | 007, 008, 009, 012, 013, 037 | L | 001 |
| 003 | NER Integration | 011, 036 | M | 002 |
| 004 | Synthetic Generation | 010 | M | 002 |
| 005 | Lineage Emitter | 014, 015, 016 | L | 001 |
| 006 | Quality Assertion Engine | 025, 026, 038 | L | 001 |
| 007 | MCP Tool Layer | 020, 023, 031, 033, 039, 041 | L | 001, 002, 005, 006 |
| 008 | Contract Enforcement | 019, 034, 040 | M | 001, 005, 007 |
| 009 | Quality Gate | 021, 022, 032, 035, 042 | L | 002, 003, 005, 006, 008 |
| 010 | Agent Definitions | 017, 018, 029, 030 | M | 001, 007, 008, 009 |
| 011 | Docker Compose | 001, 002, 003, 027, 028 | M | 002, 003 |
| 012 | Integration Testing | 041, 043, 044 | L | ALL |

---

## 8. Verdict

**PASS WITH NOTES**

The five-layer architecture is sound. Component boundaries are clean with no circular dependencies. All inter-component interfaces are defined with explicit data formats, validators, and error handling. The three canonical data flows (database pipeline, document pipeline, governance pipeline) trace completely from source to target with no gaps.

The 44 BRD requirements decompose cleanly into 12 TODO specs with a well-defined build dependency graph. The critical path (schemas -> masking engine -> MCP tools -> quality gate -> integration tests) is the longest chain at 5 steps.

**Notes requiring implementation-phase attention**:
1. ARCH-001: Explicitly document connector routing logic in `data_extract` tool
2. ARCH-003: HTTP connector needs custom implementation (not Airbyte-based)
3. ARCH-005: Monitor DuckDB memory pressure with large datasets
4. CISO-HIGH-004: Implement signed session tokens for MCP tool authentication
5. CISO-HIGH-005: Use Vault AppRole instead of static VAULT_TOKEN

None of these notes require architectural changes. All are addressable during implementation within the existing architecture.
