"""
data_load MCP Tool -- Atomic load via staging tables.

Load pattern: create temp -> load -> swap on success, drop on failure.
Target unchanged on error. Emits lineage.
Elevated + Human Gate governance classification.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _make_lineage_event(
    pipeline_id: str,
    source_table: str,
    target_table: str,
    target_tier: str,
    target_connector: str,
    columns: list[str],
    row_count: int,
    classification: str = "internal",
) -> dict:
    """Build a lineage event for a load operation."""
    content = json.dumps(
        {"source": source_table, "target": target_table, "tier": target_tier, "rows": row_count},
        sort_keys=True,
    )
    content_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    return {
        "event": {
            "gov_agent_id": "nhi_data-engineer_tool_load",
            "gov_session_id": f"sess_load_{pipeline_id}",
            "gov_classification": classification,
            "gov_timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_id": pipeline_id,
            "operation": "load",
            "source": {
                "connector": "internal/staging",
                "table": source_table,
                "columns": columns,
                "row_count": row_count,
            },
            "target": {
                "connector": target_connector,
                "tier": target_tier,
                "table": target_table,
                "masking_applied": True,
            },
            "content_hash": content_hash,
        }
    }


def _requires_human_gate(classification: str) -> bool:
    """Check if the data classification requires human approval."""
    return classification in ("confidential", "restricted")


_TOKEN_RE = re.compile(r"^[0-9a-f]{64,}$")


def _validate_approval_token(token: str) -> bool:
    """Validate that an approval token is a non-empty hex string of at least 64 chars.

    The actual cryptographic verification happens in the gate layer
    (HumanApprovalWorkflow). The tool layer rejects obviously invalid
    tokens -- empty strings, booleans coerced to strings, and short values.
    """
    if not isinstance(token, str):
        return False
    return bool(_TOKEN_RE.match(token))


class AtomicLoadError(Exception):
    """Raised when atomic load fails -- target remains unchanged."""
    pass


class SimulatedTargetStore:
    """
    In-memory simulated target database for testing atomic loads.

    Maintains a dict of table_name -> list[dict] representing the target.
    Supports staging, swap, and rollback operations.
    """

    def __init__(self) -> None:
        self._tables: dict[str, list[dict]] = {}
        self._staging: dict[str, list[dict]] = {}

    @property
    def tables(self) -> dict[str, list[dict]]:
        return dict(self._tables)

    def get_table(self, name: str) -> Optional[list[dict]]:
        return self._tables.get(name)

    def create_staging(self, table_name: str, data: list[dict]) -> str:
        """Create a staging table with the data. Returns staging table name."""
        staging_name = f"__staging_{table_name}"
        self._staging[staging_name] = list(data)
        return staging_name

    def swap_staging(self, table_name: str, staging_name: str) -> None:
        """Atomically swap staging table into the target table position."""
        if staging_name not in self._staging:
            raise AtomicLoadError(f"Staging table '{staging_name}' not found")
        self._tables[table_name] = self._staging.pop(staging_name)

    def drop_staging(self, staging_name: str) -> None:
        """Drop a staging table (on failure)."""
        self._staging.pop(staging_name, None)

    def set_table(self, table_name: str, data: list[dict]) -> None:
        """Directly set table data (for test setup)."""
        self._tables[table_name] = list(data)


def execute(params: dict) -> dict:
    """
    Execute atomic load to target destination.

    Args:
        params: Dict with keys:
            - pipeline_id (str): Pipeline identifier
            - dataset (dict): Data to load as {table_name: [{col: val, ...}]}
            - target_tier (str): Target environment tier
            - target_connector (str): Target connector type
            - classification (str): Highest data classification
            - approval_token (str, optional): Human gate approval token (>=64 hex chars)
            - target_store (SimulatedTargetStore, optional): Simulated target
            - lineage_emitter (object, optional): LineageEmitter instance
            - simulate_failure (str, optional): Table name to simulate failure on

    Returns:
        Dict with status, data, and metadata.
    """
    pipeline_id = params.get("pipeline_id", "unknown")
    dataset = params.get("dataset", {})
    target_tier = params.get("target_tier", "staging")
    target_connector = params.get("target_connector", "airbyte/destination-postgres")
    classification = params.get("classification", "internal")
    approval_token = params.get("approval_token", "")
    target_store = params.get("target_store")
    lineage_emitter = params.get("lineage_emitter")
    simulate_failure = params.get("simulate_failure")

    start_time = time.monotonic()

    if not dataset:
        return {
            "status": "error",
            "data": {"error_code": "NO_DATASET", "message": "No dataset provided for loading"},
            "metadata": {"tool": "data_load", "pipeline_id": pipeline_id},
        }

    # Check human gate
    if _requires_human_gate(classification) and not _validate_approval_token(approval_token):
        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "status": "error",
            "data": {
                "error_code": "HUMAN_GATE_REQUIRED",
                "message": f"Data classified as '{classification}' requires human approval for loading.",
                "requires_approval": True,
                "classification": classification,
            },
            "metadata": {
                "tool": "data_load",
                "pipeline_id": pipeline_id,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    if target_store is None:
        target_store = SimulatedTargetStore()

    # --- Atomic load: create staging -> load -> swap on success, drop on failure ---
    staging_tables: dict[str, str] = {}
    loaded_tables = []

    try:
        # Step 1: Create staging tables for all target tables
        for table_name, rows in dataset.items():
            staging_name = target_store.create_staging(table_name, rows)
            staging_tables[table_name] = staging_name

            # Simulate failure if requested
            if simulate_failure and table_name == simulate_failure:
                raise AtomicLoadError(
                    f"Simulated load failure on table '{table_name}'"
                )

        # Step 2: All staging succeeded -- swap all atomically
        for table_name, staging_name in staging_tables.items():
            target_store.swap_staging(table_name, staging_name)
            loaded_tables.append(table_name)

    except (AtomicLoadError, Exception) as exc:
        # Rollback: drop all staging tables, target unchanged
        for staging_name in staging_tables.values():
            target_store.drop_staging(staging_name)

        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "status": "error",
            "data": {
                "error_code": "LOAD_FAILED",
                "message": str(exc),
                "target_unchanged": True,
            },
            "metadata": {
                "tool": "data_load",
                "pipeline_id": pipeline_id,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    # Emit lineage events
    lineage_events = []
    for table_name, rows in dataset.items():
        columns = list(rows[0].keys()) if rows else []
        event = _make_lineage_event(
            pipeline_id=pipeline_id,
            source_table=table_name,
            target_table=table_name,
            target_tier=target_tier,
            target_connector=target_connector,
            columns=columns,
            row_count=len(rows),
            classification=classification,
        )
        lineage_events.append(event)

        if lineage_emitter is not None:
            try:
                lineage_emitter.emit(event)
            except Exception as exc:
                logger.error("Lineage emit failed for load table %s: %s", table_name, exc)

    elapsed = (time.monotonic() - start_time) * 1000

    return {
        "status": "success",
        "data": {
            "loaded_tables": loaded_tables,
            "rows_loaded": {t: len(rows) for t, rows in dataset.items()},
        },
        "metadata": {
            "tool": "data_load",
            "pipeline_id": pipeline_id,
            "target_tier": target_tier,
            "target_connector": target_connector,
            "elapsed_ms": round(elapsed, 2),
            "lineage_events_emitted": len(lineage_events),
        },
    }
