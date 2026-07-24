"""
data_transform MCP Tool -- Delegates to quality/transform_engine.py.

Executes transform operations (join, filter, derive, aggregate) via DuckDB
and emits lineage events. Elevated governance classification.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _make_lineage_event(
    pipeline_id: str,
    operation_type: str,
    source_table: str,
    target_table: str,
    columns: list[str],
    row_count: int,
    classification: str = "internal",
) -> dict:
    """Build a lineage event for a transform operation."""
    content = json.dumps(
        {"op": operation_type, "source": source_table, "target": target_table},
        sort_keys=True,
    )
    content_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    return {
        "event": {
            "gov_agent_id": "nhi_data-engineer_tool_transform",
            "gov_session_id": f"sess_transform_{pipeline_id}",
            "gov_classification": classification,
            "gov_timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_id": pipeline_id,
            "operation": "transform",
            "source": {
                "connector": "internal/duckdb",
                "table": source_table,
                "columns": columns,
                "row_count": row_count,
            },
            "target": {
                "connector": "internal/duckdb",
                "tier": "transform",
                "table": target_table,
                "masking_applied": False,
            },
            "content_hash": content_hash,
        }
    }


def execute(params: dict) -> dict:
    """
    Execute transform operations via the TransformEngine.

    Args:
        params: Dict with keys:
            - pipeline_id (str): Pipeline identifier
            - transforms (list[dict]): List of transform operation dicts
            - executor (DuckDBExecutor): DuckDB executor with loaded tables
            - lineage_emitter (object, optional): LineageEmitter instance
            - classification (str, optional): Data classification for lineage

    Returns:
        Dict with status, data, and metadata.
    """
    pipeline_id = params.get("pipeline_id", "unknown")
    transforms = params.get("transforms", [])
    executor = params.get("executor")
    lineage_emitter = params.get("lineage_emitter")
    classification = params.get("classification", "internal")

    start_time = time.monotonic()

    if not transforms:
        return {
            "status": "error",
            "data": {"error_code": "NO_TRANSFORMS", "message": "No transform operations specified"},
            "metadata": {"tool": "data_transform", "pipeline_id": pipeline_id},
        }

    if executor is None:
        return {
            "status": "error",
            "data": {"error_code": "NO_EXECUTOR", "message": "No DuckDB executor provided"},
            "metadata": {"tool": "data_transform", "pipeline_id": pipeline_id},
        }

    # Import here to allow mocking and avoid circular imports
    from quality.transform_engine import TransformEngine, TransformError

    engine = TransformEngine(executor)
    tables_before = set(executor.tables)

    try:
        engine.execute_transforms(transforms)
    except TransformError as exc:
        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "status": "error",
            "data": {
                "error_code": "TRANSFORM_ERROR",
                "message": str(exc),
            },
            "metadata": {
                "tool": "data_transform",
                "pipeline_id": pipeline_id,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    tables_after = set(executor.tables)
    new_tables = tables_after - tables_before

    # Emit lineage events for each transform
    lineage_events = []
    for transform in transforms:
        op = transform.get("operation", "unknown")
        # Determine source and target tables based on operation type
        if op == "join":
            source = f"{transform.get('left', 'unknown')}+{transform.get('right', 'unknown')}"
            target = transform.get("output", f"{transform.get('left')}_{transform.get('right')}_joined")
        elif op == "filter":
            source = transform.get("input", "unknown")
            target = transform.get("output", f"{source}_filtered")
        elif op == "derive":
            source = transform.get("table", transform.get("input", "unknown"))
            target = transform.get("output", source)
        elif op == "aggregate":
            source = transform.get("input", transform.get("table", "unknown"))
            target = transform.get("output", f"{source}_aggregated")
        else:
            source = "unknown"
            target = "unknown"

        event = _make_lineage_event(
            pipeline_id=pipeline_id,
            operation_type=op,
            source_table=source,
            target_table=target,
            columns=[],
            row_count=0,
            classification=classification,
        )
        lineage_events.append(event)

        if lineage_emitter is not None:
            try:
                lineage_emitter.emit(event)
            except Exception as exc:
                logger.error("Lineage emit failed for transform %s: %s", op, exc)

    elapsed = (time.monotonic() - start_time) * 1000

    return {
        "status": "success",
        "data": {
            "transforms_applied": len(transforms),
            "new_tables": sorted(new_tables),
            "all_tables": sorted(executor.tables),
        },
        "metadata": {
            "tool": "data_transform",
            "pipeline_id": pipeline_id,
            "elapsed_ms": round(elapsed, 2),
            "lineage_events_emitted": len(lineage_events),
        },
    }
