"""Masking key version tracking and rotation management.

Tracks FPE key versions, enforces quarterly rotation schedule,
retains old key versions for one rotation cycle, warns when
rotation is due within 7 days, and records key versions in lineage.

Key versions follow a semantic format: v{major}.{minor} where major
increments on rotation and minor tracks sub-versions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default rotation interval: quarterly (90 days)
DEFAULT_ROTATION_INTERVAL_DAYS = 90

# Warning threshold: 7 days before rotation due
WARNING_THRESHOLD_DAYS = 7

# Retention: 1 rotation cycle (one previous version kept)
RETENTION_CYCLES = 1


class RotationStatus(str, Enum):
    """Status of a key's rotation schedule."""
    CURRENT = "current"            # Key is current, not due for rotation
    WARNING = "warning"            # Rotation due within 7 days
    OVERDUE = "overdue"            # Past rotation date
    ROTATED = "rotated"            # Key has been rotated (no longer active)
    RETAINED = "retained"          # Old version kept for retention period


@dataclass
class KeyVersion:
    """A single key version with its metadata."""
    version_id: str               # e.g., "v1", "v2"
    created_at: float             # Unix timestamp
    rotation_due_at: float        # Unix timestamp when rotation is due
    status: RotationStatus = RotationStatus.CURRENT
    rotated_at: Optional[float] = None  # When this version was rotated out
    retention_expires_at: Optional[float] = None  # When retention period ends
    executions: list[str] = field(default_factory=list)  # pipeline_execution_ids

    @property
    def days_until_rotation(self) -> float:
        """Days until rotation is due. Negative if overdue."""
        remaining = self.rotation_due_at - time.time()
        return remaining / (24 * 60 * 60)

    @property
    def is_rotation_warning(self) -> bool:
        """True if within 7 days of rotation due date."""
        days = self.days_until_rotation
        return 0 < days <= WARNING_THRESHOLD_DAYS

    @property
    def is_overdue(self) -> bool:
        """True if past rotation due date."""
        return self.days_until_rotation < 0

    @property
    def is_retained(self) -> bool:
        """True if this version is in its retention window."""
        if self.retention_expires_at is None:
            return False
        return time.time() < self.retention_expires_at

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "version_id": self.version_id,
            "created_at": self.created_at,
            "rotation_due_at": self.rotation_due_at,
            "status": self.status.value,
            "days_until_rotation": round(self.days_until_rotation, 1),
            "executions_count": len(self.executions),
        }
        if self.rotated_at is not None:
            result["rotated_at"] = self.rotated_at
        if self.retention_expires_at is not None:
            result["retention_expires_at"] = self.retention_expires_at
        return result

    def to_lineage_record(self) -> dict[str, Any]:
        """Format for inclusion in lineage events."""
        return {
            "key_version": self.version_id,
            "created_at": self.created_at,
            "status": self.status.value,
            "days_until_rotation": round(self.days_until_rotation, 1),
        }


@dataclass
class RotationWarning:
    """Warning emitted when a key is near or past its rotation date."""
    version_id: str
    status: RotationStatus
    days_remaining: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "status": self.status.value,
            "days_remaining": round(self.days_remaining, 1),
            "message": self.message,
        }


class KeyRotationTracker:
    """Tracks FPE key versions and enforces rotation schedules.

    Manages a version chain where:
    - Only one version is CURRENT at a time
    - Old versions are RETAINED for one rotation cycle
    - Versions past retention are ROTATED (no longer accessible)
    - Warnings emitted when rotation is due within 7 days
    """

    def __init__(
        self,
        rotation_interval_days: int = DEFAULT_ROTATION_INTERVAL_DAYS,
        warning_threshold_days: int = WARNING_THRESHOLD_DAYS,
    ):
        """Initialize the key rotation tracker.

        Args:
            rotation_interval_days: Days between rotations (default 90).
            warning_threshold_days: Days before rotation to emit warnings.
        """
        self._rotation_interval_days = rotation_interval_days
        self._warning_threshold_days = warning_threshold_days
        self._versions: dict[str, KeyVersion] = {}
        self._current_version_id: Optional[str] = None
        self._version_counter = 0

    @property
    def current_version(self) -> Optional[KeyVersion]:
        """Get the current active key version."""
        if self._current_version_id is None:
            return None
        return self._versions.get(self._current_version_id)

    @property
    def all_versions(self) -> list[KeyVersion]:
        """Get all tracked key versions, ordered by creation time."""
        return sorted(self._versions.values(), key=lambda v: v.created_at)

    @property
    def accessible_versions(self) -> list[KeyVersion]:
        """Get all versions that are still accessible (current + retained)."""
        return [
            v for v in self._versions.values()
            if v.status in (RotationStatus.CURRENT, RotationStatus.RETAINED)
            or (v.status == RotationStatus.RETAINED and v.is_retained)
        ]

    def initialize_key(
        self,
        version_id: Optional[str] = None,
        created_at: Optional[float] = None,
    ) -> KeyVersion:
        """Initialize the first key version or add a new one.

        Args:
            version_id: Optional explicit version ID. Auto-generated if None.
            created_at: Optional creation timestamp. Defaults to now.

        Returns:
            The newly created KeyVersion.
        """
        self._version_counter += 1
        if version_id is None:
            version_id = f"v{self._version_counter}"

        now = created_at if created_at is not None else time.time()
        rotation_interval_seconds = self._rotation_interval_days * 24 * 60 * 60

        key = KeyVersion(
            version_id=version_id,
            created_at=now,
            rotation_due_at=now + rotation_interval_seconds,
            status=RotationStatus.CURRENT,
        )

        # If there's already a current version, mark it as retained
        if self._current_version_id is not None:
            self._retire_version(self._current_version_id, now)

        self._versions[version_id] = key
        self._current_version_id = version_id

        logger.info(  # nosemgrep: python-logger-credential-disclosure — logs version ID, not key material
            "Initialized key version %s (rotation due in %d days)",
            version_id,
            self._rotation_interval_days,
        )
        return key

    def rotate(
        self,
        new_version_id: Optional[str] = None,
    ) -> tuple[KeyVersion, Optional[RotationWarning]]:
        """Rotate to a new key version.

        - Current version moves to RETAINED status
        - Old retained versions move to ROTATED status (past retention)
        - New version becomes CURRENT

        Args:
            new_version_id: Optional explicit version ID for the new key.

        Returns:
            Tuple of (new_key_version, optional_warning_about_expired_retention).
        """
        now = time.time()
        _rotation_interval_seconds = self._rotation_interval_days * 24 * 60 * 60
        warning: Optional[RotationWarning] = None

        # Expire any RETAINED versions beyond retention window
        for v in self._versions.values():
            if v.status == RotationStatus.RETAINED:
                if v.retention_expires_at is not None and now > v.retention_expires_at:
                    v.status = RotationStatus.ROTATED
                    logger.info(  # nosemgrep: python-logger-credential-disclosure — logs version ID, not key material
                        "Key version %s expired from retention", v.version_id
                    )

        # Retire the current version
        if self._current_version_id is not None:
            self._retire_version(self._current_version_id, now)

        # Create new version
        new_key = self.initialize_key(version_id=new_version_id, created_at=now)

        return new_key, warning

    def record_execution(
        self,
        pipeline_execution_id: str,
        version_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Record that a pipeline execution used a specific key version.

        Args:
            pipeline_execution_id: The pipeline execution ID.
            version_id: The key version used. Defaults to current.

        Returns:
            Lineage record for the key version usage.
        """
        if version_id is None:
            if self._current_version_id is None:
                raise ValueError("No current key version initialized")
            version_id = self._current_version_id

        key = self._versions.get(version_id)
        if key is None:
            raise ValueError(f"Key version {version_id} not found")

        key.executions.append(pipeline_execution_id)

        lineage_record = key.to_lineage_record()
        lineage_record["pipeline_execution_id"] = pipeline_execution_id

        logger.debug(  # nosemgrep: python-logger-credential-disclosure — logs execution and version IDs, not key material
            "Recorded execution %s using key version %s",
            pipeline_execution_id,
            version_id,
        )
        return lineage_record

    def check_rotation_status(self) -> tuple[RotationStatus, Optional[RotationWarning]]:
        """Check the rotation status of the current key.

        Returns:
            Tuple of (status, optional_warning).
        """
        if self._current_version_id is None:
            return RotationStatus.CURRENT, None

        key = self._versions[self._current_version_id]
        days_remaining = key.days_until_rotation

        if days_remaining < 0:
            key.status = RotationStatus.OVERDUE
            warning = RotationWarning(
                version_id=key.version_id,
                status=RotationStatus.OVERDUE,
                days_remaining=days_remaining,
                message=(
                    f"Key version {key.version_id} is OVERDUE for rotation "
                    f"by {abs(days_remaining):.1f} days. Immediate rotation required."
                ),
            )
            logger.warning(warning.message)  # nosemgrep: python-logger-credential-disclosure — logs version ID and days, not key material
            return RotationStatus.OVERDUE, warning

        if days_remaining <= self._warning_threshold_days:
            key.status = RotationStatus.WARNING
            warning = RotationWarning(
                version_id=key.version_id,
                status=RotationStatus.WARNING,
                days_remaining=days_remaining,
                message=(
                    f"Key version {key.version_id} rotation due in "
                    f"{days_remaining:.1f} days. Schedule rotation soon."
                ),
            )
            logger.warning(warning.message)  # nosemgrep: python-logger-credential-disclosure — logs version ID and days, not key material
            return RotationStatus.WARNING, warning

        return RotationStatus.CURRENT, None

    def get_version(self, version_id: str) -> Optional[KeyVersion]:
        """Get a specific key version by ID."""
        return self._versions.get(version_id)

    def is_version_accessible(self, version_id: str) -> bool:
        """Check if a key version is still accessible (current or retained).

        Args:
            version_id: The version to check.

        Returns:
            True if the version can still be used for decryption.
        """
        key = self._versions.get(version_id)
        if key is None:
            return False
        if key.status == RotationStatus.CURRENT:
            return True
        if key.status == RotationStatus.RETAINED:
            if key.retention_expires_at is not None:
                return time.time() < key.retention_expires_at
            return True
        return False

    def detect_version_mismatch(
        self,
        execution_version: str,
    ) -> Optional[str]:
        """Detect if an execution used a different key version than current.

        Args:
            execution_version: The key version from a previous execution.

        Returns:
            Warning message if mismatch detected, None otherwise.
        """
        if self._current_version_id is None:
            return None
        if execution_version != self._current_version_id:
            return (
                f"Key version mismatch: execution used {execution_version}, "
                f"current is {self._current_version_id}. "
                f"Data may need re-masking with current key."
            )
        return None

    def _retire_version(self, version_id: str, now: float) -> None:
        """Move a version from CURRENT to RETAINED status."""
        key = self._versions.get(version_id)
        if key is None:
            return

        rotation_interval_seconds = self._rotation_interval_days * 24 * 60 * 60
        key.status = RotationStatus.RETAINED
        key.rotated_at = now
        key.retention_expires_at = now + (rotation_interval_seconds * RETENTION_CYCLES)

        logger.info(  # nosemgrep: python-logger-credential-disclosure — logs version ID, not key material
            "Key version %s retired to RETAINED (retention expires in %d days)",
            version_id,
            self._rotation_interval_days * RETENTION_CYCLES,
        )
