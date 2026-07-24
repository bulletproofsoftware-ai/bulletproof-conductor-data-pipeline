"""
data_lineage_query MCP Tool -- Delegates to lineage/query.py.

Supports four query types:
1. provenance -- trace backward from target to sources
2. impact_analysis -- forward walk from source to all targets
3. pii_audit -- Confidential/Restricted events in time range
4. pipeline_history -- all executions for a pipeline

Standard governance classification.
"""

import logging
import time

logger = logging.getLogger(__name__)


def execute(params: dict) -> dict:
    """
    Query lineage data via the LineageQueryEngine.

    Args:
        params: Dict with keys:
            - query_type (str): One of 'provenance', 'impact_analysis', 'pii_audit', 'pipeline_history'
            - query_engine (LineageQueryEngine): Query engine instance
            - For provenance: target_table (str), target_tier (str)
            - For impact_analysis: source_table (str)
            - For pii_audit: start_time (str), end_time (str)
            - For pipeline_history: pipeline_id (str)

    Returns:
        Dict with status, data (query results), and metadata.
    """
    query_type = params.get("query_type", "")
    query_engine = params.get("query_engine")

    start_time_monotonic = time.monotonic()

    if not query_type:
        return {
            "status": "error",
            "data": {"error_code": "NO_QUERY_TYPE", "message": "No query_type specified"},
            "metadata": {"tool": "data_lineage_query"},
        }

    if query_engine is None:
        return {
            "status": "error",
            "data": {"error_code": "NO_QUERY_ENGINE", "message": "No query engine provided"},
            "metadata": {"tool": "data_lineage_query"},
        }

    valid_types = {"provenance", "impact_analysis", "pii_audit", "pipeline_history"}
    if query_type not in valid_types:
        return {
            "status": "error",
            "data": {
                "error_code": "INVALID_QUERY_TYPE",
                "message": f"Invalid query_type '{query_type}'. Must be one of: {sorted(valid_types)}",
            },
            "metadata": {"tool": "data_lineage_query"},
        }

    try:
        if query_type == "provenance":
            target_table = params.get("target_table", "")
            target_tier = params.get("target_tier", "")
            if not target_table:
                return {
                    "status": "error",
                    "data": {"error_code": "MISSING_PARAM", "message": "provenance requires target_table"},
                    "metadata": {"tool": "data_lineage_query"},
                }
            result = query_engine.trace_provenance(target_table, target_tier)
            elapsed = (time.monotonic() - start_time_monotonic) * 1000
            return {
                "status": "success",
                "data": {
                    "query_type": "provenance",
                    "target_table": result.target_table,
                    "target_tier": result.target_tier,
                    "lineage_chain": result.lineage_chain,
                    "total_events": result.total_events,
                },
                "metadata": {
                    "tool": "data_lineage_query",
                    "elapsed_ms": round(elapsed, 2),
                },
            }

        elif query_type == "impact_analysis":
            source_table = params.get("source_table", "")
            if not source_table:
                return {
                    "status": "error",
                    "data": {"error_code": "MISSING_PARAM", "message": "impact_analysis requires source_table"},
                    "metadata": {"tool": "data_lineage_query"},
                }
            result = query_engine.impact_analysis(source_table)
            elapsed = (time.monotonic() - start_time_monotonic) * 1000
            return {
                "status": "success",
                "data": {
                    "query_type": "impact_analysis",
                    "source_table": result.source_table,
                    "affected_targets": result.affected_targets,
                    "total_affected": result.total_affected,
                },
                "metadata": {
                    "tool": "data_lineage_query",
                    "elapsed_ms": round(elapsed, 2),
                },
            }

        elif query_type == "pii_audit":
            start_time = params.get("start_time", "")
            end_time = params.get("end_time", "")
            if not start_time or not end_time:
                return {
                    "status": "error",
                    "data": {"error_code": "MISSING_PARAM", "message": "pii_audit requires start_time and end_time"},
                    "metadata": {"tool": "data_lineage_query"},
                }
            result = query_engine.pii_audit(start_time, end_time)
            elapsed = (time.monotonic() - start_time_monotonic) * 1000
            return {
                "status": "success",
                "data": {
                    "query_type": "pii_audit",
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "events": result.events,
                    "total_events": result.total_events,
                    "classifications_found": result.classifications_found,
                },
                "metadata": {
                    "tool": "data_lineage_query",
                    "elapsed_ms": round(elapsed, 2),
                },
            }

        elif query_type == "pipeline_history":
            pipeline_id = params.get("pipeline_id", "")
            if not pipeline_id:
                return {
                    "status": "error",
                    "data": {"error_code": "MISSING_PARAM", "message": "pipeline_history requires pipeline_id"},
                    "metadata": {"tool": "data_lineage_query"},
                }
            result = query_engine.pipeline_history(pipeline_id)
            elapsed = (time.monotonic() - start_time_monotonic) * 1000
            return {
                "status": "success",
                "data": {
                    "query_type": "pipeline_history",
                    "pipeline_id": result.pipeline_id,
                    "executions": result.executions,
                    "total_executions": result.total_executions,
                },
                "metadata": {
                    "tool": "data_lineage_query",
                    "elapsed_ms": round(elapsed, 2),
                },
            }

    except Exception as exc:
        elapsed = (time.monotonic() - start_time_monotonic) * 1000
        return {
            "status": "error",
            "data": {
                "error_code": "QUERY_ERROR",
                "message": str(exc),
            },
            "metadata": {
                "tool": "data_lineage_query",
                "query_type": query_type,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    # All valid query_types are handled by the if/elif chain above;
    # invalid types are rejected before this point. If we reach here
    # it indicates a logic error (e.g. a new query_type was added to
    # valid_types but not to the handler chain).
    raise RuntimeError(  # pragma: no cover
        f"Unhandled query_type '{query_type}' — handler chain out of sync with valid_types"
    )
