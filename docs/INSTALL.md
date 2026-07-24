# Install — bulletproof-conductor-data-pipeline

This repository has two layers that install independently:

1. **The Python subsystem** (contracts, gates, lineage, quality, tools, compliance,
   agent/schema definitions) — pure Python, installs with `pip`.
2. **The container services** (Airbyte, the masking engine, Unstructured.io, Presidio)
   — orchestrated with Docker Compose.

You can install and exercise the Python layer on its own; the container layer is only
needed to run live extractions, the masking service, and NER-based PII detection.

## Prerequisites

- **Python 3.11 or 3.12** (CI runs on 3.12; the masking-engine container uses 3.11).
- **pip**.
- For the container layer: **Docker** with the Compose plugin.

## 1. Python subsystem

```bash
git clone https://github.com/bulletproofsoftware-ai/bulletproof-conductor-data-pipeline.git
cd bulletproof-conductor-data-pipeline

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

`requirements.txt` pulls the core dependencies:

| Dependency | Purpose |
|---|---|
| `jsonschema` | Validate pipeline / contract / policy / lineage artifacts. |
| `pyyaml` | Parse the YAML artifact definitions. |
| `requests` | HTTP client used by the tool layer. |
| `duckdb` | In-memory SQL engine for transforms and quality assertions. |
| `qdrant-client` | Semantic lineage store client. |
| `asyncpg` | PostgreSQL driver for the relational lineage store. |
| `opentelemetry-api`, `opentelemetry-sdk` | Tracing / span emission. |
| `pytest` | Test runner. |

Some sub-packages declare additional dependencies for their container or optional
features — see [`lineage/requirements.txt`](../lineage/requirements.txt),
[`quality/requirements.txt`](../quality/requirements.txt), and
[`masking_engine/requirements.txt`](../masking_engine/requirements.txt).

### Run the tests

```bash
python -m pytest
```

> **Note on the test suite.** Most of the suite runs against the pure-Python packages
> with in-memory stubs (an in-memory Qdrant client, a dict-backed Postgres writer,
> in-memory DuckDB). The PII-related tests (`test_pii_validator.py`,
> `test_post_data_pipeline_gate.py`) — and, transitively, everything that imports the
> `gates` package such as `test_human_approval.py` and `test_key_rotation.py` — depend on
> `masking_engine.app.ner.presidio_client`. That module ships the **client contract** the
> pipeline codes against (`BasePresidioClient`, `RecognizedEntity`, and a dependency-free
> `MockPresidioClient` used by the tests); it imports and runs with the Python standard
> library alone, so these tests run out of the box with no extra services:
>
> ```bash
> python -m pytest tests/test_pii_validator.py \
>                  tests/test_post_data_pipeline_gate.py \
>                  tests/test_human_approval.py \
>                  tests/test_key_rotation.py
> ```
>
> The **concrete** Presidio analyzer implementation of `BasePresidioClient` (a real
> `AnalyzerEngine` wrapper backed by spaCy models) is provided by the masking-engine
> service at runtime and built into its container image — it is intentionally not vendored
> here, so the gates import and test cleanly without the heavy Presidio + model
> dependencies.
>
> Other tests still require optional back-end drivers that are not installed by the base
> requirements (`duckdb`, `qdrant-client`, `opentelemetry-*`); install those extras, or
> skip the corresponding modules, to run the full suite locally.
>
> CI (`.github/workflows/ci.yml`) compiles all Python as its hard gate and runs the test
> suite non-blockingly (services required by some tests are not present in CI).

## 2. Container services (optional)

The full runtime is defined in
[`docker-compose.data-pipeline.yml`](../docker-compose.data-pipeline.yml). It brings up
6 containers on an **internal-only** network — no ports are published to the host; agents
reach the pipeline exclusively through the MCP tool layer.

The compose file references environment variables for secrets (Airbyte DB password,
Vault address/token, masking master seed). Provide them via an `.env` file next to the
compose file before bringing the stack up. Required variables are:

| Variable | Used by | Purpose |
|---|---|---|
| `AIRBYTE_DB_PASSWORD` | `airbyte-db`, `airbyte-server` | Airbyte internal Postgres password. |
| `VAULT_ADDR` | `masking-engine` | HashiCorp Vault address for secret resolution. |
| `VAULT_TOKEN` | `masking-engine` | Vault token / AppRole credential. |
| `MASKING_MASTER_SEED` | `masking-engine` | Seed for deterministic tokenization. |

```bash
# create .env with the variables above (do not commit it), then:
docker compose -f docker-compose.data-pipeline.yml up -d
```

The `masking-engine` service is **built from** [`./masking_engine`](../masking_engine)
using its [`Dockerfile`](../masking_engine/Dockerfile). That image runs the FastAPI
masking application. The published tree vendors only the **client contract** the pipeline
codes against — [`masking_engine/app/ner/presidio_client.py`](../masking_engine/app/ner/presidio_client.py)
(`BasePresidioClient` / `RecognizedEntity`) — so `gates.pii_validator` imports cleanly. The
remainder of the FastAPI application source (the `app.main` entrypoint referenced by the
Dockerfile `CMD`, the concrete Presidio analyzer/anonymizer wiring, tokenization/FPE/redaction
strategies, and Vault key resolution) is supplied to the image build separately and is not
part of this published tree.

### Health checks

Every long-lived service defines a Docker healthcheck. A convenience script is provided:

```bash
bash scripts/healthcheck.sh
```

## Verifying the install

```bash
python -c "from tools.tool_registry import get_registry; \
print(sorted(get_registry().list_tools()))"
```

Expected output — the 8 registered MCP tools:

```
['data_connect', 'data_contract_validate', 'data_extract', 'data_lineage_query', 'data_load', 'data_mask', 'data_profile', 'data_transform']
```

## Uninstall

```bash
docker compose -f docker-compose.data-pipeline.yml down -v   # containers + volumes
deactivate && rm -rf .venv                                    # Python environment
```

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
