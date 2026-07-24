"""
data_extract MCP Tool -- Data extraction with contract enforcement.

CISO-CRITICAL-001: No data extraction without a signed data contract.
Exceptions: dry_run=true returns schema + row count + 5-row sample without contract.

Elevated governance classification.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _make_lineage_event(
    pipeline_id: str,
    source_connector: str,
    source_table: str,
    columns: list[str],
    row_count: int,
    target_tier: str = "staging",
    classification: str = "internal",
) -> dict:
    """Build a lineage event dict for extraction."""
    content = json.dumps({"table": source_table, "columns": columns, "rows": row_count}, sort_keys=True)
    content_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    return {
        "event": {
            "gov_agent_id": "nhi_data-engineer_tool_extract",
            "gov_session_id": f"sess_extract_{pipeline_id}",
            "gov_classification": classification,
            "gov_timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_id": pipeline_id,
            "operation": "extract",
            "source": {
                "connector": source_connector,
                "table": source_table,
                "columns": columns,
                "row_count": row_count,
            },
            "target": {
                "connector": "internal/staging",
                "tier": target_tier,
                "table": source_table,
                "masking_applied": False,
            },
            "content_hash": content_hash,
        }
    }


# Simulated source data for testing
_SIMULATED_DATA = {
    "customers": {
        "columns": ["id", "name", "email", "phone", "address", "created_at", "tier"],
        "row_count": 45230,
        "sample": [
            {"id": 1, "name": "Alice Smith", "email": "alice@example.com", "phone": "+1-555-0101",
             "address": "123 Main St", "created_at": "2025-01-15", "tier": "gold"},
            {"id": 2, "name": "Bob Jones", "email": "bob@example.com", "phone": "+1-555-0102",
             "address": "456 Oak Ave", "created_at": "2025-02-20", "tier": "silver"},
            {"id": 3, "name": "Carol White", "email": "carol@example.com", "phone": "+1-555-0103",
             "address": "789 Pine Rd", "created_at": "2025-03-10", "tier": "bronze"},
            {"id": 4, "name": "Dave Brown", "email": "dave@example.com", "phone": "+1-555-0104",
             "address": "321 Elm St", "created_at": "2025-04-05", "tier": "gold"},
            {"id": 5, "name": "Eve Davis", "email": "eve@example.com", "phone": "+1-555-0105",
             "address": "654 Birch Ln", "created_at": "2025-05-25", "tier": "silver"},
        ],
    },
    "orders": {
        "columns": ["id", "customer_id", "amount", "status", "created_at"],
        "row_count": 128450,
        "sample": [
            {"id": 1001, "customer_id": 1, "amount": 299.99, "status": "completed", "created_at": "2025-06-01"},
            {"id": 1002, "customer_id": 2, "amount": 149.50, "status": "completed", "created_at": "2025-06-02"},
            {"id": 1003, "customer_id": 1, "amount": 89.00, "status": "pending", "created_at": "2025-06-03"},
            {"id": 1004, "customer_id": 3, "amount": 450.00, "status": "completed", "created_at": "2025-06-04"},
            {"id": 1005, "customer_id": 4, "amount": 75.25, "status": "refunded", "created_at": "2025-06-05"},
        ],
    },
}


def execute(params: dict) -> dict:
    """
    Execute data extraction with contract enforcement.

    Args:
        params: Dict with keys:
            - pipeline_id (str): Pipeline identifier
            - connector (str): Source connector type
            - tables (list[dict]): List of table specs with name and optional columns
            - contract (dict, optional): Data contract dict
            - contract_hash (str, optional): Expected SHA-256 hash of contract
            - dry_run (bool, optional): If true, return schema info only
            - reset_cursor (bool, optional): If true, reset incremental cursor
            - lineage_emitter (object, optional): LineageEmitter instance for emitting events
            - simulated_source (dict, optional): Override simulated data source

    Returns:
        Dict with status, data, and metadata.
    """
    pipeline_id = params.get("pipeline_id", "unknown")
    connector = params.get("connector", "")
    tables = params.get("tables", [])
    contract = params.get("contract")
    contract_hash = params.get("contract_hash")
    dry_run = params.get("dry_run", False)
    reset_cursor = params.get("reset_cursor", False)
    lineage_emitter = params.get("lineage_emitter")
    simulated_source = params.get("simulated_source", _SIMULATED_DATA)

    start_time = time.monotonic()

    if not tables:
        return {
            "status": "error",
            "data": {"error_code": "NO_TABLES", "message": "No tables specified for extraction"},
            "metadata": {"tool": "data_extract", "pipeline_id": pipeline_id},
        }

    # --- Dry run: return schema + row count (sample only when contract present) ---
    if dry_run:
        dry_run_results = {}
        for table_spec in tables:
            table_name = table_spec.get("name", table_spec) if isinstance(table_spec, dict) else table_spec
            source = simulated_source.get(table_name, {})
            table_result: dict = {
                "columns": source.get("columns", []),
                "row_count": source.get("row_count", 0),
            }
            # Only include sample rows when a contract is provided;
            # without a contract we cannot verify classification so
            # returning raw data would risk leaking PII.
            if contract is not None:
                table_result["sample"] = source.get("sample", [])[:5]
            dry_run_results[table_name] = table_result

        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "status": "success",
            "data": {
                "dry_run": True,
                "tables": dry_run_results,
            },
            "metadata": {
                "tool": "data_extract",
                "pipeline_id": pipeline_id,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    # --- Contract enforcement (CISO-CRITICAL-001) ---

    # Check 1: Contract must exist
    if contract is None:
        return {
            "status": "error",
            "data": {
                "error_code": "CONTRACT_REQUIRED",
                "message": "No data contract provided. Extraction requires a signed data contract.",
            },
            "metadata": {"tool": "data_extract", "pipeline_id": pipeline_id},
        }

    # Check 2: Validate contract hash if provided
    if contract_hash:
        actual_hash = hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()
        ).hexdigest()
        expected = contract_hash.replace("sha256:", "")
        if actual_hash != expected:
            return {
                "status": "error",
                "data": {
                    "error_code": "CONTRACT_TAMPERED",
                    "message": "Contract hash does not match expected value.",
                },
                "metadata": {"tool": "data_extract", "pipeline_id": pipeline_id},
            }

    # Check 3: Contract covers all requested columns
    contract_columns = set(contract.get("columns", {}).keys())

    for table_spec in tables:
        table_name = table_spec.get("name", table_spec) if isinstance(table_spec, dict) else table_spec
        requested_columns = table_spec.get("columns", []) if isinstance(table_spec, dict) else []

        # If no specific columns requested, use all available from source
        if not requested_columns:
            source = simulated_source.get(table_name, {})
            requested_columns = source.get("columns", [])

        for col in requested_columns:
            qualified_name = f"{table_name}.{col}"
            if qualified_name not in contract_columns:
                return {
                    "status": "error",
                    "data": {
                        "error_code": "CONTRACT_INCOMPLETE",
                        "message": f"Contract does not cover column '{qualified_name}'.",
                    },
                    "metadata": {"tool": "data_extract", "pipeline_id": pipeline_id},
                }

    # --- Schema drift detection ---
    for table_spec in tables:
        table_name = table_spec.get("name", table_spec) if isinstance(table_spec, dict) else table_spec
        source = simulated_source.get(table_name, {})
        source_columns = set(source.get("columns", []))
        requested_columns = table_spec.get("columns", []) if isinstance(table_spec, dict) else []

        if not requested_columns:
            requested_columns = list(source_columns)

        # Missing column in source -> SCHEMA_DRIFT error
        for col in requested_columns:
            if col not in source_columns:
                return {
                    "status": "error",
                    "data": {
                        "error_code": "SCHEMA_DRIFT",
                        "message": f"Column '{col}' in contract/request is missing from source table '{table_name}'.",
                    },
                    "metadata": {"tool": "data_extract", "pipeline_id": pipeline_id},
                }

    # --- Execute extraction ---
    extraction_results = {}
    warnings = []
    lineage_events = []

    for table_spec in tables:
        table_name = table_spec.get("name", table_spec) if isinstance(table_spec, dict) else table_spec
        source = simulated_source.get(table_name, {})
        requested_columns = table_spec.get("columns", []) if isinstance(table_spec, dict) else []

        if not requested_columns:
            requested_columns = source.get("columns", [])

        source_columns = set(source.get("columns", []))

        # New column in source that's not in contract -> warning
        for src_col in source_columns:
            qualified = f"{table_name}.{src_col}"
            if qualified not in contract_columns and src_col not in requested_columns:
                warnings.append(
                    f"New column '{src_col}' found in source table '{table_name}' not in contract (ignored)"
                )

        # Filter sample data to requested columns
        rows = source.get("sample", [])
        filtered_rows = [
            {k: v for k, v in row.items() if k in requested_columns}
            for row in rows
        ]

        extraction_results[table_name] = {
            "columns": requested_columns,
            "row_count": source.get("row_count", 0),
            "data": filtered_rows,
        }

        # Determine classification from contract
        classifications = set()
        for col in requested_columns:
            qualified = f"{table_name}.{col}"
            col_info = contract.get("columns", {}).get(qualified, {})
            classifications.add(col_info.get("classification", "internal"))

        # Use highest classification for lineage
        classification_order = ["public", "internal", "confidential", "restricted"]
        highest = "public"
        for c in classification_order:
            if c in classifications:
                highest = c

        # Build and emit lineage event
        event = _make_lineage_event(
            pipeline_id=pipeline_id,
            source_connector=connector,
            source_table=table_name,
            columns=requested_columns,
            row_count=source.get("row_count", 0),
            classification=highest,
        )
        lineage_events.append(event)

        if lineage_emitter is not None:
            try:
                lineage_emitter.emit(event)
            except Exception as exc:
                logger.error("Lineage emit failed for table %s: %s", table_name, exc)

    elapsed = (time.monotonic() - start_time) * 1000

    result = {
        "status": "success",
        "data": {
            "tables": extraction_results,
            "reset_cursor": reset_cursor,
        },
        "metadata": {
            "tool": "data_extract",
            "pipeline_id": pipeline_id,
            "elapsed_ms": round(elapsed, 2),
            "lineage_events_emitted": len(lineage_events),
        },
    }

    if warnings:
        result["data"]["warnings"] = warnings

    return result
