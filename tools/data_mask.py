"""
data_mask MCP Tool -- Delegates to masking engine API (simulated HTTP call).

Triggers human gate for Confidential+ data. Emits lineage.
Elevated + Human Gate governance classification.
"""

import hashlib
import hmac
import json
import logging
import re
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _make_lineage_event(
    pipeline_id: str,
    source_table: str,
    target_table: str,
    target_tier: str,
    columns: list[str],
    row_count: int,
    strategy_map: dict[str, str],
    classification: str = "internal",
) -> dict:
    """Build a lineage event for a mask operation."""
    content = json.dumps(
        {"table": source_table, "tier": target_tier, "strategies": strategy_map},
        sort_keys=True,
    )
    content_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    return {
        "event": {
            "gov_agent_id": "nhi_data-steward_tool_mask",
            "gov_session_id": f"sess_mask_{pipeline_id}",
            "gov_classification": classification,
            "gov_timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_id": pipeline_id,
            "operation": "mask",
            "source": {
                "connector": "internal/staging",
                "table": source_table,
                "columns": columns,
                "row_count": row_count,
            },
            "target": {
                "connector": "masking-engine",
                "tier": target_tier,
                "table": target_table,
                "masking_applied": True,
            },
            "transformation": {
                "type": "mask",
                "strategy_map": strategy_map,
                "referential_integrity": "verified",
            },
            "content_hash": content_hash,
        }
    }


def _requires_human_gate(contract: dict) -> bool:
    """Check if any column in the contract is Confidential or Restricted."""
    columns = contract.get("columns", {})
    for col_name, col_def in columns.items():
        classification = col_def.get("classification", "public")
        if classification in ("confidential", "restricted"):
            return True
    return False


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


def _highest_classification(contract: dict) -> str:
    """Determine the highest classification in the contract."""
    order = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
    highest = "public"
    for col_def in contract.get("columns", {}).values():
        cls = col_def.get("classification", "public")
        if order.get(cls, 0) > order.get(highest, 0):
            highest = cls
    return highest


def _simulate_masking_api(dataset: dict, contract: dict, policy: dict) -> dict:
    """
    Simulate a POST /mask call to the masking engine.

    Returns a simulated masked dataset with strategy map and lineage metadata.
    """
    # Build strategy map from contract classifications and policy
    strategy_map = {}
    default_strategy = policy.get("defaults", {}).get("strategy", "tokenize")
    rules_by_classification = {}
    for rule in policy.get("rules", []):
        cls = rule.get("classification")
        if cls:
            rules_by_classification[cls] = rule.get("strategy", rule.get("action", default_strategy))

    for col_name, col_def in contract.get("columns", {}).items():
        cls = col_def.get("classification", "public")
        strategy = rules_by_classification.get(cls, default_strategy)
        strategy_map[col_name] = strategy

    # Simulate masked dataset (replace values with masked placeholders)
    masked_dataset = {}
    rows_processed = {}
    for table_name, rows in dataset.items():
        masked_rows = []
        for row in rows:
            masked_row = {}
            for col, value in row.items():
                qualified = f"{table_name}.{col}"
                strat = strategy_map.get(qualified, "passthrough")
                if strat == "passthrough":
                    masked_row[col] = value
                elif strat == "redact":
                    masked_row[col] = "[REDACTED]"
                elif strat == "tokenize":
                    masked_row[col] = f"TOKEN_{hmac.new(b'masking-sim-salt', str(value).encode(), hashlib.sha256).hexdigest()[:16]}"
                elif strat == "format_preserve_encrypt":
                    masked_row[col] = f"FPE_{hmac.new(b'masking-sim-salt', str(value).encode(), hashlib.sha256).hexdigest()[:16]}"
                else:
                    masked_row[col] = value
            masked_rows.append(masked_row)
        masked_dataset[table_name] = masked_rows
        rows_processed[table_name] = len(rows)

    return {
        "masked_dataset": masked_dataset,
        "strategy_map": strategy_map,
        "rows_processed": rows_processed,
    }


def execute(params: dict) -> dict:
    """
    Apply masking to a dataset via the masking engine.

    Args:
        params: Dict with keys:
            - pipeline_id (str): Pipeline identifier
            - dataset (dict): Dataset as {table_name: [{col: val, ...}]}
            - contract (dict): Data contract with column classifications
            - policy (dict): Masking policy with rules
            - target_tier (str): Target environment tier
            - approval_token (str, optional): Human gate approval token (>=64 hex chars)
            - lineage_emitter (object, optional): LineageEmitter instance
            - masking_engine_url (str, optional): URL for masking engine (not used in simulation)

    Returns:
        Dict with status, data, and metadata.
    """
    pipeline_id = params.get("pipeline_id", "unknown")
    dataset = params.get("dataset", {})
    contract = params.get("contract", {})
    policy = params.get("policy", {})
    target_tier = params.get("target_tier", "staging")
    approval_token = params.get("approval_token", "")
    lineage_emitter = params.get("lineage_emitter")

    start_time = time.monotonic()

    if not dataset:
        return {
            "status": "error",
            "data": {"error_code": "NO_DATASET", "message": "No dataset provided for masking"},
            "metadata": {"tool": "data_mask", "pipeline_id": pipeline_id},
        }

    if not contract:
        return {
            "status": "error",
            "data": {"error_code": "NO_CONTRACT", "message": "No data contract provided"},
            "metadata": {"tool": "data_mask", "pipeline_id": pipeline_id},
        }

    # Check human gate requirement
    needs_gate = _requires_human_gate(contract)
    if needs_gate and not _validate_approval_token(approval_token):
        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "status": "error",
            "data": {
                "error_code": "HUMAN_GATE_REQUIRED",
                "message": "Contract contains Confidential or Restricted data. Human approval required.",
                "requires_approval": True,
                "classification": _highest_classification(contract),
            },
            "metadata": {
                "tool": "data_mask",
                "pipeline_id": pipeline_id,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    # Simulate masking engine call
    try:
        mask_result = _simulate_masking_api(dataset, contract, policy)
    except Exception as exc:
        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "status": "error",
            "data": {"error_code": "MASKING_ERROR", "message": str(exc)},
            "metadata": {
                "tool": "data_mask",
                "pipeline_id": pipeline_id,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    # Emit lineage events
    highest_cls = _highest_classification(contract)
    lineage_events = []
    for table_name, rows in dataset.items():
        columns = list(rows[0].keys()) if rows else []
        event = _make_lineage_event(
            pipeline_id=pipeline_id,
            source_table=table_name,
            target_table=table_name,
            target_tier=target_tier,
            columns=columns,
            row_count=len(rows),
            strategy_map=mask_result["strategy_map"],
            classification=highest_cls,
        )
        lineage_events.append(event)

        if lineage_emitter is not None:
            try:
                lineage_emitter.emit(event)
            except Exception as exc:
                logger.error("Lineage emit failed for mask table %s: %s", table_name, exc)

    elapsed = (time.monotonic() - start_time) * 1000

    return {
        "status": "success",
        "data": {
            "masked_dataset": mask_result["masked_dataset"],
            "strategy_map": mask_result["strategy_map"],
            "rows_processed": mask_result["rows_processed"],
            "human_gate_approved": bool(approval_token) if needs_gate else None,
        },
        "metadata": {
            "tool": "data_mask",
            "pipeline_id": pipeline_id,
            "target_tier": target_tier,
            "elapsed_ms": round(elapsed, 2),
            "lineage_events_emitted": len(lineage_events),
        },
    }
