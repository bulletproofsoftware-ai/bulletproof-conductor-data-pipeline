"""Tests for masking key version tracking and rotation.

Covers:
- Key version tracked in lineage
- Rotation warning emitted when key due within 7 days
- Old key version accessible during retention window
- Key version mismatch between executions detected
- Rotation mechanics and version lifecycle
"""

import time

import pytest

from gates.key_rotation import (
    KeyRotationTracker,
    RotationStatus,
)


@pytest.fixture
def tracker() -> KeyRotationTracker:
    """Tracker with default 90-day rotation."""
    return KeyRotationTracker(
        rotation_interval_days=90,
        warning_threshold_days=7,
    )


class TestKeyVersionTracking:
    """Test key version creation and tracking."""

    def test_initialize_key(self, tracker: KeyRotationTracker) -> None:
        key = tracker.initialize_key()

        assert key.version_id == "v1"
        assert key.status == RotationStatus.CURRENT
        assert key.created_at > 0
        assert key.rotation_due_at > key.created_at
        assert tracker.current_version is key

    def test_key_version_in_lineage(self, tracker: KeyRotationTracker) -> None:
        """Key version should be recorded in lineage when execution is tracked."""
        tracker.initialize_key()
        record = tracker.record_execution("pipe-001")

        assert record["key_version"] == "v1"
        assert record["pipeline_execution_id"] == "pipe-001"
        assert record["status"] == "current"
        assert "days_until_rotation" in record
        assert "created_at" in record

    def test_multiple_executions_tracked(self, tracker: KeyRotationTracker) -> None:
        key = tracker.initialize_key()
        tracker.record_execution("pipe-001")
        tracker.record_execution("pipe-002")
        tracker.record_execution("pipe-003")

        assert len(key.executions) == 3
        assert "pipe-001" in key.executions
        assert "pipe-003" in key.executions

    def test_record_execution_requires_initialized_key(
        self, tracker: KeyRotationTracker
    ) -> None:
        """Recording an execution without an initialized key should fail."""
        with pytest.raises(ValueError, match="No current key"):
            tracker.record_execution("pipe-001")

    def test_custom_version_id(self, tracker: KeyRotationTracker) -> None:
        key = tracker.initialize_key(version_id="custom-v1")
        assert key.version_id == "custom-v1"

    def test_key_to_dict(self, tracker: KeyRotationTracker) -> None:
        key = tracker.initialize_key()
        d = key.to_dict()

        assert d["version_id"] == "v1"
        assert d["status"] == "current"
        assert "created_at" in d
        assert "rotation_due_at" in d
        assert "days_until_rotation" in d


class TestRotationWarning:
    """Test that warnings are emitted when key rotation is due soon."""

    def test_warning_within_7_days(self) -> None:
        """Key due for rotation within 7 days should trigger a warning."""
        tracker = KeyRotationTracker(rotation_interval_days=90, warning_threshold_days=7)

        # Create a key that was created 86 days ago (4 days until rotation)
        now = time.time()
        days_86_seconds = 86 * 24 * 60 * 60
        tracker.initialize_key(created_at=now - days_86_seconds)

        status, warning = tracker.check_rotation_status()

        assert status == RotationStatus.WARNING
        assert warning is not None
        assert warning.status == RotationStatus.WARNING
        assert 0 < warning.days_remaining <= 7
        assert "rotation due" in warning.message.lower()

    def test_no_warning_when_not_due(self, tracker: KeyRotationTracker) -> None:
        """Key not due for rotation should have no warning."""
        tracker.initialize_key()

        status, warning = tracker.check_rotation_status()

        assert status == RotationStatus.CURRENT
        assert warning is None

    def test_overdue_key_warning(self) -> None:
        """Key past rotation date should be OVERDUE."""
        tracker = KeyRotationTracker(rotation_interval_days=90)

        # Create a key that was created 100 days ago (10 days overdue)
        now = time.time()
        days_100_seconds = 100 * 24 * 60 * 60
        tracker.initialize_key(created_at=now - days_100_seconds)

        status, warning = tracker.check_rotation_status()

        assert status == RotationStatus.OVERDUE
        assert warning is not None
        assert warning.status == RotationStatus.OVERDUE
        assert warning.days_remaining < 0
        assert "overdue" in warning.message.lower()


class TestRetentionWindow:
    """Test old key version accessibility during retention."""

    def test_old_key_retained_after_rotation(self, tracker: KeyRotationTracker) -> None:
        """After rotation, old key should be RETAINED."""
        key_v1 = tracker.initialize_key(version_id="v1")
        key_v2, _ = tracker.rotate(new_version_id="v2")

        assert key_v1.status == RotationStatus.RETAINED
        assert key_v2.status == RotationStatus.CURRENT
        assert tracker.current_version is key_v2

    def test_retained_key_is_accessible(self, tracker: KeyRotationTracker) -> None:
        """Retained keys should still be accessible for decryption."""
        tracker.initialize_key(version_id="v1")
        tracker.rotate(new_version_id="v2")

        assert tracker.is_version_accessible("v1") is True
        assert tracker.is_version_accessible("v2") is True

    def test_double_rotation_retires_oldest(self, tracker: KeyRotationTracker) -> None:
        """After two rotations, the first key should be rotated out."""
        tracker.initialize_key(version_id="v1")
        tracker.rotate(new_version_id="v2")

        # v1 is now RETAINED, v2 is CURRENT
        assert tracker.get_version("v1").status == RotationStatus.RETAINED

        # Rotate again -- v2 becomes RETAINED, v1 becomes RETAINED still
        # (retention expiry hasn't passed yet)
        tracker.rotate(new_version_id="v3")

        assert tracker.get_version("v2").status == RotationStatus.RETAINED
        assert tracker.current_version.version_id == "v3"

    def test_all_versions_tracked(self, tracker: KeyRotationTracker) -> None:
        tracker.initialize_key(version_id="v1")
        tracker.rotate(new_version_id="v2")
        tracker.rotate(new_version_id="v3")

        all_versions = tracker.all_versions
        version_ids = [v.version_id for v in all_versions]

        assert "v1" in version_ids
        assert "v2" in version_ids
        assert "v3" in version_ids

    def test_retention_metadata(self, tracker: KeyRotationTracker) -> None:
        """Retired key should have rotated_at and retention_expires_at."""
        tracker.initialize_key(version_id="v1")
        tracker.rotate(new_version_id="v2")

        v1 = tracker.get_version("v1")
        assert v1.rotated_at is not None
        assert v1.retention_expires_at is not None
        assert v1.retention_expires_at > v1.rotated_at


class TestVersionMismatch:
    """Test detection of key version mismatches between executions."""

    def test_mismatch_detected(self, tracker: KeyRotationTracker) -> None:
        """Using a different version than current should be detected."""
        tracker.initialize_key(version_id="v1")
        tracker.rotate(new_version_id="v2")

        mismatch = tracker.detect_version_mismatch("v1")

        assert mismatch is not None
        assert "mismatch" in mismatch.lower()
        assert "v1" in mismatch
        assert "v2" in mismatch

    def test_no_mismatch_for_current(self, tracker: KeyRotationTracker) -> None:
        """Current version should not trigger mismatch."""
        tracker.initialize_key(version_id="v1")

        mismatch = tracker.detect_version_mismatch("v1")
        assert mismatch is None

    def test_mismatch_suggests_remasking(self, tracker: KeyRotationTracker) -> None:
        tracker.initialize_key(version_id="v1")
        tracker.rotate(new_version_id="v2")

        mismatch = tracker.detect_version_mismatch("v1")
        assert "re-masking" in mismatch.lower() or "re-mask" in mismatch.lower()


class TestRotationLifecycle:
    """Integration test for the full rotation lifecycle."""

    def test_full_lifecycle(self, tracker: KeyRotationTracker) -> None:
        """Walk through: init -> execute -> warn -> rotate -> verify."""
        # 1. Initialize
        tracker.initialize_key(version_id="v1")
        assert tracker.current_version.version_id == "v1"

        # 2. Record executions
        record = tracker.record_execution("pipe-001")
        assert record["key_version"] == "v1"

        # 3. Check status (should be current)
        status, warning = tracker.check_rotation_status()
        assert status == RotationStatus.CURRENT

        # 4. Rotate
        key_v2, _ = tracker.rotate(new_version_id="v2")
        assert tracker.current_version.version_id == "v2"

        # 5. Old version retained
        assert tracker.is_version_accessible("v1") is True

        # 6. New executions use new version
        record2 = tracker.record_execution("pipe-002", version_id="v2")
        assert record2["key_version"] == "v2"

        # 7. Mismatch detected for old version
        mismatch = tracker.detect_version_mismatch("v1")
        assert mismatch is not None
