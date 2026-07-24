"""
Tests for contracts/artifact_integrity.py -- Artifact Integrity Verification.

Validates:
- Hash computed correctly (SHA-256 of file content)
- Matching hash passes verification
- Modified file fails verification
- Hash registered in conductor-state.json
"""

import hashlib
import os
import tempfile
import pytest

from contracts.artifact_integrity import (
    ArtifactIntegrity,
    INTEGRITY_VIOLATION,
    VALID_ARTIFACT_TYPES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_YAML = """\
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
  steward: nhi_data-steward_alice
columns:
  customers.id:
    classification: internal
    pii: false
"""

MODIFIED_YAML = """\
apiVersion: conductor-data/v1
kind: DataContract
metadata:
  pipeline_ref: pipe-001
  steward: nhi_data-steward_alice
columns:
  customers.id:
    classification: restricted
    pii: true
"""


@pytest.fixture
def integrity():
    return ArtifactIntegrity()


@pytest.fixture
def temp_yaml():
    """Create a temporary YAML file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        f.write(SAMPLE_YAML)
    yield path
    os.unlink(path)


# ---------------------------------------------------------------------------
# Hash Computation Tests
# ---------------------------------------------------------------------------

class TestHashComputation:
    """SHA-256 hash must be correctly computed on raw file content."""

    def test_hash_content_correct(self, integrity):
        result = integrity.hash_content(SAMPLE_YAML)
        expected = "sha256:" + hashlib.sha256(SAMPLE_YAML.encode("utf-8")).hexdigest()
        assert result == expected

    def test_hash_content_prefix(self, integrity):
        result = integrity.hash_content(SAMPLE_YAML)
        assert result.startswith("sha256:")

    def test_hash_artifact_file(self, integrity, temp_yaml):
        result = integrity.hash_artifact(temp_yaml)
        expected = "sha256:" + hashlib.sha256(SAMPLE_YAML.encode("utf-8")).hexdigest()
        assert result == expected

    def test_hash_changes_with_content(self, integrity):
        hash1 = integrity.hash_content(SAMPLE_YAML)
        hash2 = integrity.hash_content(MODIFIED_YAML)
        assert hash1 != hash2

    def test_hash_file_not_found(self, integrity):
        with pytest.raises(FileNotFoundError):
            integrity.hash_artifact("/nonexistent/path/contract.yaml")

    def test_hash_deterministic(self, integrity):
        """Same content always produces the same hash."""
        h1 = integrity.hash_content(SAMPLE_YAML)
        h2 = integrity.hash_content(SAMPLE_YAML)
        assert h1 == h2


# ---------------------------------------------------------------------------
# Hash Registration Tests
# ---------------------------------------------------------------------------

class TestHashRegistration:
    """Hashes must be stored in conductor-state.json."""

    def test_register_stores_in_state(self, integrity):
        h = integrity.hash_content(SAMPLE_YAML)
        integrity.register_hash("contract", "pipe-001", h)

        entry = integrity.state["artifact_hashes"]["contract"]["pipe-001"]
        assert entry["hash"] == h
        assert "registered_at" in entry

    def test_register_all_artifact_types(self, integrity):
        h = integrity.hash_content(SAMPLE_YAML)
        for atype in VALID_ARTIFACT_TYPES:
            integrity.register_hash(atype, "test-id", h)
            assert "test-id" in integrity.state["artifact_hashes"][atype]

    def test_register_invalid_type_raises(self, integrity):
        with pytest.raises(ValueError, match="Invalid artifact_type"):
            integrity.register_hash("invalid_type", "test-id", "sha256:abc")

    def test_register_overwrites_previous(self, integrity):
        h1 = integrity.hash_content(SAMPLE_YAML)
        h2 = integrity.hash_content(MODIFIED_YAML)

        integrity.register_hash("contract", "pipe-001", h1)
        integrity.register_hash("contract", "pipe-001", h2)

        entry = integrity.state["artifact_hashes"]["contract"]["pipe-001"]
        assert entry["hash"] == h2

    def test_shared_state_dict(self):
        """State dict is shared -- changes visible to caller."""
        state = {}
        integrity = ArtifactIntegrity(state=state)
        h = integrity.hash_content(SAMPLE_YAML)
        integrity.register_hash("contract", "pipe-001", h)

        # Caller can see the registered hash
        assert state["artifact_hashes"]["contract"]["pipe-001"]["hash"] == h


# ---------------------------------------------------------------------------
# Hash Verification Tests
# ---------------------------------------------------------------------------

class TestHashVerification:
    """Verification compares current content hash to stored hash."""

    def test_matching_hash_passes(self, integrity):
        h = integrity.hash_content(SAMPLE_YAML)
        integrity.register_hash("contract", "pipe-001", h)

        result = integrity.verify_hash("contract", "pipe-001", SAMPLE_YAML)
        assert result.valid is True
        assert result.violation is None

    def test_modified_content_fails(self, integrity):
        h = integrity.hash_content(SAMPLE_YAML)
        integrity.register_hash("contract", "pipe-001", h)

        result = integrity.verify_hash("contract", "pipe-001", MODIFIED_YAML)
        assert result.valid is False
        assert result.violation is not None
        assert result.violation.error_code == INTEGRITY_VIOLATION

    def test_violation_contains_hashes(self, integrity):
        h = integrity.hash_content(SAMPLE_YAML)
        integrity.register_hash("contract", "pipe-001", h)

        result = integrity.verify_hash("contract", "pipe-001", MODIFIED_YAML)
        assert result.violation.expected_hash == h
        assert result.violation.actual_hash == integrity.hash_content(MODIFIED_YAML)

    def test_no_registered_hash_fails(self, integrity):
        result = integrity.verify_hash("contract", "pipe-nonexistent", SAMPLE_YAML)
        assert result.valid is False
        assert result.violation is not None
        assert "No registered hash" in result.violation.message

    def test_verify_invalid_type_raises(self, integrity):
        with pytest.raises(ValueError, match="Invalid artifact_type"):
            integrity.verify_hash("invalid_type", "test-id", SAMPLE_YAML)

    def test_verify_artifact_file(self, integrity, temp_yaml):
        h = integrity.hash_artifact(temp_yaml)
        integrity.register_hash("contract", "pipe-001", h)

        result = integrity.verify_artifact_file("contract", "pipe-001", temp_yaml)
        assert result.valid is True

    def test_verify_modified_file(self, integrity, temp_yaml):
        h = integrity.hash_artifact(temp_yaml)
        integrity.register_hash("contract", "pipe-001", h)

        # Modify the file
        with open(temp_yaml, "a") as f:
            f.write("\n# tampered\n")

        result = integrity.verify_artifact_file("contract", "pipe-001", temp_yaml)
        assert result.valid is False
        assert result.violation.error_code == INTEGRITY_VIOLATION

    def test_minor_formatting_change_detected(self, integrity):
        """Even whitespace changes should be caught (hash on raw content)."""
        h = integrity.hash_content(SAMPLE_YAML)
        integrity.register_hash("contract", "pipe-001", h)

        # Add trailing whitespace
        modified = SAMPLE_YAML + " "
        result = integrity.verify_hash("contract", "pipe-001", modified)
        assert result.valid is False
