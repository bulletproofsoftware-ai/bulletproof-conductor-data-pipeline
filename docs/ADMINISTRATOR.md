# Administrator guide — bulletproof-conductor-data-pipeline

This guide is for operators running the pipeline: configuration, secret management, the
container stack, key rotation, lineage stores, and audit/compliance operations. It
documents only what exists in this repository; where a capability depends on an external
system (Vault, a real Qdrant/Postgres, a running Presidio), that is called out.

## Configuration surface

The pipeline is configured through **environment variables** (read at runtime), the
**compose file**, and the **YAML artifacts** (pipelines, contracts, masking policies).

### Environment variables

Consumed by the container services in
[`docker-compose.data-pipeline.yml`](../docker-compose.data-pipeline.yml):

| Variable | Service | Purpose |
|---|---|---|
| `AIRBYTE_DB_PASSWORD` | `airbyte-db`, `airbyte-server` | Airbyte internal Postgres password. |
| `VAULT_ADDR` | `masking-engine` | HashiCorp Vault address. |
| `VAULT_TOKEN` | `masking-engine` | Vault token / AppRole credential. |
| `MASKING_MASTER_SEED` | `masking-engine` | Seed for deterministic, consistent tokenization. |
| `PRESIDIO_ENDPOINT` | `masking-engine` | URL of the Presidio analyzer (defaults to the in-network `presidio-analyzer:5002`). |
| `PIPELINE_ARTIFACTS_DIR` | `masking-engine` | Mount point for the shared `pipeline-artifacts` volume. |

Provide these through an `.env` file next to the compose file. **Never commit `.env`** —
it is excluded by [`.gitignore`](../.gitignore).

## Secret resolution (three-tier)

Credentials are resolved by [`tools/credential_resolver.py`](../tools/credential_resolver.py)
in a fixed order, first hit wins:

1. **HashiCorp Vault** (via `hvac` + AppRole).
2. **Docker secrets** — files under `/run/secrets/`.
3. **Environment variables**.

Every credential access is logged, and credentials are held in memory only for the
duration of use. Pipeline definitions must **never** embed credentials — this is a hard
constraint on the data-engineer agent (see
[`agents/conductor-data-engineer.yaml`](../agents/conductor-data-engineer.yaml)).

## Running the container stack

```bash
# one-time setup: validate prerequisites, create volumes, pull/build images, start,
# wait for health, then run the healthcheck
bash scripts/setup.sh

# ongoing:
docker compose -f docker-compose.data-pipeline.yml up -d      # start
docker compose -f docker-compose.data-pipeline.yml ps         # status
docker compose -f docker-compose.data-pipeline.yml down       # stop
bash scripts/healthcheck.sh                                    # verify all 6 healthy
```

The stack has a **memory budget of ~5.3 GB** (per-service `mem_limit` values sum to
under 6 GB): `airbyte-server` 2 GB, `airbyte-worker` 1 GB, `unstructured-api` 1 GB,
`masking-engine` 512 MB, `presidio-analyzer` 512 MB, `airbyte-db` 256 MB.

No ports are published to the host — the network is internal only, and the MCP tool layer
is the sole interface. The `masking-engine` container runs as a **non-root user**
(`appuser`, uid 1001) per its [`Dockerfile`](../masking_engine/Dockerfile).

## Lineage stores

Lineage is dual-written (see [`lineage/emitter.py`](../lineage/emitter.py)):

- **PostgreSQL** ([`lineage/pg_writer.py`](../lineage/pg_writer.py)) for relational DAG
  traversal, compliance reporting, and joins against existing audit tables. Tests use an
  in-memory dict-backed writer that implements the same interface; the real `asyncpg`
  implementation runs in production.
- **Qdrant** ([`lineage/qdrant_writer.py`](../lineage/qdrant_writer.py)) for semantic
  queries. Point IDs are deterministic (derived from a SHA-256 content fingerprint) so
  upserts are idempotent.

**Classification-aware durability:** for Confidential / Restricted events, *both* stores
must accept the write or a `LineageWriteError` is raised and the pipeline blocks — no
audit trail for sensitive data is unacceptable. For Public / Internal events, a single
store failure logs a `LINEAGE_GAP` warning and the pipeline continues.

OpenTelemetry spans are emitted per operation by
[`lineage/otel_emitter.py`](../lineage/otel_emitter.py); if an OTLP endpoint is
configured, spans are exported, otherwise they are logged as structured JSON.

## Masking key rotation

FPE masking keys are versioned and rotated on a schedule by
[`gates/key_rotation.py`](../gates/key_rotation.py):

- **Quarterly rotation** (90-day interval by default).
- A **7-day warning** window before rotation is due; overdue keys are flagged.
- **One retention cycle** — the immediately previous key version is retained so
  previously masked data can still be decrypted; older versions are rotated out.
- Every pipeline execution records the key version it used, and this is written into
  lineage. A version-mismatch check flags data that was masked with a non-current key.

Operational routine:

```python
from gates.key_rotation import KeyRotationTracker

tracker = KeyRotationTracker()          # 90-day interval, 7-day warning
tracker.initialize_key()                # first key: v1

status, warning = tracker.check_rotation_status()
if warning:
    print(warning.message)              # WARNING / OVERDUE with days remaining
    new_key, _ = tracker.rotate()       # v1 -> RETAINED, v2 -> CURRENT
```

## Governance and audit

The tool registry ([`tools/tool_registry.py`](../tools/tool_registry.py)) records an
**audit-trail entry for every Elevated / Elevated + Human Gate tool invocation** —
tool name, classification, caller, a redacted parameter summary, result status, and
duration. Sensitive parameters (credential resolvers, executors, query engines, target
stores) are excluded from the summary.

The human-approval workflow ([`gates/human_approval.py`](../gates/human_approval.py))
maintains its own audit log capturing token ID, IP, decision, and reason for every
access, **including rejected attempts and timeouts**.

### Steward review is mandatory

[`contracts/steward_gate.py`](../contracts/steward_gate.py) enforces steward review
before any pipeline execution and has **no bypass mechanism**. It verifies:

1. a `conductor-state.json` entry exists for the pipeline,
2. the `contract` field is populated (steward reviewed it),
3. the contract's `steward` is a valid data-steward identity,
4. the contract's `reviewed_at` is not stale (default 30 days), and
5. the contract hash is valid (integrity check).

### Artifact integrity

[`contracts/artifact_integrity.py`](../contracts/artifact_integrity.py) computes a
SHA-256 hash over raw YAML content (catching formatting changes) for pipelines,
contracts, and masking policies, registers it in `conductor-state.json`, and verifies it
before each use. On mismatch it raises `INTEGRITY_VIOLATION`, blocks the pipeline, and
emits an alert.

## GDPR Article 30 records

[`compliance/gdpr_article30.py`](../compliance/gdpr_article30.py) generates an Article 30
processing record from lineage — mapping controller, processor, processing purposes,
data-subject categories, personal-data categories, recipients, retention periods, and
technical safeguards from the corresponding lineage / contract fields. It is invoked by
the compliance agent via the lineage query tool.

## conductor-state.json

Runtime state (`conductor-state.json` at the repo root) is **git-ignored** — it is a
runtime file, not committed configuration. The gate registry writes gate verdicts into
it atomically (temp file + `os.replace`, avoiding a TOCTOU race). The
[`schemas/conductor-state-data.schema.json`](../schemas/conductor-state-data.schema.json)
schema describes the `data_pipelines` extension to that state file.

## Health and troubleshooting

- **All-services health:** `bash scripts/healthcheck.sh` (exit 0 = all healthy).
- **A gate keeps failing:** inspect `GateResult.failed_checks` — it names exactly which
  of the 6 checks failed and includes per-check detail metadata.
- **Lineage gap warnings:** for Public/Internal events one store may be down; for
  Confidential/Restricted a `LineageWriteError` blocks — check both Postgres and Qdrant.
- **Key rotation overdue:** run `KeyRotationTracker.check_rotation_status()` and rotate.

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
