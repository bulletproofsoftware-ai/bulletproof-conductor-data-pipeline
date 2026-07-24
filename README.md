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
