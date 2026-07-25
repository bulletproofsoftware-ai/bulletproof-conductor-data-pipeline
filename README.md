# bulletproof-conductor-data-pipeline

**A data pipeline with masking, anonymization, lineage, and human approval gates.**

![bulletproof-conductor-data-pipeline — overview](docs/media/infographic.png)

`bulletproof-conductor-data-pipeline` moves data through contract-validated pipelines
while enforcing masking and anonymization policies, tracking lineage, and gating
sensitive operations behind human approval. It includes a NER-based masking engine
that consistently tokenizes PII (e.g. a name maps to the same token everywhere it
appears, across structured and free-text columns).

> [!IMPORTANT]
> **The `masking-engine` container will not run from this repository.**
> This repo vendors only the masking engine's *client contract*
> (`masking_engine/app/ner/presidio_client.py`), so that `gates.pii_validator`
> and the test suite import cleanly. The FastAPI application source the
> Dockerfile's `CMD` expects — the `app.main` entrypoint, the concrete Presidio
> analyzer/anonymizer wiring, the tokenization/FPE/redaction strategies, and
> Vault key resolution — is **not** vendored here and is supplied to the image
> build separately.
>
> Consequences: `docker compose -f docker-compose.data-pipeline.yml up` starts
> the other services, but the `masking-engine` container fails to start and
> restarts in a loop. Everything else in this repository — the contracts,
> gates, lineage, quality checks, schemas, and the full 891-test suite — is
> complete and runs standalone. Treat the masking engine as a documented
> integration point you supply, not as a shipped runnable service. See
> [docs/INSTALL.md](docs/INSTALL.md) for the full breakdown.

## Features

- **Masking engine** — policy-driven masking + NER anonymization with cross-column
  consistent tokenization.
- **Contracts** — pipelines are validated against JSON-schema data contracts
  (see [`schemas/`](schemas/)).
- **Lineage** — emits lineage events for every transformation.
- **Human approval** — sensitive steps require a signed approval decision.

## Documentation

Full documentation lives in [`docs/`](docs/): [overview](docs/OVERVIEW.md),
[install](docs/INSTALL.md), [how-to-use](docs/HOW-TO-USE.md),
[administrator guide](docs/ADMINISTRATOR.md), [SBOM](docs/SBOM.md), and the
[security scan report](docs/scan/scan-report.md) (0 critical / 0 high).

## Media

A generated system-overview briefing is in [`media/`](media/)
([briefing](media/system-overview.md)).

## Schemas

The pipeline, contract, masking-policy, lineage-event, and state schemas live in
[`schemas/`](schemas/).

## Development

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest          # 891 tests, no external services required
```

Copy [`.env.example`](.env.example) to `.env` and fill in the placeholders
before bringing up the Docker stack. See [docs/INSTALL.md](docs/INSTALL.md).

## License

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
