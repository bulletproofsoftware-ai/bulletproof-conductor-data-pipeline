"""
Tests for contracts/contract_validator.py -- Contract Validation Logic.

Validates:
- Valid contract + pipeline passes
- Missing column coverage returns CONTRACT_INCOMPLETE
- No contract returns CONTRACT_REQUIRED
- Tampered hash returns CONTRACT_TAMPERED (INTEGRITY_VIOLATION)
- Stale contract returns CONTRACT_EXPIRED
"""

import hashlib
import pytest
from datetime import datetime, timezone, timedelta

from contracts.contract_validator import (
    ContractValidator,
    CONTRACT_REQUIRED,
    CONTRACT_INCOMPLETE,
    CONTRACT_TAMPERED,
    CONTRACT_EXPIRED,
)


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
            "connection": {"host": "${PROD_DB_HOST}", "port": 5432},
            "extraction": {
                "mode": "incremental",
                "cursor_field": "updated_at",
                "tables": [
                    {"name": "customers", "columns": ["id", "name", "email"]},
                    {"name": "orders", "columns": ["id", "customer_id", "amount"]},
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
            "assertions": ["customers.email IS NOT NULL"],
            "on_failure": "block",
        },
    }


def _make_contract():
    """Valid data contract covering all pipeline columns."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "DataContract",
        "metadata": {
            "pipeline_ref": "pipe-001",
            "steward": "nhi_data-steward_alice",
            "reviewed_at": now,
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


RAW_YAML = """\
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
"""


@pytest.fixture
def validator():
    return ContractValidator(stale_days=30)


# ---------------------------------------------------------------------------
# Valid Contract Tests
# ---------------------------------------------------------------------------

class TestValidContract:
    """Valid contract + pipeline should pass all checks."""

    def test_valid_contract_passes_pipeline_check(self, validator):
        result = validator.validate_against_pipeline(
            contract=_make_contract(),
            pipeline=_make_pipeline(),
        )
        assert result.valid is True
        assert result.errors == []

    def test_valid_contract_passes_schema_check(self, validator):
        contract = _make_contract()
        source_schema = {
            "customers.id": {"type": "INTEGER"},
            "customers.name": {"type": "VARCHAR"},
            "customers.email": {"type": "VARCHAR"},
            "orders.id": {"type": "INTEGER"},
            "orders.customer_id": {"type": "INTEGER"},
            "orders.amount": {"type": "DECIMAL"},
        }
        result = validator.validate_against_schema(contract, source_schema)
        assert result.valid is True

    def test_valid_integrity_check(self, validator):
        expected_hash = "sha256:" + hashlib.sha256(RAW_YAML.encode("utf-8")).hexdigest()
        result = validator.validate_integrity(RAW_YAML, expected_hash)
        assert result.valid is True

    def test_valid_freshness_check(self, validator):
        contract = _make_contract()  # reviewed_at is now
        result = validator.validate_freshness(contract)
        assert result.valid is True


# ---------------------------------------------------------------------------
# CONTRACT_REQUIRED Tests
# ---------------------------------------------------------------------------

class TestContractRequired:
    """Missing contract returns CONTRACT_REQUIRED."""

    def test_none_contract_returns_required(self, validator):
        result = validator.validate_against_pipeline(
            contract=None,
            pipeline=_make_pipeline(),
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == CONTRACT_REQUIRED


# ---------------------------------------------------------------------------
# CONTRACT_INCOMPLETE Tests
# ---------------------------------------------------------------------------

class TestContractIncomplete:
    """Contract missing columns returns CONTRACT_INCOMPLETE."""

    def test_missing_column_returns_incomplete(self, validator):
        contract = _make_contract()
        del contract["columns"]["orders.amount"]

        result = validator.validate_against_pipeline(
            contract=contract,
            pipeline=_make_pipeline(),
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == CONTRACT_INCOMPLETE
        assert "orders.amount" in result.errors[0].message

    def test_missing_multiple_columns(self, validator):
        contract = _make_contract()
        del contract["columns"]["orders.amount"]
        del contract["columns"]["customers.email"]

        result = validator.validate_against_pipeline(
            contract=contract,
            pipeline=_make_pipeline(),
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == CONTRACT_INCOMPLETE
        assert "2" in result.errors[0].message  # "2 pipeline column(s)"

    def test_schema_missing_column(self, validator):
        contract = _make_contract()
        source_schema = {
            "customers.id": {"type": "INTEGER"},
            # Missing customers.name, customers.email, etc.
        }
        result = validator.validate_against_schema(contract, source_schema)
        assert result.valid is False
        assert any(e.error_code == CONTRACT_INCOMPLETE for e in result.errors)


# ---------------------------------------------------------------------------
# CONTRACT_TAMPERED Tests
# ---------------------------------------------------------------------------

class TestContractTampered:
    """Hash mismatch returns CONTRACT_TAMPERED."""

    def test_tampered_hash_returns_violation(self, validator):
        result = validator.validate_integrity(
            contract_raw_yaml=RAW_YAML,
            expected_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000",
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == CONTRACT_TAMPERED

    def test_modified_content_fails(self, validator):
        expected_hash = "sha256:" + hashlib.sha256(RAW_YAML.encode("utf-8")).hexdigest()
        modified_yaml = RAW_YAML + "\n# sneaky modification"
        result = validator.validate_integrity(modified_yaml, expected_hash)
        assert result.valid is False
        assert result.errors[0].error_code == CONTRACT_TAMPERED

    def test_hash_without_prefix_still_works(self, validator):
        """Expected hash without 'sha256:' prefix should still match."""
        raw_digest = hashlib.sha256(RAW_YAML.encode("utf-8")).hexdigest()
        result = validator.validate_integrity(RAW_YAML, raw_digest)
        assert result.valid is True


# ---------------------------------------------------------------------------
# CONTRACT_EXPIRED Tests
# ---------------------------------------------------------------------------

class TestContractExpired:
    """Stale contract (>30 days) returns CONTRACT_EXPIRED."""

    def test_stale_contract_returns_expired(self, validator):
        contract = _make_contract()
        # Set reviewed_at to 60 days ago
        old_time = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        contract["metadata"]["reviewed_at"] = old_time

        result = validator.validate_freshness(contract)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].error_code == CONTRACT_EXPIRED
        assert "60" in result.errors[0].message or "days" in result.errors[0].message

    def test_fresh_contract_passes(self, validator):
        contract = _make_contract()
        # reviewed_at is now (set by _make_contract)
        result = validator.validate_freshness(contract)
        assert result.valid is True

    def test_exactly_at_threshold(self, validator):
        """Contract exactly at 30-day boundary should still pass."""
        contract = _make_contract()
        now = datetime.now(timezone.utc)
        boundary = (now - timedelta(days=30)).isoformat()
        contract["metadata"]["reviewed_at"] = boundary

        result = validator.validate_freshness(contract, reference_time=now)
        # Exactly at boundary: 30 days is NOT > 30 days, so should pass
        assert result.valid is True

    def test_one_day_past_threshold(self, validator):
        """Contract 31 days old should fail."""
        contract = _make_contract()
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=31)).isoformat()
        contract["metadata"]["reviewed_at"] = past

        result = validator.validate_freshness(contract, reference_time=now)
        assert result.valid is False
        assert result.errors[0].error_code == CONTRACT_EXPIRED

    def test_missing_reviewed_at_returns_expired(self, validator):
        contract = _make_contract()
        del contract["metadata"]["reviewed_at"]

        result = validator.validate_freshness(contract)
        assert result.valid is False
        assert result.errors[0].error_code == CONTRACT_EXPIRED

    def test_custom_stale_days(self):
        validator = ContractValidator(stale_days=7)
        contract = _make_contract()
        now = datetime.now(timezone.utc)
        past = (now - timedelta(days=10)).isoformat()
        contract["metadata"]["reviewed_at"] = past

        result = validator.validate_freshness(contract, reference_time=now)
        assert result.valid is False
        assert result.errors[0].error_code == CONTRACT_EXPIRED
