# Conductor Data Pipeline JSON Schemas

JSON Schema (draft 2020-12) definitions for validating Conductor Data Pipeline YAML artifacts.

## Schemas

| File | Validates |
|---|---|
| `pipeline.schema.json` | Pipeline definition YAML (`kind: Pipeline`) |
| `contract.schema.json` | Data contract YAML (`kind: DataContract`) |
| `masking-policy.schema.json` | Masking policy YAML (`kind: MaskingPolicy`) |
| `lineage-event.schema.json` | Lineage event payloads (PROV-AGENT extension) |
| `conductor-state-data.schema.json` | `data_pipelines` extension to conductor-state.json |

## Validation with Python

Install dependencies:

```bash
pip install jsonschema pyyaml
```

Validate a pipeline definition:

```python
import json
import yaml
from jsonschema import validate, Draft202012Validator

# Load the schema
with open("schemas/pipeline.schema.json") as f:
    schema = json.load(f)

# Load the YAML artifact
with open("pipeline/customer-data.pipeline.yaml") as f:
    document = yaml.safe_load(f)

# Validate (raises jsonschema.ValidationError on failure)
validate(instance=document, schema=schema, cls=Draft202012Validator)
print("Valid.")
```

Validate a data contract:

```python
with open("schemas/contract.schema.json") as f:
    schema = json.load(f)

with open("contracts/customer-data.contract.yaml") as f:
    document = yaml.safe_load(f)

validate(instance=document, schema=schema, cls=Draft202012Validator)
```

Validate a masking policy:

```python
with open("schemas/masking-policy.schema.json") as f:
    schema = json.load(f)

with open("policies/staging-policy.yaml") as f:
    document = yaml.safe_load(f)

validate(instance=document, schema=schema, cls=Draft202012Validator)
```

## Batch Validation

```python
import json
import yaml
import sys
from pathlib import Path
from jsonschema import validate, Draft202012Validator, ValidationError

SCHEMA_MAP = {
    "Pipeline": "schemas/pipeline.schema.json",
    "DataContract": "schemas/contract.schema.json",
    "MaskingPolicy": "schemas/masking-policy.schema.json",
}

def validate_file(yaml_path: str) -> bool:
    with open(yaml_path) as f:
        doc = yaml.safe_load(f)

    kind = doc.get("kind")
    schema_path = SCHEMA_MAP.get(kind)
    if not schema_path:
        print(f"SKIP {yaml_path}: unknown kind '{kind}'")
        return True

    with open(schema_path) as f:
        schema = json.load(f)

    try:
        validate(instance=doc, schema=schema, cls=Draft202012Validator)
        print(f"PASS {yaml_path}")
        return True
    except ValidationError as e:
        print(f"FAIL {yaml_path}: {e.message}")
        return False

if __name__ == "__main__":
    files = sys.argv[1:]
    results = [validate_file(f) for f in files]
    sys.exit(0 if all(results) else 1)
```

Usage:

```bash
python validate.py pipeline/*.yaml contracts/*.yaml policies/*.yaml
```

## Notes

- All schemas use JSON Schema draft 2020-12.
- `${VARIABLE}` placeholders in YAML are treated as plain strings and pass validation.
- The `format: date-time` annotation in `conductor-state-data.schema.json` is advisory unless a format checker is explicitly enabled in your validator.
