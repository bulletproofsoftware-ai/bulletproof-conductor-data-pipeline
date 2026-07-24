"""
Artifact Integrity Verification -- SHA-256 hashing for pipelines, contracts, policies.

CISO-HIGH: Artifact integrity verified before every use.

- hash_artifact(yaml_path): compute SHA-256 of YAML file content
- register_hash(artifact_type, artifact_id, hash): store in conductor-state.json
- verify_hash(artifact_type, artifact_id, yaml_path): compare current file hash to stored hash

Artifact types: pipeline, contract, masking_policy
On mismatch: INTEGRITY_VIOLATION error, pipeline blocked, alert emitted.
Hash computed on raw YAML content (not parsed -- catches formatting changes).
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Valid artifact types
VALID_ARTIFACT_TYPES = {"pipeline", "contract", "masking_policy"}

# Error code
INTEGRITY_VIOLATION = "INTEGRITY_VIOLATION"


@dataclass
class IntegrityViolation:
    """Structured integrity violation error."""
    error_code: str = INTEGRITY_VIOLATION
    message: str = ""
    artifact_type: str = ""
    artifact_id: str = ""
    expected_hash: str = ""
    actual_hash: str = ""


@dataclass
class IntegrityResult:
    """Result of an integrity verification."""
    valid: bool
    hash_value: str = ""
    violation: Optional[IntegrityViolation] = None


class ArtifactIntegrity:
    """
    Manages artifact integrity through SHA-256 hashing.
    Hashes are stored in conductor-state.json and verified before use.
    """

    def __init__(self, state: Optional[dict] = None):
        """
        Args:
            state: conductor-state.json dict. If None, a new empty dict is used.
                   Hashes stored under state["artifact_hashes"][artifact_type][artifact_id].
        """
        self._state = state if state is not None else {}
        self._state.setdefault("artifact_hashes", {})

    @property
    def state(self) -> dict:
        """Return the conductor-state dict."""
        return self._state

    @staticmethod
    def hash_content(content: str) -> str:
        """
        Compute SHA-256 hash of raw string content.

        Args:
            content: Raw file content as string.

        Returns:
            Hash string prefixed with 'sha256:'.
        """
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def hash_artifact(self, yaml_path: str) -> str:
        """
        Compute SHA-256 of a YAML file's raw content.

        Args:
            yaml_path: Path to the YAML file.

        Returns:
            Hash string prefixed with 'sha256:'.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.hash_content(content)

    def register_hash(
        self,
        artifact_type: str,
        artifact_id: str,
        hash_value: str,
    ) -> None:
        """
        Register an artifact hash in conductor-state.json.

        Args:
            artifact_type: One of 'pipeline', 'contract', 'masking_policy'.
            artifact_id: Unique identifier for the artifact.
            hash_value: SHA-256 hash (with 'sha256:' prefix).

        Raises:
            ValueError: If artifact_type is not valid.
        """
        if artifact_type not in VALID_ARTIFACT_TYPES:
            raise ValueError(
                f"Invalid artifact_type '{artifact_type}'. "
                f"Must be one of: {VALID_ARTIFACT_TYPES}"
            )

        self._state["artifact_hashes"].setdefault(artifact_type, {})
        now = datetime.now(timezone.utc).isoformat()

        self._state["artifact_hashes"][artifact_type][artifact_id] = {
            "hash": hash_value,
            "registered_at": now,
        }

        logger.info(
            "Registered hash for %s/%s: %s",
            artifact_type,
            artifact_id,
            hash_value[:24],
        )

    def verify_hash(
        self,
        artifact_type: str,
        artifact_id: str,
        content: str,
    ) -> IntegrityResult:
        """
        Verify that the current content hash matches the stored hash.

        Args:
            artifact_type: One of 'pipeline', 'contract', 'masking_policy'.
            artifact_id: Unique identifier for the artifact.
            content: Raw file content as a string.

        Returns:
            IntegrityResult. On mismatch, violation field contains details.

        Raises:
            ValueError: If artifact_type is not valid.
        """
        if artifact_type not in VALID_ARTIFACT_TYPES:
            raise ValueError(
                f"Invalid artifact_type '{artifact_type}'. "
                f"Must be one of: {VALID_ARTIFACT_TYPES}"
            )

        actual_hash = self.hash_content(content)

        # Look up stored hash
        type_hashes = self._state.get("artifact_hashes", {}).get(artifact_type, {})
        entry = type_hashes.get(artifact_id)

        if entry is None:
            violation = IntegrityViolation(
                message=(
                    f"No registered hash found for {artifact_type}/{artifact_id}. "
                    "Cannot verify integrity."
                ),
                artifact_type=artifact_type,
                artifact_id=artifact_id,
                expected_hash="",
                actual_hash=actual_hash,
            )
            logger.error(
                "INTEGRITY_VIOLATION: %s", violation.message,
            )
            return IntegrityResult(valid=False, hash_value=actual_hash, violation=violation)

        expected_hash = entry["hash"]

        if actual_hash != expected_hash:
            violation = IntegrityViolation(
                message=(
                    f"Integrity violation for {artifact_type}/{artifact_id}. "
                    f"Content has been modified since registration."
                ),
                artifact_type=artifact_type,
                artifact_id=artifact_id,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
            )
            logger.error(
                "INTEGRITY_VIOLATION: %s (expected=%s, actual=%s)",
                violation.message,
                expected_hash[:24],
                actual_hash[:24],
            )
            return IntegrityResult(valid=False, hash_value=actual_hash, violation=violation)

        logger.info(
            "Integrity verified for %s/%s: %s",
            artifact_type,
            artifact_id,
            actual_hash[:24],
        )
        return IntegrityResult(valid=True, hash_value=actual_hash)

    def verify_artifact_file(
        self,
        artifact_type: str,
        artifact_id: str,
        yaml_path: str,
    ) -> IntegrityResult:
        """
        Convenience method: read file and verify its hash.

        Args:
            artifact_type: One of 'pipeline', 'contract', 'masking_policy'.
            artifact_id: Unique identifier for the artifact.
            yaml_path: Path to the YAML file.

        Returns:
            IntegrityResult.
        """
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.verify_hash(artifact_type, artifact_id, content)
