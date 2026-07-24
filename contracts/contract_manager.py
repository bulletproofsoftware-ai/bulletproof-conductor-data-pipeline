"""
Contract Lifecycle Manager -- create, update, version, retrieve data contracts.

REQ-DP-034: Data contract versioning with lineage retention of all versions.

Version increment triggers:
- Column added or removed from contract
- Column classification changed
- PII tagging changed

Old versions are NEVER deleted -- required for audit trail. All historical
versions are stored in the lineage DB via PgLineageWriter.store_contract_version.

SHA-256 hash is computed on raw YAML content (not parsed).
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from lineage.pg_writer import PgLineageWriter

logger = logging.getLogger(__name__)


class ContractManager:
    """
    Manages the lifecycle of data contracts: creation, updates with
    automatic version incrementing, retrieval of current or historical
    versions, and hash computation for integrity tracking.
    """

    def __init__(
        self,
        pg_writer: PgLineageWriter,
        state: Optional[dict] = None,
    ):
        """
        Initialize the contract manager.

        Args:
            pg_writer: PostgreSQL lineage writer for storing contract versions.
            state: conductor-state.json dict. If None, a new empty dict is used.
                   Hashes are stored under state["artifact_hashes"]["contract"][pipeline_ref].
        """
        self._pg = pg_writer
        self._state = state if state is not None else {}
        # Ensure nested structure exists
        self._state.setdefault("artifact_hashes", {})
        self._state["artifact_hashes"].setdefault("contract", {})

    @property
    def state(self) -> dict:
        """Return the conductor-state dict (for inspection and testing)."""
        return self._state

    @staticmethod
    def compute_hash(raw_content: str) -> str:
        """
        Compute SHA-256 hash of raw content (YAML string, not parsed).

        Args:
            raw_content: The raw file content as a string.

        Returns:
            Hex digest string prefixed with 'sha256:'.
        """
        digest = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def create_contract(
        self,
        pipeline_ref: str,
        steward_id: str,
        columns: dict[str, dict],
        raw_yaml: str,
        governance: Optional[dict] = None,
    ) -> dict:
        """
        Create a new data contract for a pipeline.

        The contract is stored at version 1 in the lineage DB and its
        SHA-256 hash is registered in conductor-state.json.

        Args:
            pipeline_ref: Pipeline identifier this contract belongs to.
            steward_id: NHI identifier of the data steward who reviewed.
            columns: Column definitions dict {qualified_name: {classification, pii, ...}}.
            raw_yaml: Raw YAML content of the contract file.
            governance: Optional governance block. Defaults to standard values.

        Returns:
            The created contract dict.
        """
        now = datetime.now(timezone.utc).isoformat()
        content_hash = self.compute_hash(raw_yaml)

        contract = {
            "apiVersion": "conductor-data/v1",
            "kind": "DataContract",
            "metadata": {
                "pipeline_ref": pipeline_ref,
                "steward": steward_id,
                "reviewed_at": now,
                "classification_version": 1,
            },
            "columns": columns,
            "governance": governance or {
                "human_review_required": True,
                "retention_days": 90,
                "audit_frequency": "weekly",
            },
            "quality_signoff": True,
        }

        # Store version 1 in lineage DB (immutable)
        self._pg.store_contract_version(
            pipeline_ref=pipeline_ref,
            version=1,
            contract_yaml=raw_yaml,
            contract_hash=content_hash,
        )

        # Register hash in conductor-state.json
        self._state["artifact_hashes"]["contract"][pipeline_ref] = {
            "hash": content_hash,
            "version": 1,
            "updated_at": now,
        }

        logger.info(
            "Created contract for pipeline=%s steward=%s version=1 hash=%s",
            pipeline_ref,
            steward_id,
            content_hash[:24],
        )

        return contract

    def update_contract(
        self,
        pipeline_ref: str,
        changes: dict,
        raw_yaml: str,
        steward_id: Optional[str] = None,
    ) -> dict:
        """
        Update a contract: increment classification_version, recompute hash,
        store old version in lineage DB (never delete).

        Version is incremented when:
        - Column added or removed (changes["columns"] differs)
        - Column classification changed
        - PII tagging changed

        Args:
            pipeline_ref: Pipeline identifier.
            changes: Dict of changes to apply. Supported keys:
                - columns: New column definitions (replaces existing).
                - governance: Updated governance block.
                - steward: New steward NHI (if different reviewer).
            raw_yaml: Raw YAML content of the new contract file.
            steward_id: Optional new steward ID. Uses changes["steward"] if not provided.

        Returns:
            The updated contract dict.

        Raises:
            ValueError: If no previous contract version exists for this pipeline.
        """
        # Get current latest version
        latest = self._pg.get_latest_contract(pipeline_ref)
        if latest is None:
            raise ValueError(
                f"No existing contract for pipeline '{pipeline_ref}'. "
                "Use create_contract() first."
            )

        current_version = latest.version
        new_version = current_version + 1
        now = datetime.now(timezone.utc).isoformat()
        content_hash = self.compute_hash(raw_yaml)

        # Determine steward
        new_steward = steward_id or changes.get("steward", "unknown")

        contract = {
            "apiVersion": "conductor-data/v1",
            "kind": "DataContract",
            "metadata": {
                "pipeline_ref": pipeline_ref,
                "steward": new_steward,
                "reviewed_at": now,
                "classification_version": new_version,
            },
            "columns": changes.get("columns", {}),
            "governance": changes.get("governance", {
                "human_review_required": True,
                "retention_days": 90,
                "audit_frequency": "weekly",
            }),
            "quality_signoff": True,
        }

        # Store new version in lineage DB (old version remains — never deleted)
        self._pg.store_contract_version(
            pipeline_ref=pipeline_ref,
            version=new_version,
            contract_yaml=raw_yaml,
            contract_hash=content_hash,
        )

        # Update hash in conductor-state.json
        self._state["artifact_hashes"]["contract"][pipeline_ref] = {
            "hash": content_hash,
            "version": new_version,
            "updated_at": now,
        }

        logger.info(
            "Updated contract for pipeline=%s version=%d->%d hash=%s",
            pipeline_ref,
            current_version,
            new_version,
            content_hash[:24],
        )

        return contract

    def get_contract(
        self, pipeline_ref: str, version: Optional[int] = None
    ) -> Optional[dict]:
        """
        Retrieve a contract by pipeline_ref. Returns latest version unless
        a specific version is requested.

        Args:
            pipeline_ref: Pipeline identifier.
            version: Specific version number. If None, returns latest.

        Returns:
            Dict with contract version metadata, or None if not found.
        """
        if version is not None:
            # Find specific version
            all_versions = self._pg.get_contract_versions(pipeline_ref)
            for cv in all_versions:
                if cv.version == version:
                    return {
                        "id": cv.id,
                        "pipeline_ref": cv.pipeline_ref,
                        "version": cv.version,
                        "contract_yaml": cv.contract_yaml,
                        "contract_hash": cv.contract_hash,
                        "created_at": cv.created_at,
                    }
            return None

        # Latest version
        latest = self._pg.get_latest_contract(pipeline_ref)
        if latest is None:
            return None

        return {
            "id": latest.id,
            "pipeline_ref": latest.pipeline_ref,
            "version": latest.version,
            "contract_yaml": latest.contract_yaml,
            "contract_hash": latest.contract_hash,
            "created_at": latest.created_at,
        }

    def get_all_versions(self, pipeline_ref: str) -> list[dict]:
        """
        Retrieve all historical versions of a contract for audit purposes.
        Sorted by version number ascending.

        Args:
            pipeline_ref: Pipeline identifier.

        Returns:
            List of contract version dicts, sorted oldest to newest.
        """
        versions = self._pg.get_contract_versions(pipeline_ref)
        return [
            {
                "id": cv.id,
                "pipeline_ref": cv.pipeline_ref,
                "version": cv.version,
                "contract_yaml": cv.contract_yaml,
                "contract_hash": cv.contract_hash,
                "created_at": cv.created_at,
            }
            for cv in versions
        ]
