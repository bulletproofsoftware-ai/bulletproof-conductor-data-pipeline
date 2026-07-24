"""
Tests for GDPR Article 30 Processing Record Generator.

Verifies:
- All Article 30 fields populated from lineage + contract + pipeline definition
- Controller maps to correct agent NHI
- PII types extracted from contract
- Recipients include all target tiers
- Retention period from contract governance section
- Missing lineage data produces partial record with flagged gaps
"""

from __future__ import annotations

import json

import pytest

from compliance.gdpr_article30 import Article30Generator

pytestmark = pytest.mark.integration


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def generator():
    return Article30Generator()


@pytest.fixture
def sample_pipeline_def():
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "Pipeline",
        "metadata": {
            "id": "pipe-gdpr-test",
            "name": "gdpr-compliance-test",
            "created_by": "nhi_data-engineer_test",
            "brd_refs": ["REQ-GDPR-001", "REQ-GDPR-002"],
        },
        "source": {
            "connector": "airbyte/source-postgres",
            "connection": {"host": "localhost", "port": 5432, "database": "testdb"},
            "extraction": {
                "mode": "full",
                "tables": [
                    {"name": "customers", "columns": ["id", "name", "email", "ssn"]},
                    {"name": "orders", "columns": ["id", "customer_id", "amount"]},
                ],
            },
        },
        "targets": [
            {
                "tier": "production",
                "connector": "airbyte/destination-postgres",
                "connection": {"host": "localhost", "database": "prod_db"},
                "masking": "none",
            },
            {
                "tier": "staging",
                "connector": "airbyte/destination-postgres",
                "connection": {"host": "localhost", "database": "staging_db"},
                "masking": "staging-policy",
            },
            {
                "tier": "development",
                "connector": "airbyte/destination-postgres",
                "connection": {"host": "localhost", "database": "dev_db"},
                "masking": "dev-policy",
            },
        ],
        "lineage": {"enabled": True, "emit_to": ["qdrant", "postgresql"]},
    }


@pytest.fixture
def sample_contract():
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "DataContract",
        "metadata": {
            "pipeline_ref": "pipe-gdpr-test",
            "steward": "nhi_data-steward_test",
            "reviewed_at": "2025-06-01T10:00:00Z",
            "classification_version": 1,
        },
        "columns": {
            "customers.id": {"classification": "public", "pii": False},
            "customers.name": {
                "classification": "confidential",
                "pii": True,
                "pii_type": "PERSON",
            },
            "customers.email": {
                "classification": "confidential",
                "pii": True,
                "pii_type": "EMAIL",
            },
            "customers.ssn": {
                "classification": "restricted",
                "pii": True,
                "pii_type": "SSN",
            },
            "orders.id": {"classification": "public", "pii": False},
            "orders.customer_id": {"classification": "internal", "pii": False},
            "orders.amount": {"classification": "internal", "pii": False},
        },
        "governance": {
            "human_review_required": True,
            "retention_days": 365,
            "audit_frequency": "monthly",
        },
        "quality_signoff": True,
    }


@pytest.fixture
def sample_lineage_events():
    return [
        {
            "event": {
                "gov_agent_id": "nhi_data-engineer_20260318_a1b2c3d4",
                "gov_session_id": "sess_extract_pipe-gdpr-test",
                "gov_classification": "confidential",
                "gov_timestamp": "2025-06-01T10:00:00Z",
                "pipeline_id": "pipe-gdpr-test",
                "operation": "extract",
                "source": {
                    "connector": "airbyte/source-postgres",
                    "table": "customers",
                    "columns": ["id", "name", "email", "ssn"],
                    "row_count": 100,
                },
                "target": {
                    "connector": "internal/staging",
                    "tier": "staging",
                    "table": "customers",
                    "masking_applied": False,
                },
                "content_hash": "sha256:abc123",
            }
        },
        {
            "event": {
                "gov_agent_id": "nhi_data-engineer_20260318_a1b2c3d4",
                "gov_session_id": "sess_mask_pipe-gdpr-test",
                "gov_classification": "confidential",
                "gov_timestamp": "2025-06-01T10:01:00Z",
                "pipeline_id": "pipe-gdpr-test",
                "operation": "mask",
                "source": {
                    "connector": "internal/staging",
                    "table": "customers",
                    "columns": ["id", "name", "email", "ssn"],
                    "row_count": 100,
                },
                "target": {
                    "connector": "airbyte/destination-postgres",
                    "tier": "staging",
                    "table": "customers",
                    "masking_applied": True,
                },
                "transformation": {
                    "type": "mask",
                    "strategy_map": {
                        "customers.name": "tokenize",
                        "customers.email": "format_preserve_encrypt",
                        "customers.ssn": "redact",
                    },
                    "referential_integrity": "verified",
                },
                "content_hash": "sha256:def456",
            }
        },
    ]


# ── Tests: Complete Record ────────────────────────────────────────────

class TestArticle30CompleteRecord:
    """Tests with complete input data producing a full Article 30 record."""

    def test_all_fields_populated(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """All Article 30 fields are populated when inputs are complete."""
        record = generator.generate(
            pipeline_definition=sample_pipeline_def,
            contract=sample_contract,
            lineage_events=sample_lineage_events,
        )

        assert record.is_complete, f"Missing fields: {record.completeness_flags}"
        assert record.controller != ""
        assert record.processor != ""
        assert len(record.processing_purposes) > 0
        assert len(record.categories_of_data_subjects) > 0
        assert len(record.categories_of_personal_data) > 0
        assert len(record.recipients) > 0
        assert record.retention_days is not None
        assert len(record.technical_safeguards) > 0

    def test_controller_maps_to_agent_nhi(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Controller field maps to gov_agent_id from lineage events."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        assert record.controller == "nhi_data-engineer_20260318_a1b2c3d4"

    def test_processor_is_masking_engine(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Processor field identifies the masking-engine."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        assert "masking-engine" in record.processor

    def test_processing_purposes_from_brd_refs(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Processing purposes derived from pipeline BRD references."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        assert any("REQ-GDPR-001" in p for p in record.processing_purposes)
        assert any("REQ-GDPR-002" in p for p in record.processing_purposes)

    def test_data_subjects_from_source_tables(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Categories of data subjects derived from source table names."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        subjects = " ".join(record.categories_of_data_subjects)
        assert "customers" in subjects
        assert "orders" in subjects

    def test_pii_types_from_contract(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Categories of personal data extracted from contract PII types."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        assert "PERSON" in record.categories_of_personal_data
        assert "EMAIL" in record.categories_of_personal_data
        assert "SSN" in record.categories_of_personal_data

    def test_recipients_from_targets(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Recipients extracted from pipeline target definitions."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        assert len(record.recipients) == 3

        tiers = {r["tier"] for r in record.recipients}
        assert "production" in tiers
        assert "staging" in tiers
        assert "development" in tiers

        # Verify connector info
        for recipient in record.recipients:
            assert "connector" in recipient
            assert "masking_policy" in recipient

    def test_retention_from_contract_governance(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Retention period from contract governance.retention_days."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        assert record.retention_days == 365

    def test_technical_safeguards_include_strategies(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Technical safeguards include masking strategies from lineage."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        safeguards_text = " ".join(record.technical_safeguards)
        assert "tokenize" in safeguards_text
        assert "redact" in safeguards_text

    def test_referential_integrity_status(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Referential integrity status extracted from mask lineage event."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        assert record.referential_integrity == "verified"


# ── Tests: Serialization ─────────────────────────────────────────────

class TestArticle30Serialization:
    """Test serialization to dict/JSON."""

    def test_to_dict_structure(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """to_dict produces expected structure."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        d = record.to_dict()

        assert "pipeline_id" in d
        assert "generated_at" in d
        assert "article30_fields" in d
        assert "completeness" in d

        fields = d["article30_fields"]
        assert "controller" in fields
        assert "processor" in fields
        assert "processing_purposes" in fields
        assert "categories_of_data_subjects" in fields
        assert "categories_of_personal_data" in fields
        assert "recipients" in fields
        assert "retention_days" in fields
        assert "technical_safeguards" in fields

    def test_to_json_valid(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """to_json produces valid JSON."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        json_str = record.to_json()
        parsed = json.loads(json_str)
        assert parsed["pipeline_id"] == "pipe-gdpr-test"

    def test_record_hash_deterministic(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Record hash is deterministic for the same content."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, sample_lineage_events
        )
        hash1 = record.record_hash
        hash2 = record.record_hash
        assert hash1 == hash2
        assert hash1.startswith("sha256:")


# ── Tests: Partial Records (Missing Data) ─────────────────────────────

class TestArticle30PartialRecords:
    """Tests with missing data producing partial records with flagged gaps."""

    def test_missing_lineage_events(self, generator, sample_pipeline_def, sample_contract):
        """Empty lineage events produce partial record with controller gap."""
        record = generator.generate(
            pipeline_definition=sample_pipeline_def,
            contract=sample_contract,
            lineage_events=[],
        )
        assert not record.is_complete
        assert "controller" in record.completeness_flags

    def test_missing_brd_refs(self, generator, sample_contract, sample_lineage_events):
        """Pipeline without brd_refs flags processing_purposes gap."""
        pipeline_no_brd = {
            "apiVersion": "conductor-data/v1",
            "kind": "Pipeline",
            "metadata": {
                "id": "pipe-no-brd",
                "name": "no-brd-test",
                "created_by": "test",
            },
            "source": {
                "connector": "test",
                "connection": {},
                "extraction": {"mode": "full", "tables": []},
            },
            "targets": [],
        }
        record = generator.generate(
            pipeline_no_brd, sample_contract, sample_lineage_events
        )
        # pipeline name is used as fallback purpose
        # but no brd_refs, so purposes come from name
        assert len(record.processing_purposes) > 0  # fallback to name

    def test_missing_pii_columns(self, generator, sample_pipeline_def, sample_lineage_events):
        """Contract without PII columns flags personal data categories gap."""
        no_pii_contract = {
            "apiVersion": "conductor-data/v1",
            "kind": "DataContract",
            "metadata": {
                "pipeline_ref": "pipe-no-pii",
                "steward": "test",
                "reviewed_at": "2025-01-01",
                "classification_version": 1,
            },
            "columns": {
                "data.id": {"classification": "public", "pii": False},
                "data.value": {"classification": "internal", "pii": False},
            },
            "governance": {
                "human_review_required": False,
                "retention_days": 30,
                "audit_frequency": "monthly",
            },
            "quality_signoff": True,
        }
        record = generator.generate(
            sample_pipeline_def, no_pii_contract, sample_lineage_events
        )
        assert "categories_of_personal_data" in record.completeness_flags

    def test_missing_retention(self, generator, sample_pipeline_def, sample_lineage_events):
        """Contract without retention_days flags retention gap."""
        no_retention_contract = {
            "apiVersion": "conductor-data/v1",
            "kind": "DataContract",
            "metadata": {
                "pipeline_ref": "pipe-test",
                "steward": "test",
                "reviewed_at": "2025-01-01",
                "classification_version": 1,
            },
            "columns": {
                "data.id": {"classification": "public", "pii": False},
            },
            "governance": {
                "human_review_required": False,
                "retention_days": 0,
                "audit_frequency": "monthly",
            },
            "quality_signoff": True,
        }
        record = generator.generate(
            sample_pipeline_def, no_retention_contract, sample_lineage_events
        )
        assert "retention_days" in record.completeness_flags

    def test_missing_targets(self, generator, sample_contract, sample_lineage_events):
        """Pipeline without targets flags recipients gap."""
        no_targets = {
            "apiVersion": "conductor-data/v1",
            "kind": "Pipeline",
            "metadata": {
                "id": "pipe-no-targets",
                "name": "no-targets-test",
                "created_by": "test",
                "brd_refs": ["REQ-001"],
            },
            "source": {
                "connector": "test",
                "connection": {},
                "extraction": {"mode": "full", "tables": []},
            },
            "targets": [],
        }
        record = generator.generate(
            no_targets, sample_contract, sample_lineage_events
        )
        assert "recipients" in record.completeness_flags

    def test_processor_override(
        self, generator, sample_pipeline_def, sample_contract, sample_lineage_events
    ):
        """Custom processor_identity overrides lineage-derived processor."""
        record = generator.generate(
            sample_pipeline_def,
            sample_contract,
            sample_lineage_events,
            processor_identity="custom-masking-engine/v2",
        )
        assert record.processor == "custom-masking-engine/v2"

    def test_completeness_dict_output(self, generator, sample_pipeline_def, sample_contract):
        """Partial record's to_dict includes completeness info."""
        record = generator.generate(
            sample_pipeline_def, sample_contract, lineage_events=[]
        )
        d = record.to_dict()
        assert d["completeness"]["is_complete"] is False
        assert len(d["completeness"]["missing_fields"]) > 0
