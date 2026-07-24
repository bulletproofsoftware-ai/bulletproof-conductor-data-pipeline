"""
Tests for contracts/contract_manager.py -- Contract Lifecycle Manager.

Validates:
- Create contract, hash stored in state
- Update contract increments version
- Old version retrievable after update
- All versions listed for audit
"""

import hashlib
import pytest

from lineage.pg_writer import PgLineageWriter
from contracts.contract_manager import ContractManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RAW_YAML_V1 = """\
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
  steward: nhi_data-steward_alice
  classification_version: 1
columns:
  customers.id:
    classification: internal
    pii: false
  customers.email:
    classification: confidential
    pii: true
    pii_type: EMAIL
"""

RAW_YAML_V2 = """\
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
  steward: nhi_data-steward_alice
  classification_version: 2
columns:
  customers.id:
    classification: internal
    pii: false
  customers.email:
    classification: confidential
    pii: true
    pii_type: EMAIL
  customers.phone:
    classification: confidential
    pii: true
    pii_type: PHONE
"""


COLUMNS_V1 = {
    "customers.id": {"classification": "internal", "pii": False},
    "customers.email": {"classification": "confidential", "pii": True, "pii_type": "EMAIL"},
}

COLUMNS_V2 = {
    "customers.id": {"classification": "internal", "pii": False},
    "customers.email": {"classification": "confidential", "pii": True, "pii_type": "EMAIL"},
    "customers.phone": {"classification": "confidential", "pii": True, "pii_type": "PHONE"},
}


@pytest.fixture
def pg_writer():
    return PgLineageWriter()


@pytest.fixture
def manager(pg_writer):
    return ContractManager(pg_writer=pg_writer)


# ---------------------------------------------------------------------------
# Create Contract Tests
# ---------------------------------------------------------------------------

class TestCreateContract:
    """Creating a contract should store version 1 and register hash in state."""

    def test_create_stores_version_1(self, manager, pg_writer):
        contract = manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        assert contract["metadata"]["classification_version"] == 1
        assert contract["metadata"]["pipeline_ref"] == "pipe-001"
        assert contract["metadata"]["steward"] == "nhi_data-steward_alice"
        assert contract["columns"] == COLUMNS_V1

        # Verify stored in lineage DB
        versions = pg_writer.get_contract_versions("pipe-001")
        assert len(versions) == 1
        assert versions[0].version == 1
        assert versions[0].contract_yaml == RAW_YAML_V1

    def test_create_registers_hash_in_state(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )

        state = manager.state
        entry = state["artifact_hashes"]["contract"]["pipe-001"]
        assert entry["hash"].startswith("sha256:")
        assert entry["version"] == 1

        # Verify hash is correct SHA-256 of raw YAML
        expected = "sha256:" + hashlib.sha256(RAW_YAML_V1.encode("utf-8")).hexdigest()
        assert entry["hash"] == expected

    def test_create_hash_computed_on_raw_content(self, manager):
        """SHA-256 must be computed on the raw YAML string, not parsed."""
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        expected = ContractManager.compute_hash(RAW_YAML_V1)
        actual = manager.state["artifact_hashes"]["contract"]["pipe-001"]["hash"]
        assert actual == expected


# ---------------------------------------------------------------------------
# Update Contract Tests
# ---------------------------------------------------------------------------

class TestUpdateContract:
    """Updating a contract should increment version and preserve old version."""

    def test_update_increments_version(self, manager, pg_writer):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        updated = manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )
        assert updated["metadata"]["classification_version"] == 2

    def test_update_stores_new_version_in_lineage_db(self, manager, pg_writer):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )

        versions = pg_writer.get_contract_versions("pipe-001")
        assert len(versions) == 2
        assert versions[0].version == 1
        assert versions[1].version == 2

    def test_update_without_existing_raises(self, manager):
        with pytest.raises(ValueError, match="No existing contract"):
            manager.update_contract(
                pipeline_ref="pipe-nonexistent",
                changes={"columns": COLUMNS_V2},
                raw_yaml=RAW_YAML_V2,
                steward_id="nhi_data-steward_alice",
            )

    def test_update_hash_changes_in_state(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        hash_v1 = manager.state["artifact_hashes"]["contract"]["pipe-001"]["hash"]

        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )
        hash_v2 = manager.state["artifact_hashes"]["contract"]["pipe-001"]["hash"]

        assert hash_v1 != hash_v2
        assert manager.state["artifact_hashes"]["contract"]["pipe-001"]["version"] == 2


# ---------------------------------------------------------------------------
# Version Retrieval Tests
# ---------------------------------------------------------------------------

class TestVersionRetrieval:
    """Old versions should remain retrievable; all versions listed for audit."""

    def test_old_version_retrievable_after_update(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )

        v1 = manager.get_contract("pipe-001", version=1)
        assert v1 is not None
        assert v1["version"] == 1
        assert v1["contract_yaml"] == RAW_YAML_V1

    def test_get_latest_returns_newest(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )

        latest = manager.get_contract("pipe-001")
        assert latest is not None
        assert latest["version"] == 2

    def test_get_nonexistent_returns_none(self, manager):
        result = manager.get_contract("pipe-nonexistent")
        assert result is None

    def test_get_nonexistent_version_returns_none(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        result = manager.get_contract("pipe-001", version=99)
        assert result is None

    def test_all_versions_listed_for_audit(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )

        all_versions = manager.get_all_versions("pipe-001")
        assert len(all_versions) == 2
        assert all_versions[0]["version"] == 1
        assert all_versions[1]["version"] == 2
        # Both have different hashes
        assert all_versions[0]["contract_hash"] != all_versions[1]["contract_hash"]

    def test_versions_never_deleted(self, manager, pg_writer):
        """Old versions must persist in the lineage DB -- never deleted."""
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )

        # Directly check the PG writer's internal storage
        raw_versions = pg_writer.get_contract_versions("pipe-001")
        assert len(raw_versions) == 2
        # Version 1 still has its original YAML
        assert raw_versions[0].contract_yaml == RAW_YAML_V1
        assert raw_versions[1].contract_yaml == RAW_YAML_V2
