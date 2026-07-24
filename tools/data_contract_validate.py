"""
data_contract_validate MCP Tool -- Validate pipeline + contract + policy consistency.

Uses JSON schemas from schemas/ to validate structure, then checks semantic
consistency across the three artifacts. Standard governance classification.
"""

import json
import logging
import os
import time

from jsonschema import validate, Draft202012Validator, ValidationError

logger = logging.getLogger(__name__)

# Schema file paths
_SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")

_SCHEMA_CACHE: dict[str, dict] = {}


def _load_schema(name: str) -> dict:
    """Load and cache a JSON schema."""
    if name not in _SCHEMA_CACHE:
        path = os.path.join(_SCHEMAS_DIR, name)
        with open(path) as f:
            _SCHEMA_CACHE[name] = json.load(f)
    return _SCHEMA_CACHE[name]


def _validate_structure(artifact: dict, schema_name: str) -> list[str]:
    """Validate an artifact against its JSON schema, return list of errors."""
    try:
        schema = _load_schema(schema_name)
        validate(instance=artifact, schema=schema, cls=Draft202012Validator)
        return []
    except ValidationError as exc:
        return [f"Schema validation error: {exc.message}"]
    except FileNotFoundError:
        return [f"Schema file not found: {schema_name}"]


def _check_contract_covers_pipeline(pipeline: dict, contract: dict) -> list[str]:
    """Check that the contract covers all columns in the pipeline's source tables."""
    errors = []
    contract_columns = set(contract.get("columns", {}).keys())

    source = pipeline.get("source", {})
    tables = source.get("extraction", {}).get("tables", [])

    for table_spec in tables:
        table_name = table_spec.get("name", "")
        columns = table_spec.get("columns", [])
        if not columns:
            # Empty columns list means "extract all" -- contract must have
            # at least one entry for this table name.
            has_table_entry = any(
                col_key.startswith(f"{table_name}.") for col_key in contract_columns
            )
            if not has_table_entry:
                errors.append(
                    f"Pipeline table '{table_name}' extracts all columns but contract has no entries for it"
                )
        else:
            for col in columns:
                qualified = f"{table_name}.{col}"
                if qualified not in contract_columns:
                    errors.append(f"Pipeline column '{qualified}' not covered by contract")

    return errors


def _check_contract_pipeline_ref(pipeline: dict, contract: dict) -> list[str]:
    """Check that the contract references the correct pipeline."""
    pipeline_id = pipeline.get("metadata", {}).get("id", "")
    contract_ref = contract.get("metadata", {}).get("pipeline_ref", "")

    if pipeline_id and contract_ref and pipeline_id != contract_ref:
        return [
            f"Contract pipeline_ref '{contract_ref}' does not match pipeline id '{pipeline_id}'"
        ]
    return []


def _check_policy_tier_match(pipeline: dict, policy: dict) -> list[str]:
    """Check that the masking policy tier matches a pipeline target tier."""
    errors = []
    policy_tier = policy.get("metadata", {}).get("tier", "")

    if not policy_tier:
        return []

    target_tiers = [
        t.get("tier", "") for t in pipeline.get("targets", [])
    ]

    if policy_tier not in target_tiers:
        errors.append(
            f"Policy tier '{policy_tier}' does not match any pipeline target tier: {target_tiers}"
        )

    return errors


def _check_assertions_valid(pipeline: dict) -> list[str]:
    """Basic validation of quality assertion strings."""
    errors = []
    quality = pipeline.get("quality", {})
    assertions = quality.get("assertions", [])

    for i, assertion in enumerate(assertions):
        if not isinstance(assertion, str) or not assertion.strip():
            errors.append(f"Assertion at index {i} is empty or not a string")

    return errors


def _check_classification_coverage(contract: dict) -> list[str]:
    """Check that all columns have valid classifications."""
    errors = []
    valid_classifications = {"public", "internal", "confidential", "restricted"}

    for col_name, col_def in contract.get("columns", {}).items():
        cls = col_def.get("classification", "")
        if cls not in valid_classifications:
            errors.append(
                f"Column '{col_name}' has invalid classification '{cls}'"
            )
        # Check PII consistency
        if col_def.get("pii") and not col_def.get("pii_type"):
            # pii_type is optional per schema but recommended
            pass  # Not an error, just informational

    return errors


def execute(params: dict) -> dict:
    """
    Validate pipeline definition, data contract, and masking policy for consistency.

    Args:
        params: Dict with keys:
            - pipeline (dict): Pipeline definition
            - contract (dict): Data contract
            - policy (dict, optional): Masking policy

    Returns:
        Dict with status, data (validation results), and metadata.
    """
    pipeline = params.get("pipeline", {})
    contract = params.get("contract", {})
    policy = params.get("policy")

    start_time = time.monotonic()

    all_errors: list[str] = []
    all_warnings: list[str] = []

    # Step 1: Validate pipeline structure
    if pipeline:
        errors = _validate_structure(pipeline, "pipeline.schema.json")
        all_errors.extend(errors)

    # Step 2: Validate contract structure
    if contract:
        errors = _validate_structure(contract, "contract.schema.json")
        all_errors.extend(errors)

    # Step 3: Validate policy structure (if provided)
    if policy:
        errors = _validate_structure(policy, "masking-policy.schema.json")
        all_errors.extend(errors)

    # Step 4: Semantic consistency checks (only if structures are valid)
    if pipeline and contract and not all_errors:
        # Check contract covers pipeline columns
        coverage_errors = _check_contract_covers_pipeline(pipeline, contract)
        all_errors.extend(coverage_errors)

        # Check contract references correct pipeline
        ref_errors = _check_contract_pipeline_ref(pipeline, contract)
        all_errors.extend(ref_errors)

        # Check classification coverage
        cls_errors = _check_classification_coverage(contract)
        all_errors.extend(cls_errors)

        # Check assertions
        assertion_errors = _check_assertions_valid(pipeline)
        all_errors.extend(assertion_errors)

    if pipeline and policy and not all_errors:
        # Check policy tier matches pipeline targets
        tier_errors = _check_policy_tier_match(pipeline, policy)
        all_warnings.extend(tier_errors)

    elapsed = (time.monotonic() - start_time) * 1000
    is_valid = len(all_errors) == 0

    return {
        "status": "success" if is_valid else "error",
        "data": {
            "valid": is_valid,
            "errors": all_errors,
            "warnings": all_warnings,
        },
        "metadata": {
            "tool": "data_contract_validate",
            "elapsed_ms": round(elapsed, 2),
        },
    }
