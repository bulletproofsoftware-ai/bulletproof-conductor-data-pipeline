# Overview — bulletproof-conductor-data-pipeline

`bulletproof-conductor-data-pipeline` is a governed data pipeline subsystem. It moves
data through **contract-validated** pipelines while enforcing masking and anonymization
policies, tracking lineage for every operation, and gating sensitive operations behind
**human approval**. It is designed to plug into a conductor-style multi-agent workflow:
two dedicated agents (a *data engineer* and a *data steward*) collaborate across three
workflow phases, and a blocking quality gate must pass before a pipeline can progress.

## What it does

- **Masks and anonymizes PII** with a policy-driven masking engine that performs
  cross-column consistent tokenization — the same source value maps to the same token
  everywhere it appears, so referential integrity survives masking.
- **Validates every pipeline against a data contract** expressed as JSON Schema
  (draft 2020-12). A pipeline cannot extract a column that the contract does not cover.
- **Emits lineage** (a PROV-AGENT-style event) for every extract, transform, mask and
  load, dual-written to a relational store (PostgreSQL) and a semantic store (Qdrant).
- **Requires human approval** for `data_mask` and `data_load` when the data is
  classified *Confidential* or *Restricted*. Approval uses single-use, time-limited,
  256-bit cryptographically random tokens.

## Architecture at a glance

The subsystem is organized into cooperating Python packages plus a set of container
services (see [`docker-compose.data-pipeline.yml`](../docker-compose.data-pipeline.yml)).

### Python packages

| Package | Responsibility |
|---|---|
| [`tools/`](../tools) | The 8 MCP tools agents call: `data_connect`, `data_extract`, `data_transform`, `data_mask`, `data_load`, `data_profile`, `data_contract_validate`, `data_lineage_query`. Registered with governance classifications in [`tools/tool_registry.py`](../tools/tool_registry.py). |
| [`contracts/`](../contracts) | Data-contract lifecycle: versioning ([`contract_manager.py`](../contracts/contract_manager.py)), validation ([`contract_validator.py`](../contracts/contract_validator.py)), schema-drift detection ([`schema_drift_detector.py`](../contracts/schema_drift_detector.py)), steward-review enforcement ([`steward_gate.py`](../contracts/steward_gate.py)), and SHA-256 artifact integrity ([`artifact_integrity.py`](../contracts/artifact_integrity.py)). |
| [`gates/`](../gates) | The `POST-DATA-PIPELINE` blocking quality gate ([`post_data_pipeline.py`](../gates/post_data_pipeline.py)) with its 6 checks, the post-mask PII validator ([`pii_validator.py`](../gates/pii_validator.py)), human-approval workflow ([`human_approval.py`](../gates/human_approval.py)), FPE key-rotation tracking ([`key_rotation.py`](../gates/key_rotation.py)), and the gate registry ([`gate_registry.py`](../gates/gate_registry.py)). |
| [`lineage/`](../lineage) | Lineage emission and query: dual-write emitter ([`emitter.py`](../lineage/emitter.py)), PostgreSQL writer ([`pg_writer.py`](../lineage/pg_writer.py)), Qdrant writer ([`qdrant_writer.py`](../lineage/qdrant_writer.py)), OpenTelemetry span emitter ([`otel_emitter.py`](../lineage/otel_emitter.py)), and the query engine ([`query.py`](../lineage/query.py)). |
| [`quality/`](../quality) | The quality-assertion DSL parser and engine, the DuckDB executor, the transform engine, and the quality report. |
| [`compliance/`](../compliance) | GDPR Article 30 processing-record generation from lineage. |
| [`masking_engine/`](../masking_engine) | Container definition (Dockerfile + requirements) for the FastAPI masking service that fronts Presidio for NER-based PII detection. |
| [`agents/`](../agents) | Agent, workflow-phase, handoff, and classification-pattern definitions (YAML). |
| [`schemas/`](../schemas) | JSON Schemas for pipeline, contract, masking-policy, lineage-event, and the conductor-state data extension. |

### Container services

`docker-compose.data-pipeline.yml` brings up 6 containers on an internal-only network
(no external ports are exposed; the MCP tool layer is the only interface):

| Service | Image / Build | Purpose |
|---|---|---|
| `airbyte-db` | `postgres:15` | Airbyte's internal state database. |
| `airbyte-server` | `airbyte/server:latest` | Connector orchestration. |
| `airbyte-worker` | `airbyte/worker:latest` | Connector execution. |
| `masking-engine` | build [`./masking_engine`](../masking_engine) | Custom FastAPI masking service. |
| `unstructured-api` | `quay.io/unstructured-io/unstructured-api:latest` | Document parsing (PDF/DOCX/…). |
| `presidio-analyzer` | `mcr.microsoft.com/presidio-analyzer:latest` | NER-based PII detection. |

## The workflow

Defined in [`agents/workflow-phases.yaml`](../agents/workflow-phases.yaml), the pipeline
inserts three phases into a conductor workflow, *after architecture and before
implementation*, and only for `STANDARD`+ tier tasks that require data:

1. **Data Pipeline Design** — the *data engineer* designs a pipeline definition from
   the data requirements.
2. **Data Governance Review** — the *data steward* classifies every column, reviews the
   masking recommendation, and validates governance. This phase carries the
   `POST-DATA-PIPELINE` blocking gate and, when the data is Confidential+, a human gate.
3. **Data Pipeline Execute** — the *data engineer* executes the approved pipeline and
   validates the results against the gate.

## Governance model

Tools carry one of three governance classifications (see
[`tools/tool_registry.py`](../tools/tool_registry.py)):

- **Standard** (no gate): `data_connect`, `data_contract_validate`, `data_lineage_query`.
- **Elevated** (audit trail on every invocation): `data_profile`, `data_extract`,
  `data_transform`.
- **Elevated + Human Gate** (audit trail *and* human approval for Confidential+):
  `data_mask`, `data_load`.

## Scope of this repository

This repository publishes the pipeline's Python source, agent/workflow definitions,
JSON Schemas, and the container-orchestration compose file. The masking service's
FastAPI application code (`masking_engine/app/…`) is provided as a container build target
via [`masking_engine/Dockerfile`](../masking_engine/Dockerfile) and is not vendored into
this repository; the compose file builds it from `./masking_engine`. See
[INSTALL.md](INSTALL.md) for what runs out of the box versus what requires the container
services.

## Documentation map

- [INSTALL.md](INSTALL.md) — install dependencies and run the tests / services.
- [HOW-TO-USE.md](HOW-TO-USE.md) — validate artifacts, run the gate, use the tools.
- [ADMINISTRATOR.md](ADMINISTRATOR.md) — configuration, secrets, key rotation, operations.
- [SBOM.md](SBOM.md) — software bill of materials.
- [scan/scan-report.md](scan/scan-report.md) — security scan results.

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
