# Software Bill of Materials (SBOM)

A machine-readable CycloneDX SBOM is committed at
[`bulletproof-conductor-data-pipeline.cyclonedx.json`](bulletproof-conductor-data-pipeline.cyclonedx.json)
(CycloneDX spec version 1.6, JSON). It was generated from the resolved dependency tree of
the project's [`requirements.txt`](../requirements.txt) — the 9 direct dependencies plus
their transitive dependencies — for a total of **39 components**.

Regenerate it with:

```bash
python -m venv /tmp/sbomvenv && /tmp/sbomvenv/bin/pip install -r requirements.txt
pip install cyclonedx-bom
cyclonedx-py environment /tmp/sbomvenv --output-format json \
  > docs/bulletproof-conductor-data-pipeline.cyclonedx.json
```

## Direct Python dependencies

From [`requirements.txt`](../requirements.txt). Versions below are the ones resolved for
the committed SBOM; the manifest itself pins lower bounds (`>=`).

| Package | Resolved version | License | Role |
|---|---|---|---|
| `jsonschema` | 4.26.0 | MIT | Validate pipeline / contract / policy / lineage artifacts. |
| `PyYAML` | 6.0.3 | MIT | Parse YAML artifact definitions. |
| `requests` | 2.34.2 | Apache-2.0 | HTTP client for the tool layer. |
| `duckdb` | 1.5.5 | MIT | In-memory SQL engine for transforms and quality assertions. |
| `qdrant-client` | 1.18.0 | Apache-2.0 | Semantic lineage store client. |
| `asyncpg` | 0.31.0 | Apache-2.0 | PostgreSQL driver for relational lineage. |
| `opentelemetry-api` | 1.44.0 | Apache-2.0 | Tracing API. |
| `opentelemetry-sdk` | 1.44.0 | Apache-2.0 | Tracing SDK / span emission. |
| `pytest` | 9.1.1 | MIT | Test runner. |

Sub-packages declare additional dependencies for their container or optional features:
[`lineage/requirements.txt`](../lineage/requirements.txt) (adds `aiosqlite`,
`opentelemetry-exporter-otlp`), [`quality/requirements.txt`](../quality/requirements.txt),
and [`masking_engine/requirements.txt`](../masking_engine/requirements.txt) (FastAPI,
uvicorn, `hvac`, `pyffx`, `pydantic`, `httpx`, `faker` — installed inside the
masking-engine container image, not by the root `requirements.txt`).

## License distribution (all 39 components)

| License | Components |
|---|---|
| MIT | 22 |
| Apache-2.0 | 9 |
| BSD-3-Clause | 4 |
| MPL-2.0 | 2 |
| BSD-2-Clause | 1 |
| BSD (unspecified variant) | 1 |
| `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | 1 |
| `Apache-2.0 OR BSD-2-Clause` | 1 |
| PSF-2.0 | 1 |
| (none declared in metadata) | 1 |

All resolved licenses are permissive (MIT / Apache-2.0 / BSD / MPL-2.0 / PSF / ISC-class).
No copyleft (GPL/AGPL) licenses are present in the runtime tree. The single "(none
declared)" entry lacks a machine-readable license classifier in its package metadata; it
is a transitive dependency, not a direct one.

## Container base images

The runtime containers pull upstream base images (see
[`docker-compose.data-pipeline.yml`](../docker-compose.data-pipeline.yml)); these are
outside the Python SBOM above:

| Image | Provenance |
|---|---|
| `python:3.11-slim` | Base for the `masking-engine` build ([`masking_engine/Dockerfile`](../masking_engine/Dockerfile)). |
| `postgres:15` | Airbyte internal state database. |
| `airbyte/server:latest`, `airbyte/worker:latest` | Airbyte connector orchestration / execution. |
| `quay.io/unstructured-io/unstructured-api:latest` | Document parsing. |
| `mcr.microsoft.com/presidio-analyzer:latest` | NER-based PII detection. |

For reproducible deployments, pin the `:latest` tags to specific digests before
production use.

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
