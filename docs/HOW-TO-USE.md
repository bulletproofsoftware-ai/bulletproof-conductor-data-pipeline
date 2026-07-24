# How to use — bulletproof-conductor-data-pipeline

This guide covers the two things you will do most often:

1. **Author and validate artifacts** — pipeline definitions, data contracts, and
   masking policies, against the JSON Schemas in [`schemas/`](../schemas).
2. **Call the MCP tools** — the 8 data tools, and run the `POST-DATA-PIPELINE` quality
   gate and the human-approval workflow.

All examples use the pure-Python layer; no container services are required unless noted.

## 1. Authoring artifacts

Artifacts are YAML documents with an `apiVersion: conductor-data/v1` and a `kind`
(`Pipeline`, `DataContract`, or `MaskingPolicy`). Each `kind` has a JSON Schema.

### A pipeline definition

A `Pipeline` names a source, one or more targets (each with a `tier` and a `masking`
policy reference), and optional `transform`, `lineage`, and `quality` sections. Required
top-level keys are `apiVersion`, `kind`, `metadata`, `source`, `targets`.

```yaml
apiVersion: conductor-data/v1
kind: Pipeline
metadata:
  id: customer-export-001
  name: Customer export to staging
  created_by: conductor-data-engineer
source:
  connector: postgres
  connection:
    host: source-db
    port: 5432
  extraction:
    mode: incremental          # full | incremental | cdc
    cursor_field: updated_at
    tables:
      - name: customers
        columns: [id, email, phone, updated_at]
targets:
  - tier: staging
    connector: postgres
    connection:
      host: staging-db
    masking: staging-policy      # references a MaskingPolicy by name
quality:
  assertions:
    - customers.id IS NOT NULL
    - customers.id IS UNIQUE
  on_failure: block              # block | warn
```

### Validating an artifact

```python
import json, yaml
from jsonschema import validate, Draft202012Validator

with open("schemas/pipeline.schema.json") as f:
    schema = json.load(f)
with open("customer-export.pipeline.yaml") as f:
    document = yaml.safe_load(f)

validate(instance=document, schema=schema, cls=Draft202012Validator)
print("Valid.")
```

The [`schemas/README.md`](../schemas/README.md) includes a ready-made batch validator
that dispatches on each document's `kind`.

## 2. The MCP tools

The tool layer is registered in [`tools/tool_registry.py`](../tools/tool_registry.py).
Get the registry and list the tools:

```python
from tools.tool_registry import get_registry

registry = get_registry()
print(registry.list_tools())
# ['data_connect', 'data_contract_validate', 'data_extract', 'data_lineage_query',
#  'data_load', 'data_mask', 'data_profile', 'data_transform']
```

Each tool has a governance classification:

| Tool | Classification | What it does |
|---|---|---|
| `data_connect` | Standard | Test connectivity to a source, return its schema catalog. |
| `data_contract_validate` | Standard | Validate pipeline + contract + policy consistency. |
| `data_lineage_query` | Standard | Query lineage: provenance, impact, PII audit, history. |
| `data_profile` | Elevated | Column types, cardinality, null rates, PII flags. |
| `data_extract` | Elevated | Extract with contract enforcement (no contract → refused). |
| `data_transform` | Elevated | join / filter / derive / aggregate via DuckDB. |
| `data_mask` | Elevated + Human Gate | Apply the masking policy; human approval for Confidential+. |
| `data_load` | Elevated + Human Gate | Atomic staged load; human approval for Confidential+. |

### Invoking a tool through the registry

Invoking through `registry.invoke(...)` runs the tool **and** applies governance: an
audit-trail entry is recorded for every *Elevated* / *Elevated + Human Gate* invocation.

```python
result = registry.invoke(
    "data_contract_validate",
    {"pipeline": pipeline_dict, "contract": contract_dict},
    caller="conductor-data-engineer",
)
print(result["status"])          # "success" | "error"

# Audit trail (elevated tools only)
for entry in registry.audit_trail:
    print(entry.tool_name, entry.caller, entry.result_status, entry.duration_ms)
```

`data_extract` enforces **CISO-CRITICAL-001**: it refuses to extract without a signed
data contract, except when `dry_run=true`, which returns only the schema, a row count,
and a 5-row sample.

### Contract-enforced extraction

Extraction requires a contract that the data steward has reviewed and signed. The
steward-review requirement is enforced architecturally with **no bypass** — see
[`contracts/steward_gate.py`](../contracts/steward_gate.py), which verifies the pipeline
has a populated, non-stale, hash-valid contract signed by a valid data steward before
execution proceeds.

## 3. Data quality assertions

Quality assertions are written in a small DSL (parsed by
[`quality/assertion_parser.py`](../quality/assertion_parser.py)) and executed against an
in-memory DuckDB database ([`quality/duckdb_executor.py`](../quality/duckdb_executor.py)).
Supported forms include:

```
table.column IS NOT NULL
table.column IS UNIQUE
table.column >= N
table.column BETWEEN N AND M
ROW_COUNT(table) > N
```

```python
from quality.duckdb_executor import DuckDBExecutor
from quality.assertion_engine import AssertionEngine

with DuckDBExecutor() as executor:
    executor.load_table("customers", [
        {"id": 1, "email": "a@example.com"},
        {"id": 2, "email": None},
    ])
    engine = AssertionEngine(executor)
    report = engine.run_assertions(
        assertions=["customers.id IS NOT NULL", "customers.id IS UNIQUE"],
        phase="pre_mask",
        on_failure="warn",     # "block" raises QualityAssertionError on failure
    )
    print(report.assertions_passed, report.assertions_failed)
```

## 4. The POST-DATA-PIPELINE quality gate

> **Import note.** The `gates` package aggregates the PII validator, which imports the
> masking-engine's Presidio client (`masking_engine.app.ner.presidio_client`). Because
> the masking-engine application is a container build target rather than vendored source
> (see [OVERVIEW.md](OVERVIEW.md) → *Scope*), importing from the `gates` package requires
> the masking-engine `app/` to be present on the path — as it is inside the built
> `masking-engine` container. When running the gate outside that container, provide the
> masking-engine app (mount or install it) so the Presidio client resolves.

Before a pipeline can progress, the blocking gate in
[`gates/post_data_pipeline.py`](../gates/post_data_pipeline.py) runs **6 checks**:

1. **Contract coverage** — every extracted column is defined in the contract.
2. **Quality assertions** — all assertions passed (pre-mask and post-mask).
3. **Masking correctness** — post-mask PII validation (samples rows, scans Confidential /
   Restricted columns for residual PII).
4. **Lineage completeness** — a lineage event was emitted for every expected operation.
5. **Restricted data check** — no restricted data leaks into non-production targets.
6. **Referential integrity** — FK relationships survive masking.

```python
from gates.post_data_pipeline import PostDataPipelineGate, PipelineContext

gate = PostDataPipelineGate(pii_validator=my_validator)   # validator optional
result = gate.evaluate(PipelineContext(
    pipeline_id="customer-export-001",
    target_tier="staging",
    contract=contract_dict,
    extracted_columns=["customers.id", "customers.email"],
    quality_results={"assertions_run": 2, "assertions_passed": 2, "assertions_failed": 0},
    expected_lineage_operations=["extract", "mask"],
    emitted_lineage_events=[{"operation": "extract"}, {"operation": "mask"}],
))
print(result.verdict)            # "PASS" or "FAIL"
print(result.failed_checks)      # names of any failed checks
```

The gate is **BLOCKING** — a `FAIL` verdict stops the pipeline. Results can be recorded
to `conductor-state.json` through the gate registry
([`gates/gate_registry.py`](../gates/gate_registry.py)).

## 5. Human approval for sensitive operations

`data_mask` and `data_load` on Confidential / Restricted data require a human decision.
The workflow ([`gates/human_approval.py`](../gates/human_approval.py)) issues single-use,
time-limited, 256-bit random tokens bound to a `pipeline_execution_id` + `contract_version`.

```python
from gates.human_approval import HumanApprovalWorkflow, ApprovalDecision

wf = HumanApprovalWorkflow()                       # default 24h token TTL

if wf.requires_approval("data_mask", "confidential"):
    token = wf.generate_token(
        pipeline_execution_id="run-2026-07-24-001",
        contract_version="v3",
    )
    # ... present token.payload to the reviewer out of band ...
    ok, msg = wf.process_decision(
        token.token_hex, ApprovalDecision.APPROVE,
        ip_address="10.0.0.5", reason="Reviewed masked sample",
    )
    print(wf.get_decision(token.token_hex))        # ApprovalDecision.APPROVE
```

Tokens are single-use, expire (auto-rejected on timeout), and every access — including
rejected attempts — is written to the workflow's audit log.

## 6. Querying lineage

The lineage query engine ([`lineage/query.py`](../lineage/query.py)) routes queries to
the right store:

- **provenance** — DAG walk backward from a target to its sources.
- **impact_analysis** — forward walk from a source to all downstream targets.
- **pii_audit** — all Confidential / Restricted events in a time range.
- **pipeline_history** — all executions of a pipeline, newest first.

Relational queries go to PostgreSQL; "everything derived from X" semantic queries go to
Qdrant. Call it through the `data_lineage_query` tool for governance and audit.

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
