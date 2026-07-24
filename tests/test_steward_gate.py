"""
Tests for contracts/steward_gate.py -- Steward Review Enforcement.

Validates:
- Pipeline with valid contract passes
- Pipeline without contract blocked
- Pipeline with stale contract (>30 days) blocked
- Pipeline with invalid steward NHI blocked
- Pipeline not in state blocked
- Tampered contract hash blocked
"""

import hashlib
from datetime import datetime, timezone, timedelta

from contracts.steward_gate import (
    StewardGate,
    CHECK_PIPELINE_EXISTS,
    CHECK_CONTRACT_EXISTS,
    CHECK_STEWARD_VALID,
    CHECK_NOT_STALE,
    CHECK_INTEGRITY,
    STEWARD_NHI_PREFIX,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RAW_YAML = """\
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
  steward: nhi_data-steward_alice
"""


def _make_contract(reviewed_at=None, steward=None):
    """Build a valid contract dict."""
    now = reviewed_at or datetime.now(timezone.utc).isoformat()
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "DataContract",
        "metadata": {
            "pipeline_ref": "pipe-001",
            "steward": steward if steward is not None else "nhi_data-steward_alice",
            "reviewed_at": now,
            "classification_version": 1,
        },
        "columns": {
            "customers.id": {"classification": "internal", "pii": False},
        },
        "governance": {
            "human_review_required": True,
            "retention_days": 90,
            "audit_frequency": "weekly",
        },
        "quality_signoff": True,
    }


def _make_state(pipeline_id="pipe-001", contract=None, contract_hash=None):
    """Build a conductor-state.json dict with a pipeline entry."""
    state = {
        "pipelines": {
            pipeline_id: {
                "status": "active",
                "contract": contract,
            },
        },
        "artifact_hashes": {
            "contract": {},
        },
    }
    if contract_hash:
        state["artifact_hashes"]["contract"][pipeline_id] = {
            "hash": contract_hash,
        }
    return state


# ---------------------------------------------------------------------------
# Valid Pipeline Tests
# ---------------------------------------------------------------------------

class TestValidPipeline:
    """Pipeline with a valid, fresh, signed contract should pass."""

    def test_valid_contract_passes(self):
        contract = _make_contract()
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is True
        assert result.rejection is None

    def test_valid_with_integrity_check(self):
        contract = _make_contract()
        content_hash = "sha256:" + hashlib.sha256(RAW_YAML.encode("utf-8")).hexdigest()
        state = _make_state(contract=contract, contract_hash=content_hash)
        gate = StewardGate(state=state)

        result = gate.check(
            "pipe-001",
            contract=contract,
            contract_raw_yaml=RAW_YAML,
        )
        assert result.allowed is True

    def test_blocked_property(self):
        contract = _make_contract()
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.blocked is False


# ---------------------------------------------------------------------------
# Pipeline Not Found Tests
# ---------------------------------------------------------------------------

class TestPipelineNotFound:
    """Pipeline not in conductor-state.json should be blocked."""

    def test_missing_pipeline_blocked(self):
        state = _make_state()
        gate = StewardGate(state=state)

        result = gate.check("pipe-nonexistent")
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_PIPELINE_EXISTS
        assert "pipe-nonexistent" in result.rejection.message

    def test_empty_state_blocked(self):
        gate = StewardGate(state={})
        result = gate.check("pipe-001")
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_PIPELINE_EXISTS


# ---------------------------------------------------------------------------
# No Contract Tests
# ---------------------------------------------------------------------------

class TestNoContract:
    """Pipeline without a contract should be blocked."""

    def test_no_contract_blocked(self):
        state = _make_state(contract=None)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001")
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_CONTRACT_EXISTS

    def test_empty_contract_blocked(self):
        state = _make_state(contract={})
        gate = StewardGate(state=state)

        result = gate.check("pipe-001")
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_CONTRACT_EXISTS


# ---------------------------------------------------------------------------
# Invalid Steward NHI Tests
# ---------------------------------------------------------------------------

class TestInvalidSteward:
    """Invalid steward NHI should be blocked."""

    def test_wrong_prefix_blocked(self):
        contract = _make_contract(steward="nhi_data-engineer_bob")
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_STEWARD_VALID
        assert STEWARD_NHI_PREFIX in result.rejection.message

    def test_empty_steward_blocked(self):
        contract = _make_contract(steward="")
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_STEWARD_VALID

    def test_random_string_blocked(self):
        contract = _make_contract(steward="alice@example.com")
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_STEWARD_VALID


# ---------------------------------------------------------------------------
# Stale Contract Tests
# ---------------------------------------------------------------------------

class TestStaleContract:
    """Contract reviewed more than 30 days ago should be blocked."""

    def test_stale_contract_blocked(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        contract = _make_contract(reviewed_at=old_time)
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_NOT_STALE
        assert "stale" in result.rejection.message.lower()

    def test_fresh_contract_passes(self):
        contract = _make_contract()  # reviewed_at is now
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is True

    def test_custom_stale_days(self):
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        contract = _make_contract(reviewed_at=old_time)
        state = _make_state(contract=contract)
        gate = StewardGate(state=state, stale_days=7)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_NOT_STALE

    def test_exactly_at_threshold_passes(self):
        """Contract exactly 30 days old should pass."""
        now = datetime.now(timezone.utc)
        boundary = (now - timedelta(days=30)).isoformat()
        contract = _make_contract(reviewed_at=boundary)
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract, reference_time=now)
        # 30 days is NOT > 30 days
        assert result.allowed is True

    def test_missing_reviewed_at_blocked(self):
        contract = _make_contract()
        del contract["metadata"]["reviewed_at"]
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_NOT_STALE


# ---------------------------------------------------------------------------
# Integrity Check Tests
# ---------------------------------------------------------------------------

class TestIntegrityCheck:
    """Tampered contract hash should be blocked."""

    def test_tampered_hash_blocked(self):
        contract = _make_contract()
        stored_hash = "sha256:" + hashlib.sha256(RAW_YAML.encode("utf-8")).hexdigest()
        state = _make_state(contract=contract, contract_hash=stored_hash)
        gate = StewardGate(state=state)

        tampered_yaml = RAW_YAML + "\n# sneaky modification"
        result = gate.check(
            "pipe-001",
            contract=contract,
            contract_raw_yaml=tampered_yaml,
        )
        assert result.allowed is False
        assert result.rejection.failed_check == CHECK_INTEGRITY

    def test_valid_hash_passes(self):
        contract = _make_contract()
        stored_hash = "sha256:" + hashlib.sha256(RAW_YAML.encode("utf-8")).hexdigest()
        state = _make_state(contract=contract, contract_hash=stored_hash)
        gate = StewardGate(state=state)

        result = gate.check(
            "pipe-001",
            contract=contract,
            contract_raw_yaml=RAW_YAML,
        )
        assert result.allowed is True

    def test_no_yaml_skips_integrity(self):
        """If no raw YAML is provided, integrity check is skipped."""
        contract = _make_contract()
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)

        result = gate.check("pipe-001", contract=contract, contract_raw_yaml=None)
        assert result.allowed is True

    def test_no_stored_hash_skips_integrity(self):
        """If no hash is stored, integrity check is skipped (no comparison)."""
        contract = _make_contract()
        state = _make_state(contract=contract, contract_hash=None)
        gate = StewardGate(state=state)

        result = gate.check(
            "pipe-001",
            contract=contract,
            contract_raw_yaml=RAW_YAML,
        )
        assert result.allowed is True


# ---------------------------------------------------------------------------
# No Bypass Tests
# ---------------------------------------------------------------------------

class TestNoBypas:
    """Steward review has NO bypass mechanism."""

    def test_no_bypass_without_contract(self):
        """Even with a 'bypass' flag, no contract means blocked."""
        state = _make_state(contract=None)
        # There is no bypass parameter -- the gate always checks
        gate = StewardGate(state=state)
        result = gate.check("pipe-001")
        assert result.allowed is False

    def test_no_bypass_with_invalid_steward(self):
        """There is no override for invalid steward."""
        contract = _make_contract(steward="admin")
        state = _make_state(contract=contract)
        gate = StewardGate(state=state)
        result = gate.check("pipe-001", contract=contract)
        assert result.allowed is False

    def test_check_order_pipeline_first(self):
        """Checks run in order: pipeline exists is checked first."""
        gate = StewardGate(state={})
        result = gate.check("pipe-001")
        assert result.rejection.failed_check == CHECK_PIPELINE_EXISTS
