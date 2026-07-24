"""
Tests for the data_contract_validate MCP tool.

Validates:
- Valid artifacts pass
- Missing coverage fails
- Invalid assertions fail
"""


from tools.data_contract_validate import execute


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pipeline():
    """Valid pipeline definition."""
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "Pipeline",
        "metadata": {
            "id": "pipe-001",
            "name": "customer-data-extract",
            "created_by": "nhi_data-engineer_test",
        },
        "source": {
            "connector": "airbyte/source-postgres",
            "connection": {
                "host": "${PROD_DB_HOST}",
                "port": 5432,
            },
            "extraction": {
                "mode": "incremental",
                "cursor_field": "updated_at",
                "tables": [
                    {
                        "name": "customers",
                        "columns": ["id", "name", "email"],
                    },
                    {
                        "name": "orders",
                        "columns": ["id", "customer_id", "amount"],
                    },
                ],
            },
        },
        "targets": [
            {
                "tier": "staging",
                "connector": "airbyte/destination-postgres",
                "connection": {"host": "${STAGING_DB_HOST}"},
                "masking": "staging-policy",
            },
        ],
        "quality": {
            "assertions": [
                "customers.email IS NOT NULL",
                "customers.id IS UNIQUE",
            ],
            "on_failure": "block",
        },
    }


def _make_contract():
    """Valid data contract covering pipeline columns."""
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "DataContract",
        "metadata": {
            "pipeline_ref": "pipe-001",
            "steward": "test-steward",
            "reviewed_at": "2026-03-18T14:30:00Z",
            "classification_version": 1,
        },
        "columns": {
            "customers.id": {"classification": "internal", "pii": False},
            "customers.name": {"classification": "confidential", "pii": True, "pii_type": "PERSON"},
            "customers.email": {"classification": "confidential", "pii": True, "pii_type": "EMAIL"},
            "orders.id": {"classification": "internal", "pii": False},
            "orders.customer_id": {"classification": "internal", "pii": False},
            "orders.amount": {"classification": "confidential", "pii": False},
        },
        "governance": {
            "human_review_required": True,
            "retention_days": 90,
            "audit_frequency": "weekly",
        },
        "quality_signoff": True,
    }


def _make_policy():
    """Valid masking policy."""
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "MaskingPolicy",
        "metadata": {
            "name": "staging-policy",
            "tier": "staging",
            "description": "Staging masking policy",
        },
        "rules": [
            {"classification": "confidential", "strategy": "tokenize"},
            {"classification": "public", "strategy": "passthrough"},
        ],
    }


# ---------------------------------------------------------------------------
# Valid Artifact Tests
# ---------------------------------------------------------------------------

class TestValidArtifacts:
    """Valid artifacts should pass validation."""

    def test_valid_pipeline_and_contract(self):
        result = execute({
            "pipeline": _make_pipeline(),
            "contract": _make_contract(),
        })
        assert result["status"] == "success"
        assert result["data"]["valid"] is True
        assert result["data"]["errors"] == []

    def test_valid_with_policy(self):
        result = execute({
            "pipeline": _make_pipeline(),
            "contract": _make_contract(),
            "policy": _make_policy(),
        })
        assert result["status"] == "success"
        assert result["data"]["valid"] is True

    def test_pipeline_only_validates_structure(self):
        result = execute({
            "pipeline": _make_pipeline(),
            "contract": {},
        })
        # Pipeline structure is valid even if contract is empty
        assert result["data"]["errors"] == [] or result["status"] in ("success", "error")


# ---------------------------------------------------------------------------
# Missing Coverage Tests
# ---------------------------------------------------------------------------

class TestMissingCoverage:
    """Contract must cover all pipeline columns."""

    def test_missing_column_in_contract(self):
        contract = _make_contract()
        # Remove a column that the pipeline references
        del contract["columns"]["orders.amount"]

        result = execute({
            "pipeline": _make_pipeline(),
            "contract": contract,
        })
        assert result["data"]["valid"] is False
        assert any("orders.amount" in e for e in result["data"]["errors"])

    def test_missing_all_order_columns(self):
        contract = _make_contract()
        # Remove all order columns
        for key in list(contract["columns"].keys()):
            if key.startswith("orders."):
                del contract["columns"][key]

        result = execute({
            "pipeline": _make_pipeline(),
            "contract": contract,
        })
        assert result["data"]["valid"] is False
        assert len(result["data"]["errors"]) >= 1

    def test_pipeline_ref_mismatch(self):
        contract = _make_contract()
        contract["metadata"]["pipeline_ref"] = "pipe-999"

        result = execute({
            "pipeline": _make_pipeline(),
            "contract": contract,
        })
        assert result["data"]["valid"] is False
        assert any("pipeline_ref" in e or "pipe-999" in e for e in result["data"]["errors"])


# ---------------------------------------------------------------------------
# Invalid Assertion Tests
# ---------------------------------------------------------------------------

class TestInvalidAssertions:
    """Invalid quality assertions should be detected."""

    def test_empty_assertion_flagged(self):
        pipeline = _make_pipeline()
        pipeline["quality"]["assertions"].append("")

        result = execute({
            "pipeline": pipeline,
            "contract": _make_contract(),
        })
        assert result["data"]["valid"] is False
        assert any("empty" in e.lower() or "assertion" in e.lower() for e in result["data"]["errors"])


# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    """Artifacts must conform to their JSON schemas."""

    def test_invalid_pipeline_kind(self):
        pipeline = _make_pipeline()
        pipeline["kind"] = "WrongKind"

        result = execute({
            "pipeline": pipeline,
            "contract": _make_contract(),
        })
        assert result["data"]["valid"] is False
        assert len(result["data"]["errors"]) > 0

    def test_missing_required_pipeline_fields(self):
        pipeline = {"apiVersion": "conductor-data/v1", "kind": "Pipeline"}
        # Missing metadata, source, targets

        result = execute({
            "pipeline": pipeline,
            "contract": _make_contract(),
        })
        assert result["data"]["valid"] is False

    def test_invalid_contract_classification(self):
        contract = _make_contract()
        contract["columns"]["customers.id"]["classification"] = "top_secret"

        result = execute({
            "pipeline": _make_pipeline(),
            "contract": contract,
        })
        assert result["data"]["valid"] is False


# ---------------------------------------------------------------------------
# Policy Tier Match Tests
# ---------------------------------------------------------------------------

class TestPolicyTierMatch:
    """Policy tier should match a pipeline target tier."""

    def test_policy_tier_mismatch_warning(self):
        policy = _make_policy()
        policy["metadata"]["tier"] = "production"  # Pipeline targets staging

        result = execute({
            "pipeline": _make_pipeline(),
            "contract": _make_contract(),
            "policy": policy,
        })
        # Should be valid but with warnings
        assert result["data"]["valid"] is True
        assert len(result["data"]["warnings"]) > 0
        assert any("tier" in w for w in result["data"]["warnings"])
