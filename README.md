# bulletproof-conductor-data-pipeline

**A data pipeline with masking, anonymization, lineage, and human approval gates.**

`bulletproof-conductor-data-pipeline` moves data through contract-validated pipelines
while enforcing masking and anonymization policies, tracking lineage, and gating
sensitive operations behind human approval. It includes a NER-based masking engine
that consistently tokenizes PII (e.g. a name maps to the same token everywhere it
appears, across structured and free-text columns).

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
pip install -r requirements.txt
python -m pytest
```

## License

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
