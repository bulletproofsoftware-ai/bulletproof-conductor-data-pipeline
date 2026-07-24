# Technical Briefing: bulletproof-conductor-data-pipeline

### 1. Executive System Overview
**The `bulletproof-conductor-data-pipeline` is a robust, governed data pipeline subsystem architected for secure, multi-agent conductor workflows. It ensures data integrity and regulatory compliance by orchestrating contract-validated data movement, policy-driven masking, and high-fidelity lineage tracking, with mandatory human-in-the-loop authorization for sensitive data operations.**

**Core Pillars:**
*   **Contract-Validated Pipelines:** Every pipeline is rigorously validated against JSON-schema data contracts following the **Draft 2020-12** specification, ensuring no unauthorized column extraction occurs.
*   **Policy-Driven Masking:** A specialized engine provides cross-column consistent tokenization, ensuring referential integrity remains intact by mapping identical source values to identical tokens across the ecosystem.
*   **Dual-Write Lineage Tracking:** Captures detailed provenance (PROV-AGENT style) for every operation, ensuring auditability through simultaneous writes to relational and semantic stores.
*   **Human-in-the-loop Approval:** Critical operations involving Confidential or Restricted data tiers are blocked until authorized via time-limited cryptographic tokens.

### 2. Architectural Framework

#### 2.1 Python Subsystem (Packages)
The system is composed of specialized Python packages, each managing a distinct domain of the pipeline lifecycle.

| Package Name | Responsibility |
| :--- | :--- |
| `conductor_tools` | Manages the 8 Model Context Protocol (MCP) tools and governance enforcement. |
| `conductor_contracts` | Handles contract versioning, validation, and SHA-256 artifact integrity. |
| `conductor_gates` | Manages the 6-check quality gate, human approval workflows, and PII validation. |
| `conductor_lineage` | Executes dual-write lineage emission to PostgreSQL, Qdrant, and OpenTelemetry. |
| `conductor_quality` | Parses the quality-assertion DSL and executes validation via DuckDB. |
| `conductor_compliance` | Generates GDPR Article 30 records from lineage and contract metadata. |
| `masking_engine` | Containerized FastAPI service for policy-driven masking and NER-based detection. |
| `conductor_agents` | Defines the agent personas, workflow phases, and classification patterns. |
| `conductor_schemas` | Maintains the JSON Schemas for all pipeline artifacts and state extensions. |

#### 2.2 Containerized Service Stack
The runtime environment is orchestrated via Docker Compose, utilizing an internal-only network to isolate data processing from external access.

*   **airbyte-server:** Central orchestration for data connectors (Memory: 2 GB).
*   **airbyte-worker:** Executes specific connector tasks (Memory: 1 GB).
*   **unstructured-api:** High-performance document parsing for PDF/DOCX (Memory: 1 GB).
*   **masking-engine:** Custom FastAPI service built from `python:3.11-slim` (Memory: 512 MB).
*   **presidio-analyzer:** Microsoft Presidio-based NER for PII detection (Memory: 512 MB).
*   **airbyte-db:** PostgreSQL 15 instance for internal Airbyte state (Memory: 256 MB).

> **Resource Constraints & Networking**
> The stack operates within a strict total memory budget of **~5.3 GB**. Networking is configured as **internal-only**, with no ports published to the host; the system is accessible exclusively through the MCP tool layer. Regarding build provenance: the `masking-engine` FastAPI application source is **not vendored** in the repository but is supplied dynamically during the container build process under `masking_engine/app/`.

### 3. MCP Tool Registry and Governance Classifications
The system exposes 8 MCP tools. Access is governed by three classification tiers that dictate audit requirements and human intervention.

| Tool Name | Governance Classification | Functional Description |
| :--- | :--- | :--- |
| `data_connect` | Standard | Tests source connectivity and retrieves schema catalogs. |
| `data_contract_validate` | Standard | Verifies consistency between pipelines, contracts, and policies. |
| `data_lineage_query` | Standard | Queries provenance, impact analysis, and PII audit history. |
| `data_profile` | Elevated | Provides column metadata, null rates, and PII classification flags. |
| `data_extract` | Elevated | Executes contract-enforced data extraction. |
| `data_transform` | Elevated | Performs joins, filters, and aggregations using an in-memory DuckDB engine. |
| `data_mask` | Elevated + Human Gate | Applies masking policies; requires human approval for Confidential+ data. |
| `data_load` | Elevated + Human Gate | Performs atomic staged loads; requires human approval for Confidential+ data. |

### 4. Three-Phase Operational Workflow
The lifecycle applies specifically to **STANDARD+ tier tasks** that require data, involving collaboration between a Data Engineer and a Data Steward.

1.  **Data Pipeline Design:** The **data engineer** authors the pipeline definition, specifying sources, targets, transform logic, and masking policy references.
2.  **Data Governance Review:** The **data steward** classifies data columns, reviews masking recommendations, and validates the governance artifacts against the blocking quality gate.
3.  **Data Pipeline Execute:** The **data engineer** executes the approved pipeline, with the system performing final validation against the steward-signed artifacts.

### 5. The POST-DATA-PIPELINE Quality Gate
Before a pipeline progresses to completion, it must pass a blocking 6-check protocol. A failure in any check results in a `FAIL` verdict that stops the pipeline.

*   **Contract Coverage:** Success requires every extracted column to be explicitly defined in the steward-approved data contract.
*   **Quality Assertions:** Validates that all DSL-defined assertions pass in both pre-masking and post-masking states.
*   **Masking Correctness:** Samples rows and utilizes NER-based scans to ensure no residual PII remains in Confidential/Restricted columns.
*   **Lineage Completeness:** Verifies that a lineage event was successfully recorded for every expected operational step.
*   **Restricted Data Check:** Prevents leakage by ensuring data tagged as "Restricted" does not flow into targets defined with a non-production "tier."
*   **Referential Integrity:** Confirms that foreign key relationships and cross-column logic remain valid after masking transformations.

### 6. Security and Integrity Mechanisms

#### 6.1 Secret Resolution and Masking Key Rotation
The system implements a three-tier secret resolution order: **HashiCorp Vault (via hvac/AppRole) > Docker secrets > Environment variables**. 

**FPE Masking Key Rotation Policy:**
*   **Interval:** Mandatory rotation every 90 days.
*   **Warning:** A 7-day notification window precedes key expiration.
*   **Retention:** The system retains the previous key version for exactly one cycle to allow for data decryption, after which older keys are purged.

#### 6.2 Human Approval Workflow
> **Security Protocol**
> Operations classified as "Elevated + Human Gate" trigger a manual authorization request. The system generates single-use, 256-bit cryptographically random tokens bound to a specific **pipeline_execution_id** and **contract_version**. A comprehensive audit log captures every access attempt, including rejections, decision reasons, and timeouts.

#### 6.3 Artifact Integrity and Steward Review
The `conductor-contracts` package enforces a strict stewardship model with no bypass mechanism. Verification includes:
*   [ ] A `conductor-state.json` entry exists for the pipeline.
*   [ ] The contract field is fully populated and reviewed.
*   [ ] The contract steward matches a valid, authorized data-steward identity.
*   [ ] Staleness check: The review must have occurred within the last **30 days** (default).
*   [ ] Integrity check: The SHA-256 hash of the raw YAML content matches the registered state.

### 7. Lineage and Compliance Reporting
Lineage is recorded using a dual-write strategy to balance relational depth with semantic search capabilities.

| Storage Backend | Primary Use Case |
| :--- | :--- |
| **PostgreSQL** | Relational DAG traversal, compliance reporting, and audit table joins. |
| **Qdrant** | Semantic queries and "everything derived from X" impact analysis. |

**Classification-aware Durability:**
*   **Confidential/Restricted Data:** Both stores must successfully acknowledge the write. Failure to write to either store raises a `LineageWriteError` and blocks the pipeline.
*   **Public/Internal Data:** Failure in one store logs a `LINEAGE_GAP` warning but allows the pipeline to continue.

**Compliance Reporting:**
The system automatically generates **GDPR Article 30** processing records. It maps lineage and contract data to formal fields including processing purposes, data-subject categories, personal-data categories, recipients, retention periods, and specific technical safeguards.