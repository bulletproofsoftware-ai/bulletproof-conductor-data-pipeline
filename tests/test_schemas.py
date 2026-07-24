"""
Test suite for Conductor Data Pipeline JSON Schemas.

Validates canonical YAML examples from SPEC.md, rejects invalid variants,
and tests edge cases for all five schemas.
"""

import json
import os
import copy
import pytest
import yaml
from jsonschema import validate, Draft202012Validator, ValidationError

# ---------------------------------------------------------------------------
# Schema loading helpers
# ---------------------------------------------------------------------------

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")


def _load_schema(name: str) -> dict:
    path = os.path.join(SCHEMA_DIR, name)
    with open(path) as f:
        return json.load(f)


PIPELINE_SCHEMA = _load_schema("pipeline.schema.json")
CONTRACT_SCHEMA = _load_schema("contract.schema.json")
MASKING_SCHEMA = _load_schema("masking-policy.schema.json")
LINEAGE_SCHEMA = _load_schema("lineage-event.schema.json")
STATE_SCHEMA = _load_schema("conductor-state-data.schema.json")


def _validate(instance, schema):
    """Validate instance against schema using draft 2020-12."""
    validate(instance=instance, schema=schema, cls=Draft202012Validator)


def _assert_invalid(instance, schema):
    """Assert that instance fails validation."""
    with pytest.raises(ValidationError):
        _validate(instance, schema)


# ===================================================================
# CANONICAL FIXTURES (from SPEC.md)
# ===================================================================

CANONICAL_PIPELINE = yaml.safe_load("""
apiVersion: conductor-data/v1
kind: Pipeline
metadata:
  id: pipe-001
  name: customer-data-extract
  brd_refs: [REQ-012, REQ-013]
  created_by: nhi_data-engineer_20260318_a1b2c3d4

source:
  connector: airbyte/source-postgres
  connection:
    host: "${PROD_DB_HOST}"
    port: 5432
    database: customers
    schema: public
  extraction:
    mode: incremental
    cursor_field: updated_at
    tables:
      - name: customers
        columns: [id, name, email, phone, address, created_at, tier]
      - name: orders
        columns: [id, customer_id, amount, status, created_at]
        filter: "status != 'draft'"

transform:
  - operation: join
    left: customers
    right: orders
    on: customers.id = orders.customer_id
    type: left
  - operation: derive
    field: lifetime_value
    expression: "SUM(orders.amount) GROUP BY customers.id"
  - operation: classify
    auto: true

targets:
  - tier: production
    connector: airbyte/destination-postgres
    connection:
      host: "${PROD_TARGET_HOST}"
      database: app_db
    masking: none
  - tier: staging
    connector: airbyte/destination-postgres
    connection:
      host: "${STAGING_DB_HOST}"
      database: app_db
    masking: staging-policy
  - tier: development
    connector: airbyte/destination-postgres
    connection:
      host: "${DEV_DB_HOST}"
      database: app_db
    masking: dev-policy

lineage:
  enabled: true
  emit_to: [qdrant, postgresql]
  classification_audit: true

quality:
  assertions:
    - "customers.email IS NOT NULL"
    - "customers.id IS UNIQUE"
    - "orders.amount >= 0"
    - "ROW_COUNT(customers) > 0"
  on_failure: block
""")

CANONICAL_CONTRACT = yaml.safe_load("""
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
  steward: nhi_data-steward_20260318_e5f6g7h8
  reviewed_at: "2026-03-18T14:30:00Z"
  classification_version: 1

columns:
  customers.id:
    classification: internal
    pii: false
  customers.name:
    classification: confidential
    pii: true
    pii_type: PERSON
  customers.email:
    classification: confidential
    pii: true
    pii_type: EMAIL
  customers.phone:
    classification: confidential
    pii: true
    pii_type: PHONE
  customers.address:
    classification: restricted
    pii: true
    pii_type: ADDRESS
  customers.created_at:
    classification: internal
    pii: false
  customers.tier:
    classification: public
    pii: false
  orders.id:
    classification: internal
    pii: false
  orders.customer_id:
    classification: internal
    pii: false
  orders.amount:
    classification: confidential
    pii: false
  orders.status:
    classification: public
    pii: false
  orders.created_at:
    classification: internal
    pii: false
  lifetime_value:
    classification: confidential
    pii: false

governance:
  human_review_required: true
  retention_days: 90
  audit_frequency: weekly

quality_signoff: true
""")

CANONICAL_MASKING = yaml.safe_load("""
apiVersion: conductor-data/v1
kind: MaskingPolicy
metadata:
  name: staging-policy
  tier: staging
  description: "Masked production data preserving referential integrity"

defaults:
  strategy: tokenize
  deterministic: true
  seed: "${MASKING_SEED}"

rules:
  - classification: restricted
    action: redact

  - classification: confidential
    fields:
      - pattern: "*.email"
        strategy: format_preserve_encrypt
        format: "user_{token}@example.com"
      - pattern: "*.phone"
        strategy: format_preserve_encrypt
        format: "+1-555-{token}"
      - pattern: "*.ssn"
        strategy: redact
      - pattern: "*.name"
        strategy: tokenize
        prefix: "NAME_"

  - classification: internal
    strategy: tokenize
    deterministic: true

  - classification: public
    strategy: passthrough

unstructured_rules:
  enabled: true
  ner_model: "presidio"
  entities: [PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, ADDRESS]
  replacement: tokenize

referential_integrity:
  enabled: true
  consistency_scope: pipeline
""")

CANONICAL_LINEAGE = yaml.safe_load("""
event:
  gov_agent_id: nhi_data-engineer_20260318_a1b2c3d4
  gov_session_id: sess_abc123
  gov_classification: confidential
  gov_timestamp: "2026-03-18T14:32:00Z"

  pipeline_id: pipe-001
  operation: extract
  source:
    connector: airbyte/source-postgres
    table: customers
    columns: [id, name, email, phone]
    row_count: 45230
    filter_applied: "status = 'active'"
  target:
    connector: airbyte/destination-postgres
    tier: staging
    table: customers
    masking_applied: true
  transformation:
    type: mask
    strategy_map:
      name: tokenize
      email: format_preserve_encrypt
      phone: format_preserve_encrypt
    referential_integrity: verified
  quality:
    assertions_run: 4
    assertions_passed: 4
  content_hash: "sha256:a1b2c3d4e5f6"
""")

CANONICAL_STATE = yaml.safe_load("""
data_pipelines:
  - id: pipe-001
    definition: pipeline/customer-data.pipeline.yaml
    contract: contracts/customer-data.contract.yaml
    status: executed
    last_run: "2026-03-18T14:32:00Z"
    targets_ready:
      - staging
      - development
    quality_gate: passed
""")


# ===================================================================
# PIPELINE SCHEMA TESTS
# ===================================================================

class TestPipelineSchema:
    """Tests for pipeline.schema.json"""

    def test_canonical_passes(self):
        _validate(CANONICAL_PIPELINE, PIPELINE_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["metadata", "source", "targets"],
        ids=["missing-metadata", "missing-source", "missing-targets"],
    )
    def test_missing_required_top_level_field(self, field):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        del doc[field]
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_wrong_api_version(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["apiVersion"] = "conductor-data/v99"
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_wrong_kind(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["kind"] = "DataContract"
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_invalid_extraction_mode(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["source"]["extraction"]["mode"] = "streaming"
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_invalid_on_failure_enum(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["quality"]["on_failure"] = "ignore"
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_missing_table_name(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["source"]["extraction"]["tables"] = [{"columns": ["id"]}]
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_empty_tables_array(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["source"]["extraction"]["tables"] = []
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_placeholder_strings_pass(self):
        """${VARIABLE} placeholders must be accepted as strings."""
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["source"]["connection"]["host"] = "${MY_CUSTOM_HOST}"
        doc["source"]["connection"]["database"] = "${MY_DB}"
        _validate(doc, PIPELINE_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["transform", "lineage", "quality"],
        ids=["no-transform", "no-lineage", "no-quality"],
    )
    def test_optional_section_omitted(self, field):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        del doc[field]
        _validate(doc, PIPELINE_SCHEMA)

    def test_optional_brd_refs_omitted(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        del doc["metadata"]["brd_refs"]
        _validate(doc, PIPELINE_SCHEMA)

    def test_empty_brd_refs_array(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["metadata"]["brd_refs"] = []
        _validate(doc, PIPELINE_SCHEMA)

    def test_empty_assertions_array(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["quality"]["assertions"] = []
        _validate(doc, PIPELINE_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["id", "name", "created_by"],
        ids=["missing-id", "missing-name", "missing-created_by"],
    )
    def test_metadata_missing_required_field(self, field):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        del doc["metadata"][field]
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_target_missing_masking(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        del doc["targets"][0]["masking"]
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_additional_top_level_property_rejected(self):
        doc = copy.deepcopy(CANONICAL_PIPELINE)
        doc["extra_field"] = "should fail"
        _assert_invalid(doc, PIPELINE_SCHEMA)

    def test_minimal_pipeline(self):
        """Minimal valid pipeline: no optional sections."""
        doc = {
            "apiVersion": "conductor-data/v1",
            "kind": "Pipeline",
            "metadata": {
                "id": "p1",
                "name": "test",
                "created_by": "agent_001"
            },
            "source": {
                "connector": "airbyte/source-mysql",
                "connection": {"host": "localhost"},
                "extraction": {
                    "mode": "full",
                    "tables": [{"name": "users"}]
                }
            },
            "targets": [
                {
                    "tier": "dev",
                    "connector": "airbyte/destination-postgres",
                    "connection": {"host": "localhost"},
                    "masking": "none"
                }
            ]
        }
        _validate(doc, PIPELINE_SCHEMA)


# ===================================================================
# CONTRACT SCHEMA TESTS
# ===================================================================

class TestContractSchema:
    """Tests for contract.schema.json"""

    def test_canonical_passes(self):
        _validate(CANONICAL_CONTRACT, CONTRACT_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["metadata", "columns", "governance", "quality_signoff"],
        ids=["missing-metadata", "missing-columns", "missing-governance", "missing-quality_signoff"],
    )
    def test_missing_required_top_level_field(self, field):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        del doc[field]
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_wrong_kind(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        doc["kind"] = "Pipeline"
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_invalid_classification_enum(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        doc["columns"]["customers.id"]["classification"] = "secret"
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_invalid_pii_type_enum(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        doc["columns"]["customers.name"]["pii_type"] = "FINGERPRINT"
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_invalid_audit_frequency(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        doc["governance"]["audit_frequency"] = "yearly"
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_retention_days_not_integer(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        doc["governance"]["retention_days"] = "ninety"
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_classification_version_not_integer(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        doc["metadata"]["classification_version"] = "1"
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_pii_type_optional(self):
        """pii_type is optional even when pii is true."""
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        for col in doc["columns"].values():
            if "pii_type" in col:
                del col["pii_type"]
        _validate(doc, CONTRACT_SCHEMA)

    def test_pii_boolean_required(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        del doc["columns"]["customers.id"]["pii"]
        _assert_invalid(doc, CONTRACT_SCHEMA)

    def test_empty_columns_rejected(self):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        doc["columns"] = {}
        _assert_invalid(doc, CONTRACT_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["pipeline_ref", "classification_version"],
        ids=["missing-pipeline_ref", "missing-classification_version"],
    )
    def test_metadata_missing_required_field(self, field):
        doc = copy.deepcopy(CANONICAL_CONTRACT)
        del doc["metadata"][field]
        _assert_invalid(doc, CONTRACT_SCHEMA)


# ===================================================================
# MASKING POLICY SCHEMA TESTS
# ===================================================================

class TestMaskingPolicySchema:
    """Tests for masking-policy.schema.json"""

    def test_canonical_passes(self):
        _validate(CANONICAL_MASKING, MASKING_SCHEMA)

    def test_missing_metadata(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        del doc["metadata"]
        _assert_invalid(doc, MASKING_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["name", "tier", "description"],
        ids=["missing-name", "missing-tier", "missing-description"],
    )
    def test_missing_metadata_required_field(self, field):
        doc = copy.deepcopy(CANONICAL_MASKING)
        del doc["metadata"][field]
        _assert_invalid(doc, MASKING_SCHEMA)

    def test_wrong_kind(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["kind"] = "Pipeline"
        _assert_invalid(doc, MASKING_SCHEMA)

    def test_invalid_strategy_enum(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["defaults"]["strategy"] = "encrypt"
        _assert_invalid(doc, MASKING_SCHEMA)

    def test_invalid_classification_in_rule(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["rules"][0]["classification"] = "top_secret"
        _assert_invalid(doc, MASKING_SCHEMA)

    def test_invalid_consistency_scope(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["referential_integrity"]["consistency_scope"] = "global"
        _assert_invalid(doc, MASKING_SCHEMA)

    def test_invalid_entity_in_unstructured(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["unstructured_rules"]["entities"] = ["PERSON", "FINGERPRINT"]
        _assert_invalid(doc, MASKING_SCHEMA)

    def test_placeholder_in_seed(self):
        """${VARIABLE} in seed must pass as string."""
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["defaults"]["seed"] = "${ANOTHER_SEED}"
        _validate(doc, MASKING_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["defaults", "rules", "unstructured_rules", "referential_integrity"],
        ids=["no-defaults", "no-rules", "no-unstructured_rules", "no-referential_integrity"],
    )
    def test_optional_section_omitted(self, field):
        doc = copy.deepcopy(CANONICAL_MASKING)
        del doc[field]
        _validate(doc, MASKING_SCHEMA)

    def test_empty_rules_array(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["rules"] = []
        _validate(doc, MASKING_SCHEMA)

    def test_minimal_policy(self):
        """Minimal valid policy: only required fields."""
        doc = {
            "apiVersion": "conductor-data/v1",
            "kind": "MaskingPolicy",
            "metadata": {
                "name": "dev-policy",
                "tier": "development",
                "description": "Dev masking"
            }
        }
        _validate(doc, MASKING_SCHEMA)

    def test_thresholds_in_unstructured(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["unstructured_rules"]["thresholds"] = {
            "restricted": 0.70,
            "confidential": 0.85,
            "internal": 0.90
        }
        _validate(doc, MASKING_SCHEMA)

    def test_field_rule_missing_pattern(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["rules"] = [
            {
                "classification": "confidential",
                "fields": [
                    {"strategy": "tokenize"}
                ]
            }
        ]
        _assert_invalid(doc, MASKING_SCHEMA)

    def test_field_rule_missing_strategy(self):
        doc = copy.deepcopy(CANONICAL_MASKING)
        doc["rules"] = [
            {
                "classification": "confidential",
                "fields": [
                    {"pattern": "*.email"}
                ]
            }
        ]
        _assert_invalid(doc, MASKING_SCHEMA)


# ===================================================================
# LINEAGE EVENT SCHEMA TESTS
# ===================================================================

class TestLineageEventSchema:
    """Tests for lineage-event.schema.json"""

    def test_canonical_passes(self):
        _validate(CANONICAL_LINEAGE, LINEAGE_SCHEMA)

    def test_missing_event_wrapper(self):
        _assert_invalid(CANONICAL_LINEAGE["event"], LINEAGE_SCHEMA)

    @pytest.mark.parametrize(
        "field",
        ["gov_agent_id", "pipeline_id", "operation", "source", "target", "content_hash"],
        ids=[
            "missing-gov_agent_id", "missing-pipeline_id", "missing-operation",
            "missing-source", "missing-target", "missing-content_hash",
        ],
    )
    def test_missing_required_event_field(self, field):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        del doc["event"][field]
        _assert_invalid(doc, LINEAGE_SCHEMA)

    def test_invalid_operation_enum(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        doc["event"]["operation"] = "delete"
        _assert_invalid(doc, LINEAGE_SCHEMA)

    def test_invalid_gov_classification_enum(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        doc["event"]["gov_classification"] = "secret"
        _assert_invalid(doc, LINEAGE_SCHEMA)

    def test_invalid_content_hash_pattern(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        doc["event"]["content_hash"] = "md5:abc123"
        _assert_invalid(doc, LINEAGE_SCHEMA)

    def test_invalid_content_hash_uppercase(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        doc["event"]["content_hash"] = "sha256:ABCDEF"
        _assert_invalid(doc, LINEAGE_SCHEMA)

    def test_invalid_referential_integrity_enum(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        doc["event"]["transformation"]["referential_integrity"] = "unknown"
        _assert_invalid(doc, LINEAGE_SCHEMA)

    def test_row_count_not_integer(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        doc["event"]["source"]["row_count"] = "45230"
        _assert_invalid(doc, LINEAGE_SCHEMA)

    @pytest.mark.parametrize(
        "path, field",
        [
            (["event"], "transformation"),
            (["event"], "quality"),
            (["event", "source"], "filter_applied"),
        ],
        ids=["no-transformation", "no-quality", "no-filter_applied"],
    )
    def test_optional_field_omitted(self, path, field):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        target = doc
        for key in path:
            target = target[key]
        del target[field]
        _validate(doc, LINEAGE_SCHEMA)

    def test_empty_columns_array(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        doc["event"]["source"]["columns"] = []
        _validate(doc, LINEAGE_SCHEMA)

    def test_source_missing_connector(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        del doc["event"]["source"]["connector"]
        _assert_invalid(doc, LINEAGE_SCHEMA)

    def test_target_missing_tier(self):
        doc = copy.deepcopy(CANONICAL_LINEAGE)
        del doc["event"]["target"]["tier"]
        _assert_invalid(doc, LINEAGE_SCHEMA)


# ===================================================================
# CONDUCTOR STATE DATA SCHEMA TESTS
# ===================================================================

class TestConductorStateDataSchema:
    """Tests for conductor-state-data.schema.json"""

    def test_canonical_passes(self):
        _validate(CANONICAL_STATE, STATE_SCHEMA)

    def test_missing_data_pipelines(self):
        _assert_invalid({}, STATE_SCHEMA)

    @pytest.mark.parametrize(
        "field", ["id", "definition", "contract", "status"],
        ids=["missing-id", "missing-definition", "missing-contract", "missing-status"],
    )
    def test_missing_required_pipeline_field(self, field):
        doc = copy.deepcopy(CANONICAL_STATE)
        del doc["data_pipelines"][0][field]
        _assert_invalid(doc, STATE_SCHEMA)

    def test_invalid_status_enum(self):
        doc = copy.deepcopy(CANONICAL_STATE)
        doc["data_pipelines"][0]["status"] = "running"
        _assert_invalid(doc, STATE_SCHEMA)

    def test_invalid_quality_gate_enum(self):
        doc = copy.deepcopy(CANONICAL_STATE)
        doc["data_pipelines"][0]["quality_gate"] = "skipped"
        _assert_invalid(doc, STATE_SCHEMA)

    def test_targets_ready_not_array(self):
        doc = copy.deepcopy(CANONICAL_STATE)
        doc["data_pipelines"][0]["targets_ready"] = "staging"
        _assert_invalid(doc, STATE_SCHEMA)

    def test_empty_data_pipelines_array(self):
        _validate({"data_pipelines": []}, STATE_SCHEMA)

    def test_empty_targets_ready_array(self):
        doc = copy.deepcopy(CANONICAL_STATE)
        doc["data_pipelines"][0]["targets_ready"] = []
        _validate(doc, STATE_SCHEMA)

    def test_additional_top_level_properties_allowed(self):
        """conductor-state.json has other fields; additionalProperties is true at root."""
        doc = copy.deepcopy(CANONICAL_STATE)
        doc["version"] = "1.0"
        doc["agents"] = []
        _validate(doc, STATE_SCHEMA)

    def test_multiple_pipelines(self):
        doc = copy.deepcopy(CANONICAL_STATE)
        second = copy.deepcopy(doc["data_pipelines"][0])
        second["id"] = "pipe-002"
        second["status"] = "pending"
        second["quality_gate"] = "pending"
        doc["data_pipelines"].append(second)
        _validate(doc, STATE_SCHEMA)

    def test_all_status_values(self):
        """Every valid status enum value should pass."""
        for status in ["pending", "designing", "reviewing", "approved", "executing", "executed", "failed"]:
            doc = copy.deepcopy(CANONICAL_STATE)
            doc["data_pipelines"][0]["status"] = status
            _validate(doc, STATE_SCHEMA)

    def test_all_quality_gate_values(self):
        """Every valid quality_gate enum value should pass."""
        for qg in ["pending", "passed", "failed"]:
            doc = copy.deepcopy(CANONICAL_STATE)
            doc["data_pipelines"][0]["quality_gate"] = qg
            _validate(doc, STATE_SCHEMA)
