# Conductor Data Pipeline — Design Specification

**PRD**: #9 in the example.com ecosystem
**Date**: 2026-03-18
**Status**: Reviewed (spec review passed, pending user approval)
**Built with**: Conductor orchestration system (dogfooding)

---

## 1. Overview

A governed, agent-orchestrated data pipeline that gives conductor workflows the ability to extract data from enterprise databases, documents, and APIs — transform it, classify it, mask it per environment tier, load it to targets, and maintain full lineage throughout.

### Position in the Ecosystem

Slots between the existing Memory System (PRD 4) and Governance Framework (PRD 5). Consumes governance policies (classification, provenance tagging) and extends the memory system (lineage stored in Qdrant + PostgreSQL). This is the data substrate every other conductor component has been missing.

### Core Principle

**Agents make decisions, tools do work.** The data pipeline gives conductor agents the tools to design, execute, and govern data flows under human oversight. `conductor-data-engineer` designs the pipeline; `conductor-data-steward` classifies and governs the data; existing agents consume the results through MCP tools.

### What This Is NOT

- Not a data warehouse or lake (it moves data, doesn't store it long-term)
- Not a replacement for production ETL platforms (it governs agent-driven data flows)
- Not a BI/analytics tool (it serves agent workflows, not dashboards)

### Build Strategy

This system is built BY the conductor orchestration system itself. The conductor dispatches its existing agent roster to implement the data pipeline components, then the new data agents bootstrap into the workflow. The BRD requirements below feed directly into conductor-state.json for orchestrated implementation.

---

## 2. Architecture — Five Layers

```
┌─────────────────────────────────────────────────────────┐
│                   AGENT LAYER                           │
│  conductor-data-engineer  │  conductor-data-steward     │
│  (pipeline design/exec)   │  (classify/mask/govern)     │
├─────────────────────────────────────────────────────────┤
│                   MCP TOOL LAYER                        │
│  data_connect │ data_extract │ data_transform           │
│  data_mask    │ data_load    │ data_lineage_query       │
│  data_profile │ data_contract_validate                  │
├─────────────────────────────────────────────────────────┤
│                   CONNECTOR LAYER                       │
│  Airbyte OSS (DB connectors: Oracle, MySQL, PG,        │
│  Snowflake, SQL Server, 400+)                           │
│  Unstructured.io (PDF, docs, 65+ file types)            │
│  HTTP/API connector (REST, GraphQL, webhooks)           │
├─────────────────────────────────────────────────────────┤
│                   MASKING ENGINE                         │
│  Policy resolver → Classifier → Transformer             │
│  FPE │ Tokenization │ Redaction │ Synthetic generation  │
│  Tier policies (declarative YAML per environment)       │
├─────────────────────────────────────────────────────────┤
│                   LINEAGE & GOVERNANCE LAYER            │
│  PROV-AGENT model │ OpenLineage events                  │
│  Qdrant (vector lineage) │ PostgreSQL (relational)      │
│  Extends existing 9-field provenance tagging            │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

**Agent Layer** — Two new conductor agents (agents 15 and 16). `conductor-data-engineer` accepts data requirements (from BRD, from architect specs, from human requests) and produces pipeline definitions — what to extract, how to transform, where to load. `conductor-data-steward` reviews every pipeline definition before execution: classifies data columns against the governance framework's 4-tier system (Public/Internal/Confidential/Restricted), selects masking strategies per target tier, and validates lineage capture. Both participate in the existing quality gate system via a new `POST-DATA-PIPELINE` gate.

**MCP Tool Layer** — Eight tools exposed to all conductor agents via MCP. Any agent can call `data_extract` to pull data or `data_lineage_query` to trace provenance. Complex operations (designing multi-source pipelines, choosing masking strategies) route through the data agents. Tools for simple access, agents for governance.

**Connector Layer** — Airbyte OSS handles all database connectivity. No custom JDBC code. Airbyte's catalog provides Oracle, MySQL, PostgreSQL, SQL Server, Snowflake, BigQuery, Redshift, MongoDB, and 400+ others as Docker-based source/destination connectors. Unstructured.io (Docker) handles document parsing with hybrid strategies. A lightweight HTTP connector handles REST APIs, GraphQL endpoints, and webhook ingestion.

**Masking Engine** — Custom Python service (FastAPI, Docker). Implements four masking strategies: format-preserving encryption (AES-FF1), tokenization (deterministic surrogates), redaction, and synthetic data generation. Masking rules declared per environment tier in YAML policy files. The engine receives data, resolves the tier policy, reads the data contract's classifications, applies the appropriate strategy per column, validates referential integrity, and emits lineage metadata.

**Lineage & Governance Layer** — Every data movement emits a PROV-AGENT event extending the existing 9-field provenance model with data-specific fields: `source_connection_id`, `pipeline_id`, `transformation_hash`, `masking_strategy`, `target_tier`, `content_hash`. Events stored in Qdrant (semantic lineage queries) and PostgreSQL (relational traversal, compliance reporting).

---

## 3. Data Contracts & Pipeline Definitions

### 3.1 Pipeline Definition

Declarative YAML artifact produced by `conductor-data-engineer`. Lives alongside TODO specs and BRD files in the project.

```yaml
# pipeline/customer-data.pipeline.yaml
apiVersion: conductor-data/v1
kind: Pipeline
metadata:
  id: pipe-001
  name: customer-data-extract
  brd_refs: [REQ-012, REQ-013]
  created_by: nhi_data-engineer_20260318_a1b2c3d4

source:
  connector: airbyte/source-postgres
  connection:
    host: "${PROD_DB_HOST}"
    port: 5432
    database: customers
    schema: public
  extraction:
    mode: incremental            # full, incremental, cdc
    cursor_field: updated_at
    tables:
      - name: customers
        columns: [id, name, email, phone, address, created_at, tier]
      - name: orders
        columns: [id, customer_id, amount, status, created_at]
        filter: "status != 'draft'"

transform:
  - operation: join
    left: customers
    right: orders
    on: customers.id = orders.customer_id
    type: left
  - operation: derive
    field: lifetime_value
    expression: "SUM(orders.amount) GROUP BY customers.id"
  - operation: classify
    auto: true

targets:
  - tier: production
    connector: airbyte/destination-postgres
    connection:
      host: "${PROD_TARGET_HOST}"
      database: app_db
    masking: none
  - tier: staging
    connector: airbyte/destination-postgres
    connection:
      host: "${STAGING_DB_HOST}"
      database: app_db
    masking: staging-policy
  - tier: development
    connector: airbyte/destination-postgres
    connection:
      host: "${DEV_DB_HOST}"
      database: app_db
    masking: dev-policy

lineage:
  enabled: true
  emit_to: [qdrant, postgresql]
  classification_audit: true

quality:
  assertions:
    - "customers.email IS NOT NULL"
    - "customers.id IS UNIQUE"
    - "orders.amount >= 0"
    - "ROW_COUNT(customers) > 0"
  on_failure: block
```

### 3.2 Masking Policy

Declared per tier, referenced by pipeline definitions:

```yaml
# policies/staging-policy.yaml
apiVersion: conductor-data/v1
kind: MaskingPolicy
metadata:
  name: staging-policy
  tier: staging
  description: "Masked production data preserving referential integrity"

defaults:
  strategy: tokenize
  deterministic: true
  seed: "${MASKING_SEED}"

rules:
  - classification: restricted
    action: redact

  - classification: confidential
    fields:
      - pattern: "*.email"
        strategy: format_preserve_encrypt
        format: "user_{token}@example.com"
      - pattern: "*.phone"
        strategy: format_preserve_encrypt
        format: "+1-555-{token}"
      - pattern: "*.ssn"
        strategy: redact
      - pattern: "*.name"
        strategy: tokenize
        prefix: "NAME_"

  - classification: internal
    strategy: tokenize
    deterministic: true

  - classification: public
    strategy: passthrough

unstructured_rules:
  enabled: true
  ner_model: "presidio"
  entities: [PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, ADDRESS]
  replacement: tokenize

referential_integrity:
  enabled: true
  consistency_scope: pipeline
```

### 3.3 Data Contract

Produced by `conductor-data-steward` after reviewing a pipeline definition:

```yaml
# contracts/customer-data.contract.yaml
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
  steward: nhi_data-steward_20260318_e5f6g7h8
  reviewed_at: 2026-03-18T14:30:00Z
  classification_version: 1

columns:
  customers.id:        { classification: internal,     pii: false }
  customers.name:      { classification: confidential, pii: true,  pii_type: PERSON }
  customers.email:     { classification: confidential, pii: true,  pii_type: EMAIL }
  customers.phone:     { classification: confidential, pii: true,  pii_type: PHONE }
  customers.address:   { classification: restricted,   pii: true,  pii_type: ADDRESS }
  customers.created_at:{ classification: internal,     pii: false }
  customers.tier:      { classification: public,       pii: false }
  orders.id:           { classification: internal,     pii: false }
  orders.customer_id:  { classification: internal,     pii: false }
  orders.amount:       { classification: confidential, pii: false }
  orders.status:       { classification: public,       pii: false }
  orders.created_at:   { classification: internal,     pii: false }
  lifetime_value:      { classification: confidential, pii: false }

governance:
  human_review_required: true
  retention_days: 90
  audit_frequency: weekly

quality_signoff: true
```

### 3.4 Artifact Interaction Flow

1. `conductor-data-engineer` produces the **pipeline definition** (what data, where from, where to)
2. `conductor-data-steward` reviews and produces the **data contract** (classification, governance)
3. The **masking policy** (pre-existing per tier) gets applied based on the contract's classifications
4. The `POST-DATA-PIPELINE` quality gate validates all three are consistent before execution
5. At runtime, the masking engine reads contract + policy and applies the correct strategy per column per tier

**No data moves without a contract.** The steward is a mandatory gate.

---

## 4. New Agents

### 4.1 Agent 15: conductor-data-engineer

```yaml
name: conductor-data-engineer
model: opus[1m]
role: "Designs and executes data pipelines for conductor workflows"
accepts:
  - data-requirements
  - schema-analysis-request
  - pipeline-revision
produces:
  - pipeline-definition
  - schema-profile
  - extraction-report
requires:
  - BRD-tracker.json
  - source-connection-config
constraints:
  - "Never embed credentials in pipeline definitions"
  - "Never extract without a data contract signed by conductor-data-steward"
  - "Incremental extraction preferred over full when source supports cursors"
  - "All quality assertions must pass before marking pipeline complete"
intent_constraints:
  - "Minimize data surface area — extract only columns explicitly needed"
  - "Prefer narrow filters over broad extractions"
```

### 4.2 Agent 16: conductor-data-steward

```yaml
name: conductor-data-steward
model: opus[1m]
role: "Classifies data, governs masking policies, validates lineage"
accepts:
  - pipeline-definition
  - classification-request
  - lineage-query
produces:
  - data-contract
  - masking-recommendation
  - lineage-report
  - classification-audit
requires:
  - pipeline-definition
  - classification-patterns.yaml
  - masking-policies/
constraints:
  - "Every column must be classified before pipeline executes"
  - "Restricted data triggers human approval gate — no override"
  - "Classification decisions must include reasoning for audit trail"
  - "Masking must preserve referential integrity across joined tables"
intent_constraints:
  - "When uncertain about classification, escalate to higher tier (err conservative)"
  - "Prefer tokenization over redaction when downstream utility matters"
```

### 4.3 Handoff Protocol

```
conductor-architect  ──produces: data-requirements──▶  conductor-data-engineer
conductor-data-engineer  ──produces: pipeline-definition──▶  conductor-data-steward
conductor-data-steward  ──produces: data-contract──▶  conductor-data-engineer (execution)
conductor-data-engineer  ──produces: extraction-report──▶  conductor-builder (consumption)
conductor-builder  ──calls: data_extract MCP tool──▶  (direct data access for simple queries)
```

---

## 5. MCP Tools

### 5.1 Tool Catalog

| Tool | Purpose | Typical Caller |
|---|---|---|
| `data_connect` | Test connectivity to a source/target, return schema catalog | data-engineer, architect |
| `data_extract` | Execute extraction (full, incremental, or query) against a connected source | data-engineer, builder |
| `data_transform` | Apply transformations (join, filter, derive, aggregate) to extracted datasets | data-engineer |
| `data_mask` | Apply masking policy to a dataset for a specific target tier | data-steward, data-engineer |
| `data_load` | Load transformed/masked data to a target destination | data-engineer |
| `data_profile` | Analyze a dataset: column types, cardinality, null rates, PII detection, distributions | data-steward, data-engineer |
| `data_contract_validate` | Validate pipeline definition against data contract and masking policies | data-steward, qa |
| `data_lineage_query` | Query lineage graph: provenance tracing, impact analysis | any agent, human |

### 5.2 Tool Governance Classification

- **Standard** (no gate): `data_connect`, `data_lineage_query`, `data_contract_validate`
- **Elevated** (audit trail): `data_profile`, `data_extract`, `data_transform`
- **Elevated + Human Gate for Confidential+**: `data_mask`, `data_load`

### 5.3 Contract Enforcement on Extraction (CISO-CRITICAL-001)

`data_extract` MUST validate that a signed data contract exists and covers all requested columns before returning any data. Without this check, agents can bypass the steward review entirely by calling `data_extract` directly.

**Enforcement logic**:
1. `data_extract` receives pipeline reference (or table/column list)
2. Tool layer resolves the pipeline's data contract from `contracts/` directory
3. If no contract exists → reject with `CONTRACT_REQUIRED` error
4. If contract exists but doesn't cover requested columns → reject with `CONTRACT_INCOMPLETE` error
5. If contract exists and covers all columns → proceed with extraction
6. Contract hash validated against conductor-state.json to prevent tampering

Exception: `dry_run: true` mode returns schema + row count only (no data), permitted without a contract for pipeline design purposes.

### 5.4 Secure Approval Endpoint (CISO-CRITICAL-002)

The human approval endpoint (`/approve`) on the masking engine MUST be secured:

- **HTTPS only** — TLS termination at the masking engine or via reverse proxy
- **Cryptographically random approval tokens** — 256-bit random, single-use, bound to specific pipeline execution ID + contract version
- **Token expiration** — matches `governance.approval_timeout_hours` (default 24hr)
- **Authentication** — approval link includes the random token as the sole auth mechanism (knowledge-based)
- **Auto-expire** — tokens invalidated after use or timeout, whichever comes first
- **Audit** — all access to `/approve` (view, approve, reject) logged to lineage with IP, timestamp, token ID

---

## 6. Masking Engine

### 6.1 Architecture

Python service (FastAPI) running as a Docker container.

```
                     ┌──────────────────────┐
   data_mask MCP     │    MASKING ENGINE     │
   tool call ──────▶ │                       │
                     │  1. Policy Resolver   │  ← reads tier YAML policies
                     │  2. Contract Mapper   │  ← reads data contract
                     │  3. Strategy Router   │  ← picks FPE/token/redact/synthetic
                     │  4. Transformer       │  ← applies masking per column
                     │  5. Integrity Checker │  ← validates FK consistency
                     │  6. Lineage Emitter   │  ← PROV-AGENT events
                     │                       │
   masked data ◀──── │  Returns: masked data │
   + lineage         │  + lineage metadata   │
                     └──────────────────────┘
```

### 6.2 Four Masking Strategies

**Format-Preserving Encryption (FPE — AES-FF1)**
- For structured fields where format matters: credit cards, phone numbers, SSNs, account numbers
- Encrypts to a value passing the same validation rules as the original
- Deterministic with key+tweak — same input always produces same output
- Key stored in environment variable, rotatable per masking cycle

**Tokenization**
- For fields where referential integrity matters: names, emails, IDs as foreign keys
- Generates deterministic surrogate: `Jane Doe` → `NAME_a7f3b2`
- Token map scoped to pipeline — same token across all tables in a single execution
- Token map is ephemeral (not persisted) — prevents reverse-lookup attacks

**Redaction**
- For restricted data with zero non-production utility
- Replaces with NULL or fixed sentinel value (`[REDACTED]`)

**Synthetic Generation**
- For dev tiers needing realistic-looking data with zero real data
- Matches statistical distributions: cardinality ranges, null rates, value distributions
- Uses Faker for realistic names, emails, addresses, dates
- Validates synthetic data passes same quality assertions as original pipeline
- Most expensive — only for dev/sandbox tiers

### 6.3 Referential Integrity Preservation

1. **Pipeline-scoped token map**: Single in-memory dictionary shared across all tables. `customers.id = 42` maps to `TOKEN_x9` everywhere.
2. **FK declaration**: Join operations in pipeline YAML tell the engine which columns share identity.
3. **Post-mask integrity check**: Engine runs join assertions against masked data. FK breakage fails the `POST-DATA-PIPELINE` gate.

### 6.4 Free-Text Field Handling

Microsoft Presidio (open-source, Docker) for NER-based PII detection in unstructured text:
- Scans for PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, ADDRESS, DATE_OF_BIRTH
- Replaces entities using same tokenization map as structured columns
- Confidence threshold configurable per policy (default 0.85)

---

## 7. Lineage & Observability

### 7.1 Lineage Event Schema

```yaml
event:
  # Inherited governance provenance
  gov_agent_id: nhi_data-engineer_20260318_a1b2c3d4
  gov_session_id: sess_abc123
  gov_classification: confidential
  gov_timestamp: 2026-03-18T14:32:00Z

  # Data pipeline extensions
  pipeline_id: pipe-001
  operation: extract | transform | mask | load
  source:
    connector: airbyte/source-postgres
    table: customers
    columns: [id, name, email, phone]
    row_count: 45230
    filter_applied: "status = 'active'"
  target:
    connector: airbyte/destination-postgres
    tier: staging
    table: customers
    masking_applied: true
  transformation:
    type: mask
    strategy_map:
      name: tokenize
      email: format_preserve_encrypt
      phone: format_preserve_encrypt
    referential_integrity: verified
  quality:
    assertions_run: 4
    assertions_passed: 4
  content_hash: sha256:a1b2c3...
```

### 7.2 Dual-Write Storage

**Qdrant** — Semantic lineage queries. "Show everything derived from the customer table." "What pipelines touched PII this week?"

**PostgreSQL** — Relational traversal and compliance reporting. Parent-child DAG for tracing masked records to production sources. GDPR Article 30 processing record generation. Joins against existing `memory_audit` and `memory_links` tables.

### 7.3 OpenTelemetry Spans

```
trace: pipe-001-execution-20260318
├── span: extract (source=postgres/customers, rows=45230, duration=12.3s)
├── span: extract (source=postgres/orders, rows=128450, duration=34.1s)
├── span: transform.join (left=customers, right=orders, result_rows=45230)
├── span: transform.derive (field=lifetime_value)
├── span: classify (columns=13, confidential=4, restricted=1)
├── span: mask.staging (strategy_map={...}, integrity=verified)
├── span: quality_gate (assertions=4/4, passed=true)
└── span: load (target=staging/postgres, rows=45230, duration=8.7s)
```

Flows to Wazuh-compatible syslog or Grafana/Jaeger.

---

## 8. Conductor Workflow Integration

### 8.1 New Phases

For STANDARD+ tier tasks requiring data:

```
existing phases...
├── phase: ciso-review
├── phase: brd-extraction
├── phase: architecture
│
├── phase: data-pipeline-design        ← NEW
│   agent: conductor-data-engineer
│   gate: none (produces artifact)
│
├── phase: data-governance-review      ← NEW
│   agent: conductor-data-steward
│   gate: POST-DATA-PIPELINE (BLOCKING)
│   human_gate: true (if confidential+ data)
│
├── phase: data-pipeline-execute       ← NEW
│   agent: conductor-data-engineer
│   gate: POST-DATA-PIPELINE (validates results)
│
├── phase: implementation
│   agent: conductor-builder
...existing phases
```

### 8.2 New Quality Gate

```yaml
gate: POST-DATA-PIPELINE
mode: BLOCKING
validates:
  - Data contract exists and covers all extracted columns
  - All quality assertions pass (non-null, uniqueness, range checks)
  - Masking applied correctly for target tier (spot-check sample rows)
  - Lineage events emitted for every extraction and transformation
  - No restricted data present in non-production targets
  - Referential integrity preserved across masked tables
agent: conductor-data-steward
triggers_after: pipeline execution completes
```

### 8.3 conductor-state.json Extensions

```json
{
  "data_pipelines": [
    {
      "id": "pipe-001",
      "definition": "pipeline/customer-data.pipeline.yaml",
      "contract": "contracts/customer-data.contract.yaml",
      "status": "executed",
      "last_run": "2026-03-18T14:32:00Z",
      "targets_ready": ["staging", "development"],
      "quality_gate": "passed"
    }
  ]
}
```

### 8.4 Existing Agent Data Awareness

- `conductor-ciso`: Reviews data contracts during security review
- `conductor-qa`: Verifies test data exists and is correctly masked
- `conductor-compliance`: Generates data processing records from lineage events
- `conductor-architect`: References pipeline definitions in TODO specs

No changes to existing agent code — they inspect new artifact types through existing handoff patterns.

---

## 9. Docker Deployment

### 9.1 New Containers

| Container | Image | RAM | Purpose |
|---|---|---|---|
| `airbyte-server` | airbyte/server | ~2GB | Connector orchestration |
| `airbyte-worker` | airbyte/worker | ~1GB | Connector execution |
| `airbyte-db` | postgres:15 | ~256MB | Airbyte internal state |
| `masking-engine` | custom (Python/FastAPI) | ~512MB | Masking service |
| `unstructured-api` | unstructured-io/unstructured-api | ~1GB | Document parsing |
| `presidio-analyzer` | microsoft/presidio-analyzer | ~512MB | NER-based PII detection |

Total additional footprint: ~5-6GB RAM.

### 9.2 Network Topology

All containers on a shared Docker network. Masking engine and MCP tools communicate via internal HTTP. No new ports exposed externally — the MCP tool layer is the only interface.

### 9.3 Credential Management

**Storage**: All database credentials, API keys, and masking encryption keys stored as Docker secrets (for single-host) or HashiCorp Vault (for multi-host). Never in YAML files, environment files committed to git, or pipeline definitions.

**Resolution**: The MCP tool layer resolves `${VARIABLE}` placeholders at runtime. When `data_connect` or `data_extract` is called, the tool reads the pipeline YAML, resolves credential placeholders from the secret store, and passes resolved values to the Airbyte connector API. Resolved credentials exist only in memory for the duration of the API call.

**Masking Keys**: AES-FF1 keys for format-preserving encryption stored in the secret store with version tagging. Key rotation is quarterly by default (configurable per policy). Old key versions retained for 1 rotation cycle to support re-masking operations. Key access logged to the lineage database.

**Access Control**: Only the `masking-engine` and `airbyte-worker` containers have access to the secret store. Agent-layer components never see resolved credentials. Audit trail records which container accessed which secret at what time.

### 9.4 Performance Requirements

- **CPU**: 4+ cores recommended (2 for Airbyte workers, 1 for masking engine, 1 for overhead)
- **Disk**: SSD recommended, 50GB minimum for temporary extraction staging
- **Large datasets**: Batch processing in 100K row chunks, streamed to masking engine. Backpressure via queue depth limits prevents OOM.
- **Concurrency**: Up to 3 pipelines in parallel per conductor instance (configurable via `PIPELINE_MAX_CONCURRENT`)
- **Extraction timeout**: 30 minutes per table (configurable), fail pipeline if exceeded

### 9.5 Docker Compose Structure

```yaml
# docker-compose.data-pipeline.yml (structural reference)
version: "3.8"
services:
  airbyte-db:
    image: postgres:15
    mem_limit: 256m
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U airbyte"]
    volumes:
      - airbyte-db-data:/var/lib/postgresql/data

  airbyte-server:
    image: airbyte/server:latest
    mem_limit: 2g
    depends_on:
      airbyte-db: { condition: service_healthy }
    environment:
      - DATABASE_URL=postgresql://airbyte:${AIRBYTE_DB_PASSWORD}@airbyte-db:5432/airbyte

  airbyte-worker:
    image: airbyte/worker:latest
    mem_limit: 1g
    depends_on:
      airbyte-server: { condition: service_started }

  masking-engine:
    build: ./masking-engine
    mem_limit: 512m
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    depends_on:
      presidio-analyzer: { condition: service_healthy }
    environment:
      - VAULT_ADDR=${VAULT_ADDR}
      - VAULT_TOKEN=${VAULT_TOKEN}

  unstructured-api:
    image: unstructured-io/unstructured-api:latest
    mem_limit: 1g
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthcheck"]

  presidio-analyzer:
    image: microsoft/presidio-analyzer:latest
    mem_limit: 512m
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5002/health"]

networks:
  default:
    name: conductor-data-pipeline

volumes:
  airbyte-db-data:
  pipeline-artifacts:  # Shared volume for YAML definitions
```

---

## 10. Standards Alignment

| Standard | How This Design Aligns |
|---|---|
| **ISO 42001 A.7** | Data classification (A.7.3), quality standards (A.7.4), provenance (A.7.5), preparation (A.7.6) |
| **NIST AI RMF** | Govern (masking policies), Map (data contracts), Measure (quality assertions), Manage (lineage) |
| **EU AI Act Art. 10** | Data governance practices, origin tracking, cleaning, bias examination |
| **OWASP ASI Top 10** | ASI06 Memory Poisoning (lineage prevents), ASI07 Inter-Agent Comms (typed handoffs), ASI08 Cascading Failures (quality gates) |
| **MAESTRO Layer 2** | Data Operations layer threat modeling |
| **GDPR** | Article 30 processing records via lineage, pseudonymization via masking engine |
| **W3C PROV** | PROV-AGENT extension for agent-specific provenance |

---

## 11. Intent Engineering (Section 3.6)

### 11.1 System Intent

```yaml
intent:
  primary: "Enable conductor workflows to extract, transform, mask, and load data from enterprise sources with full governance and lineage"
  constraints:
    - "No data moves without a signed data contract"
    - "Masking is mandatory for all non-production tiers"
    - "Lineage must be captured at every transformation boundary"
    - "Credentials never appear in pipeline definitions or logs"
  trade_offs:
    - prefer: "Data minimization (extract only what's needed)"
      over: "Convenience (extract everything, filter later)"
    - prefer: "Conservative classification (escalate uncertain columns)"
      over: "Permissive classification (assume lower tier)"
    - prefer: "Pipeline failure on integrity violation"
      over: "Silent degradation with broken FK relationships"
  success_criteria:
    - "Any conductor-built application can declare data requirements in BRD and receive governed, masked data for all environment tiers"
    - "Complete lineage trail from production source to masked non-production target"
    - "Zero restricted data in non-production environments"
    - "Masking preserves referential integrity across all joined tables"
```

### 11.2 Agent Intent Blocks

**conductor-data-engineer**:
```yaml
intent:
  directive: "Design minimal, efficient pipelines that extract only what the BRD requires"
  hard_limits:
    - "Never bypass data steward review"
    - "Never store credentials in artifacts"
  soft_preferences:
    - "Incremental over full extraction"
    - "Narrow column selection over SELECT *"
```

**conductor-data-steward**:
```yaml
intent:
  directive: "Protect data subjects by ensuring correct classification and masking"
  hard_limits:
    - "Never approve restricted data for non-production without human gate"
    - "Never skip classification for any column"
  soft_preferences:
    - "Tokenization over redaction when downstream utility exists"
    - "Higher classification tier when uncertain"
```

---

## 12. Operational Specifications

### 12.1 Incremental Extraction State Management

**State storage**: Airbyte's internal PostgreSQL database (`airbyte-db`) persists cursor values per connection/table pair. No custom state management needed.

**Initialization**: First run for any table is treated as full extraction. Subsequent runs use the last extracted cursor value from `airbyte-db`.

**Null cursor handling**: Rows where the cursor field is NULL are included in every incremental run. Pipeline definitions should avoid cursor fields with high null rates.

**State reset**: `data_extract` MCP tool accepts a `reset_cursor: true` flag for backfill scenarios. Resets cursor to epoch, triggering a full extraction on next run. Reset events logged to lineage.

### 12.2 Data Contract Versioning

**Version increment triggers**: Schema changes (column add/remove/rename) or classification changes (column reclassified to different tier) bump the `classification_version` field.

**Pipeline references**: Pipeline definitions reference contracts by `pipeline_ref` (the pipeline ID). At execution time, the latest contract version for that pipeline is used. Explicit version pinning is optional: `contract_version: 3`.

**Retention**: All contract versions stored in the lineage database. Old versions are never deleted — required for audit trail of historical classification decisions.

**Mismatch handling**: If the data contract's column list doesn't match the extracted schema at execution time, the `POST-DATA-PIPELINE` gate fails with a `SCHEMA_DRIFT` error. The data-engineer agent must update both the pipeline definition and request a new contract from the data-steward.

### 12.3 Human Approval Gate Workflow

**Notification**: Webhook to configured channel (Slack, email, or n8n workflow) with approval link. The link points to a minimal web page served by the masking engine's `/approve` endpoint.

**Approval payload presented to human**:
- Pipeline summary (source, target tier, row count estimate)
- Data contract (all column classifications)
- Masking strategy map (what happens to each classified column)
- Sample of 5 masked rows (showing before/after for Confidential fields)
- Risk assessment (count of Restricted/Confidential columns)

**Workflow options**: Approve (proceed with execution), Reject (fail gate, route back to data-steward with rejection reason), Request Changes (return to data-steward with specific feedback).

**Timeout**: 24 hours default. Configurable per pipeline via `governance.approval_timeout_hours` in the data contract. Pipeline marked `AWAITING_APPROVAL` in conductor-state.json during wait. Timeout = automatic rejection.

**Audit**: All approval actions logged to lineage database with: timestamp, approver ID (human), decision (approve/reject/changes), rejection reason (if applicable), contract version reviewed.

### 12.4 Unstructured Text Scope

**Database text columns**: Presidio scans both document-sourced text AND database text columns (VARCHAR, TEXT, CLOB types). Any column typed as text/string in the schema profile is eligible for NER scanning.

**NER output storage**: Detected entities replaced with tokens from the same pipeline-scoped token map used for structured columns. `Jane Doe` in a `notes` TEXT column maps to the same `NAME_a7f3b2` token as `Jane Doe` in a structured `name` VARCHAR column.

**Confidence thresholds by classification**:
- Restricted columns: 0.70 (aggressive detection, accept more false positives)
- Confidential columns: 0.85 (balanced)
- Internal columns: 0.90 (conservative, minimize false positives)
- Thresholds configurable per policy in `unstructured_rules.thresholds`

**Classification escalation**: If Presidio detects PII in a column classified as Public or Internal, the masking engine flags a `CLASSIFICATION_ESCALATION` event. The POST-DATA-PIPELINE gate routes this to the data-steward for reclassification before proceeding.

### 12.5 Token Map Persistence

Token maps use deterministic generation via HMAC-SHA256: `HMAC-SHA256(pipeline_derived_seed, input_value)` where `pipeline_derived_seed = HMAC-SHA256(master_seed, pipeline_id)`. Per-pipeline derived seeds limit blast radius if any single seed is exposed. Master seed stored in Vault (not as flat env var). This means:
- Same input always produces same token across executions (as long as seed is unchanged)
- Incremental updates produce consistent tokens matching previous runs
- Seed rotation (quarterly) produces new tokens — downstream targets must be fully refreshed after rotation
- No token map is persisted to disk or database — tokens are recomputed deterministically at runtime
- Lineage records the seed version used per execution for forensic reconstruction

### 12.6 Quality Assertion Language

**Engine**: SQL subset executed via DuckDB (in-memory analytical query engine). DuckDB processes extracted datasets as in-memory tables.

**Supported syntax**:
- `column IS NOT NULL` — null check
- `column IS UNIQUE` — uniqueness constraint
- `column >= N` / `column BETWEEN N AND M` — range checks
- `ROW_COUNT(table) > N` — non-empty result sets
- `column IN (value1, value2, ...)` — allowed values
- `column MATCHES 'regex'` — regex pattern matching
- `COUNT(DISTINCT column) >= N` — cardinality minimums
- Custom SQL: `ASSERT <any valid DuckDB SELECT returning 0 rows on success>`

**Execution timing**: Assertions run twice:
1. Post-transform, pre-mask: validates source data quality
2. Post-mask: validates masking didn't break constraints (e.g., uniqueness still holds after tokenization)

### 12.7 Masking Policy Precedence

Rules are evaluated most-specific-first:

1. **Field pattern rules** (`fields[].pattern: "*.email"`) — highest precedence
2. **Classification rules** (`classification: confidential`) — middle precedence
3. **Defaults block** (`defaults.strategy: tokenize`) — lowest precedence

When a column matches both a classification rule and a field pattern rule, the field pattern wins. The Policy Resolver logs which rule was selected per column for audit trail.

### 12.8 Artifact Integrity Verification (CISO-HIGH)

All YAML artifacts (pipeline definitions, data contracts, masking policies) are SHA-256 hashed at creation time. Hashes stored in `conductor-state.json`. Before use:
- Masking engine validates contract hash before applying masking strategies
- MCP tool layer validates pipeline definition hash before executing
- Steward contract hash validated against conductor-state.json entry

Tampered artifacts fail with `INTEGRITY_VIOLATION` error, pipeline blocked, alert emitted.

### 12.9 Error Handling

| Error Type | Behavior | Recovery |
|---|---|---|
| Source connectivity failure | Fail fast, 3 retries with exponential backoff (1s, 5s, 25s) | Alert data-engineer, log to lineage |
| Credential resolution failure | Fail immediately, no retry | Alert human — secret store issue |
| Partial extraction failure | Fail entire pipeline, no partial loads | Data-engineer investigates, re-runs |
| Transformation error (type coercion, join mismatch) | Fail pipeline, log failing rows | Data-engineer revises transform spec |
| Masking engine crash mid-pipeline | Rollback target writes (truncate), fail POST-DATA-PIPELINE gate | Auto-restart container, re-run |
| Quality assertion failure with `on_failure: block` | Stop pipeline, no load | Data-engineer/steward review assertions |
| Quality assertion failure with `on_failure: warn` | Log warning to lineage, continue | Advisory — human reviews warnings |
| Lineage write failure (Public/Internal) | Pipeline continues but emits `LINEAGE_GAP` warning | Post-execution reconciliation job |
| Lineage write failure (Confidential/Restricted) | Pipeline BLOCKED — no audit trail for sensitive data is not acceptable | Retry lineage write, fail pipeline if retry fails |
| Human approval timeout | Automatic rejection, pipeline fails | Re-submit after human availability |

**Rollback guarantee**: No partially masked data ever reaches a target. Either all tables for a target tier load successfully, or none do. Implemented via staging to temporary tables, then atomic swap on success.

### 12.10 Schema Drift Detection (Minimal v1)

While full schema evolution is v2, v1 includes basic detection:

1. Each `data_extract` call compares current source schema to the data contract's column list
2. **New column in source**: Warning logged, column ignored (not extracted)
3. **Missing column in source**: Pipeline fails with `SCHEMA_DRIFT` error
4. **Type change in source**: Pipeline fails with `SCHEMA_DRIFT` error
5. Data-engineer must update pipeline definition and request new contract from data-steward

---

## 13. Testing Strategy

### 13.1 Unit Tests

- Each masking strategy tested with known inputs/expected outputs
- FPE: verify format preservation (credit card still passes Luhn, phone still matches pattern)
- Tokenization: verify determinism (same input + seed = same token across invocations)
- Redaction: verify complete removal (no residual PII in output)
- Synthetic: verify distribution matching (mean/variance within 5% of source)

### 13.2 Pipeline Dry-Run

`data_extract` accepts `dry_run: true` flag. Returns:
- Source schema (column names, types, nullable)
- Row count estimate
- Sample of 5 rows (from first page only)
- Contract coverage check (which extracted columns are/aren't in the contract)

No data leaves the source. No masking applied. Used by data-engineer to validate pipeline design before requesting steward review.

### 13.3 Masking Validation

POST-DATA-PIPELINE gate samples 100 random rows from each masked target and verifies:
- No unmasked PII detected by Presidio in any Confidential/Restricted column
- FPE-masked values pass format validation
- Tokenized values are consistent across joined tables (FK spot-check)
- Redacted columns contain only NULL or `[REDACTED]`

### 13.4 Integration Tests

Suite of canonical pipelines executed on synthetic source data:
- Single-table extraction with all four masking strategies
- Multi-table join with FK integrity verification
- Free-text column with known PII entities
- Multi-tier pipeline (prod + staging + dev targets)
- Error scenarios: connectivity failure, schema drift, assertion failure

Run on every masking engine build and policy change.

### 13.5 GDPR Article 30 Compliance Mapping

For `conductor-compliance` agent to auto-generate Article 30 processing records from lineage:

| Article 30 Field | Lineage Source |
|---|---|
| Controller | `gov_agent_id` (orchestrating agent NHI) |
| Processor | `masking-engine` container identity |
| Processing purposes | `pipeline.metadata.brd_refs` → BRD requirement descriptions |
| Categories of data subjects | Inferred from source table names + contract classifications |
| Categories of personal data | `contract.columns[*].pii_type` where `pii: true` |
| Recipients | `target.tier` + `target.connector` per pipeline target |
| Retention periods | `contract.governance.retention_days` |
| Technical safeguards | `masking_strategy` per column, `referential_integrity: verified` |

---

## 14. Scope Boundaries

### 14.1 In Scope (v1)

- Batch and incremental extraction from all Airbyte-supported databases
- Document parsing via Unstructured.io (PDF, docx, 65+ formats)
- HTTP/API connector for REST and GraphQL sources
- Four masking strategies (FPE, tokenization, redaction, synthetic)
- Declarative pipeline definitions, masking policies, and data contracts
- Configurable N-tier environment masking
- NER-based free-text PII detection via Presidio
- PROV-AGENT lineage with dual-write to Qdrant and PostgreSQL
- OpenTelemetry span emission
- POST-DATA-PIPELINE quality gate
- Two new conductor agents
- Eight MCP tools

### 14.2 Out of Scope (v2+)

- **Real-time CDC streaming** (Debezium + Kafka) — v1 is batch/incremental
- **Data catalog / discovery UI** — queryable via tools, no visual dashboard
- **Cross-pipeline lineage** — v1 tracks within single pipelines
- **Schema evolution handling** — v1 assumes stable schemas
- **ML-based classification** — v1 uses pattern matching + NER, not fine-tuned classifiers

---

## 15. Requirements Summary

| ID | Category | Requirement | Priority |
|---|---|---|---|
| REQ-DP-001 | Connector | Support extraction from Oracle, MySQL, PostgreSQL, SQL Server, Snowflake via Airbyte OSS | P0 |
| REQ-DP-002 | Connector | Support document parsing (PDF, docx, 65+ types) via Unstructured.io | P1 |
| REQ-DP-003 | Connector | Support HTTP/API extraction (REST, GraphQL) | P1 |
| REQ-DP-004 | Contract | Pipeline definitions in declarative YAML with JSON Schema validation | P0 |
| REQ-DP-005 | Contract | Data contracts with per-column classification and PII tagging | P0 |
| REQ-DP-006 | Contract | Masking policies per environment tier in declarative YAML | P0 |
| REQ-DP-007 | Masking | Format-preserving encryption (AES-FF1) for structured fields | P0 |
| REQ-DP-008 | Masking | Deterministic tokenization with pipeline-scoped token maps | P0 |
| REQ-DP-009 | Masking | Redaction for restricted-classified data | P0 |
| REQ-DP-010 | Masking | Synthetic data generation matching source distributions | P1 |
| REQ-DP-011 | Masking | NER-based PII detection in free-text via Presidio | P1 |
| REQ-DP-012 | Masking | Referential integrity preservation across joined tables | P0 |
| REQ-DP-013 | Masking | Configurable N-tier environment masking | P0 |
| REQ-DP-014 | Lineage | PROV-AGENT events for every data operation | P0 |
| REQ-DP-015 | Lineage | Dual-write to Qdrant (semantic) and PostgreSQL (relational) | P0 |
| REQ-DP-016 | Lineage | OpenTelemetry span emission for observability | P1 |
| REQ-DP-017 | Agent | conductor-data-engineer agent with pipeline design/execution | P0 |
| REQ-DP-018 | Agent | conductor-data-steward agent with classification/governance | P0 |
| REQ-DP-019 | Agent | Mandatory steward review before pipeline execution | P0 |
| REQ-DP-020 | Tool | 8 MCP tools (connect, extract, transform, mask, load, profile, validate, lineage) | P0 |
| REQ-DP-021 | Gate | POST-DATA-PIPELINE quality gate (BLOCKING) | P0 |
| REQ-DP-022 | Gate | Human approval gate for Confidential+ data in load operations | P0 |
| REQ-DP-023 | Governance | Tool classification (standard/elevated/elevated+human) | P0 |
| REQ-DP-024 | Governance | Extend conductor-state.json with data_pipelines section | P0 |
| REQ-DP-025 | Transform | Join, filter, derive, aggregate operations | P1 |
| REQ-DP-026 | Quality | Data quality assertions (non-null, unique, range, non-empty) | P0 |
| REQ-DP-027 | Deploy | All components Dockerized with docker-compose | P0 |
| REQ-DP-028 | Deploy | Total additional RAM footprint under 6GB | P1 |
| REQ-DP-029 | Integration | BRD data requirements flow to data-engineer via existing handoff protocol | P0 |
| REQ-DP-030 | Integration | Existing agents gain read access to data contracts and lineage | P1 |
| REQ-DP-031 | Security | Credential management via Docker secrets or HashiCorp Vault | P0 |
| REQ-DP-032 | Security | Masking key rotation (quarterly default) with version tracking | P1 |
| REQ-DP-033 | State | Incremental extraction cursor state persisted in Airbyte DB | P0 |
| REQ-DP-034 | Contract | Data contract versioning with lineage retention of all versions | P0 |
| REQ-DP-035 | Gate | Human approval workflow with notification, payload, timeout | P0 |
| REQ-DP-036 | Masking | NER scans database text columns (VARCHAR/TEXT/CLOB), not just documents | P0 |
| REQ-DP-037 | Masking | Deterministic token generation from pipeline_id + seed + input (no persisted map) | P0 |
| REQ-DP-038 | Quality | DuckDB-based quality assertion engine with pre-mask and post-mask execution | P0 |
| REQ-DP-039 | Resilience | Atomic load via staging tables — no partial masked data in targets | P0 |
| REQ-DP-040 | Resilience | Schema drift detection (missing/changed columns fail pipeline) | P0 |
| REQ-DP-041 | Testing | Pipeline dry-run mode via data_extract dry_run flag | P1 |
| REQ-DP-042 | Testing | Post-mask PII validation (100-row sample scan) in quality gate | P0 |
| REQ-DP-043 | Testing | Integration test suite with canonical pipelines on synthetic data | P1 |
| REQ-DP-044 | Compliance | GDPR Article 30 field mapping from lineage events | P1 |
