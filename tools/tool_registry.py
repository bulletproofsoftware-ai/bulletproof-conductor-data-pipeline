"""
Tool Registry -- Register all 8 MCP tools with governance classification.

Classifications:
- Standard (no gate): data_connect, data_lineage_query, data_contract_validate
- Elevated (audit trail): data_profile, data_extract, data_transform
- Elevated + Human Gate for Confidential+: data_mask, data_load
"""

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

from tools import data_connect
from tools import data_extract
from tools import data_transform
from tools import data_mask
from tools import data_load
from tools import data_profile
from tools import data_contract_validate
from tools import data_lineage_query

logger = logging.getLogger(__name__)


# Governance classification levels
CLASSIFICATION_STANDARD = "standard"
CLASSIFICATION_ELEVATED = "elevated"
CLASSIFICATION_ELEVATED_HUMAN = "elevated_human_gate"

# Audit trail entry
@dataclass
class AuditEntry:
    """Audit trail record for elevated tool invocations."""
    tool_name: str
    classification: str
    timestamp: float
    caller: str
    params_summary: dict
    result_status: str
    duration_ms: float


@dataclass
class ToolDefinition:
    """Definition of a registered MCP tool."""
    name: str
    description: str
    classification: str
    handler: Callable[[dict], dict]
    input_schema: dict
    output_schema: dict


class ToolRegistry:
    """
    Registry of all MCP tools with governance classification.

    Elevated tools create audit trail entries on every invocation.
    Elevated + Human Gate tools additionally check for human approval
    when data classification is Confidential or Restricted.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._audit_trail: list[AuditEntry] = []
        self._register_all()

    def _register_all(self) -> None:
        """Register all 8 MCP tools."""
        self.register(ToolDefinition(
            name="data_connect",
            description="Test connectivity to a data source and return schema catalog",
            classification=CLASSIFICATION_STANDARD,
            handler=data_connect.execute,
            input_schema={
                "type": "object",
                "required": ["connector", "connection"],
                "properties": {
                    "connector": {"type": "string"},
                    "connection": {"type": "object"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "connected": {"type": "boolean"},
                    "catalog": {"type": "object"},
                },
            },
        ))

        self.register(ToolDefinition(
            name="data_extract",
            description="Extract data from source with contract enforcement (CISO-CRITICAL-001)",
            classification=CLASSIFICATION_ELEVATED,
            handler=data_extract.execute,
            input_schema={
                "type": "object",
                "required": ["pipeline_id", "connector", "tables"],
                "properties": {
                    "pipeline_id": {"type": "string"},
                    "connector": {"type": "string"},
                    "tables": {"type": "array"},
                    "contract": {"type": "object"},
                    "dry_run": {"type": "boolean"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "tables": {"type": "object"},
                },
            },
        ))

        self.register(ToolDefinition(
            name="data_transform",
            description="Apply transform operations (join, filter, derive, aggregate) via DuckDB",
            classification=CLASSIFICATION_ELEVATED,
            handler=data_transform.execute,
            input_schema={
                "type": "object",
                "required": ["pipeline_id", "transforms", "executor"],
                "properties": {
                    "pipeline_id": {"type": "string"},
                    "transforms": {"type": "array"},
                    "executor": {"type": "object"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "transforms_applied": {"type": "integer"},
                    "new_tables": {"type": "array"},
                },
            },
        ))

        self.register(ToolDefinition(
            name="data_mask",
            description="Apply masking policy to dataset. Human gate for Confidential+",
            classification=CLASSIFICATION_ELEVATED_HUMAN,
            handler=data_mask.execute,
            input_schema={
                "type": "object",
                "required": ["pipeline_id", "dataset", "contract"],
                "properties": {
                    "pipeline_id": {"type": "string"},
                    "dataset": {"type": "object"},
                    "contract": {"type": "object"},
                    "policy": {"type": "object"},
                    "target_tier": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "masked_dataset": {"type": "object"},
                    "strategy_map": {"type": "object"},
                },
            },
        ))

        self.register(ToolDefinition(
            name="data_load",
            description="Atomic load to target via staging tables. Human gate for Confidential+",
            classification=CLASSIFICATION_ELEVATED_HUMAN,
            handler=data_load.execute,
            input_schema={
                "type": "object",
                "required": ["pipeline_id", "dataset", "target_tier"],
                "properties": {
                    "pipeline_id": {"type": "string"},
                    "dataset": {"type": "object"},
                    "target_tier": {"type": "string"},
                    "classification": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "loaded_tables": {"type": "array"},
                    "rows_loaded": {"type": "object"},
                },
            },
        ))

        self.register(ToolDefinition(
            name="data_profile",
            description="Analyze dataset: column types, cardinality, null rates, PII detection",
            classification=CLASSIFICATION_ELEVATED,
            handler=data_profile.execute,
            input_schema={
                "type": "object",
                "required": ["dataset"],
                "properties": {
                    "dataset": {"type": "object"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "tables": {"type": "object"},
                    "total_pii_flags": {"type": "integer"},
                },
            },
        ))

        self.register(ToolDefinition(
            name="data_contract_validate",
            description="Validate pipeline + contract + policy consistency against schemas",
            classification=CLASSIFICATION_STANDARD,
            handler=data_contract_validate.execute,
            input_schema={
                "type": "object",
                "required": ["pipeline", "contract"],
                "properties": {
                    "pipeline": {"type": "object"},
                    "contract": {"type": "object"},
                    "policy": {"type": "object"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "valid": {"type": "boolean"},
                    "errors": {"type": "array"},
                    "warnings": {"type": "array"},
                },
            },
        ))

        self.register(ToolDefinition(
            name="data_lineage_query",
            description="Query lineage: provenance, impact analysis, PII audit, pipeline history",
            classification=CLASSIFICATION_STANDARD,
            handler=data_lineage_query.execute,
            input_schema={
                "type": "object",
                "required": ["query_type", "query_engine"],
                "properties": {
                    "query_type": {"type": "string"},
                    "query_engine": {"type": "object"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "query_type": {"type": "string"},
                },
            },
        ))

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return sorted(self._tools.keys())

    def get_classification(self, name: str) -> Optional[str]:
        """Get the governance classification for a tool."""
        tool = self._tools.get(name)
        return tool.classification if tool else None

    @property
    def audit_trail(self) -> list[AuditEntry]:
        """Return the audit trail."""
        return list(self._audit_trail)

    def invoke(self, name: str, params: dict, caller: str = "unknown") -> dict:
        """
        Invoke a tool by name with governance enforcement.

        For elevated tools, creates an audit trail entry.
        For elevated+human gate tools, checks human_gate_approved in params
        if data classification is Confidential or Restricted.

        Args:
            name: Tool name.
            params: Tool parameters.
            caller: Identifier of the calling agent.

        Returns:
            Tool execution result dict.
        """
        tool = self._tools.get(name)
        if tool is None:
            return {
                "status": "error",
                "data": {"error_code": "TOOL_NOT_FOUND", "message": f"Tool '{name}' not registered"},
                "metadata": {},
            }

        start_time = time.monotonic()

        # Execute the tool
        result = tool.handler(params)

        elapsed = (time.monotonic() - start_time) * 1000

        # Create audit trail entry for elevated tools
        if tool.classification in (CLASSIFICATION_ELEVATED, CLASSIFICATION_ELEVATED_HUMAN):
            # Build a params summary (exclude sensitive data)
            params_summary = {
                k: v for k, v in params.items()
                if k not in ("credential_resolver", "lineage_emitter", "executor",
                             "query_engine", "target_store")
                and not callable(v)
            }
            # Truncate large values
            for k, v in params_summary.items():
                if isinstance(v, (dict, list)):
                    s = str(v)
                    if len(s) > 200:
                        params_summary[k] = f"<{type(v).__name__} len={len(v)}>"

            entry = AuditEntry(
                tool_name=name,
                classification=tool.classification,
                timestamp=time.time(),
                caller=caller,
                params_summary=params_summary,
                result_status=result.get("status", "unknown"),
                duration_ms=round(elapsed, 2),
            )
            self._audit_trail.append(entry)
            logger.info(
                "AUDIT: tool=%s classification=%s caller=%s status=%s duration=%.2fms",
                name,
                tool.classification,
                caller,
                result.get("status"),
                elapsed,
            )

        return result


# Module-level singleton
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the module-level ToolRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
