"""
Tests for the MCP Tool Registry.

Validates:
- All 8 tools registered
- Classifications correct
- Elevated tools create audit trail
- Human gate triggered for Confidential+
"""

import pytest

from tools.tool_registry import (
    ToolRegistry,
    CLASSIFICATION_STANDARD,
    CLASSIFICATION_ELEVATED,
    CLASSIFICATION_ELEVATED_HUMAN,
)


@pytest.fixture
def registry():
    """Fresh tool registry."""
    return ToolRegistry()


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------

class TestToolRegistration:
    """All 8 tools must be registered with correct metadata."""

    EXPECTED_TOOLS = [
        "data_connect",
        "data_contract_validate",
        "data_extract",
        "data_lineage_query",
        "data_load",
        "data_mask",
        "data_profile",
        "data_transform",
    ]

    def test_all_eight_tools_registered(self, registry):
        tools = registry.list_tools()
        assert len(tools) == 8
        assert tools == self.EXPECTED_TOOLS

    def test_each_tool_has_handler(self, registry):
        for name in self.EXPECTED_TOOLS:
            tool = registry.get(name)
            assert tool is not None, f"Tool '{name}' not registered"
            assert callable(tool.handler), f"Tool '{name}' handler not callable"

    def test_each_tool_has_schemas(self, registry):
        for name in self.EXPECTED_TOOLS:
            tool = registry.get(name)
            assert tool.input_schema, f"Tool '{name}' missing input_schema"
            assert tool.output_schema, f"Tool '{name}' missing output_schema"

    def test_each_tool_has_description(self, registry):
        for name in self.EXPECTED_TOOLS:
            tool = registry.get(name)
            assert len(tool.description) > 10, f"Tool '{name}' description too short"


# ---------------------------------------------------------------------------
# Classification Tests
# ---------------------------------------------------------------------------

class TestClassifications:
    """Governance classifications must match spec."""

    def test_standard_tools(self, registry):
        standard_tools = ["data_connect", "data_lineage_query", "data_contract_validate"]
        for name in standard_tools:
            assert registry.get_classification(name) == CLASSIFICATION_STANDARD, \
                f"Tool '{name}' should be standard"

    def test_elevated_tools(self, registry):
        elevated_tools = ["data_profile", "data_extract", "data_transform"]
        for name in elevated_tools:
            assert registry.get_classification(name) == CLASSIFICATION_ELEVATED, \
                f"Tool '{name}' should be elevated"

    def test_elevated_human_gate_tools(self, registry):
        human_tools = ["data_mask", "data_load"]
        for name in human_tools:
            assert registry.get_classification(name) == CLASSIFICATION_ELEVATED_HUMAN, \
                f"Tool '{name}' should be elevated_human_gate"

    def test_unknown_tool_returns_none(self, registry):
        assert registry.get_classification("nonexistent") is None


# ---------------------------------------------------------------------------
# Audit Trail Tests
# ---------------------------------------------------------------------------

class TestAuditTrail:
    """Elevated tools must create audit trail entries."""

    def test_standard_tool_no_audit_trail(self, registry):
        """Standard tools should NOT create audit trail entries."""
        registry.invoke("data_connect", {
            "connector": "airbyte/source-postgres",
            "connection": {"host": "localhost"},
        })
        assert len(registry.audit_trail) == 0

    def test_elevated_tool_creates_audit_entry(self, registry):
        """Elevated tools must create audit trail entries."""
        registry.invoke("data_extract", {
            "pipeline_id": "test-pipe",
            "connector": "airbyte/source-postgres",
            "tables": [{"name": "customers"}],
            "dry_run": True,
        }, caller="test-agent")

        assert len(registry.audit_trail) == 1
        entry = registry.audit_trail[0]
        assert entry.tool_name == "data_extract"
        assert entry.classification == CLASSIFICATION_ELEVATED
        assert entry.caller == "test-agent"
        assert entry.result_status == "success"
        assert entry.duration_ms >= 0

    def test_elevated_human_tool_creates_audit_entry(self, registry):
        """Elevated+human tools must also create audit trail entries."""
        registry.invoke("data_mask", {
            "pipeline_id": "test-pipe",
            "dataset": {"t": [{"a": 1}]},
            "contract": {"columns": {"t.a": {"classification": "public", "pii": False}}},
            "policy": {"defaults": {"strategy": "passthrough"}, "rules": []},
        })

        assert len(registry.audit_trail) == 1
        entry = registry.audit_trail[0]
        assert entry.tool_name == "data_mask"
        assert entry.classification == CLASSIFICATION_ELEVATED_HUMAN

    def test_multiple_invocations_accumulate(self, registry):
        """Audit trail should accumulate entries across invocations."""
        for _ in range(3):
            registry.invoke("data_extract", {
                "pipeline_id": "test-pipe",
                "connector": "test",
                "tables": [{"name": "t"}],
                "dry_run": True,
            })
        assert len(registry.audit_trail) == 3


# ---------------------------------------------------------------------------
# Human Gate Tests
# ---------------------------------------------------------------------------

class TestHumanGate:
    """Human gate must be triggered for Confidential+ data."""

    def test_mask_confidential_requires_gate(self, registry):
        """data_mask with confidential data requires human gate."""
        result = registry.invoke("data_mask", {
            "pipeline_id": "test-pipe",
            "dataset": {"customers": [{"name": "Alice"}]},
            "contract": {
                "columns": {
                    "customers.name": {"classification": "confidential", "pii": True},
                },
            },
            "policy": {"defaults": {"strategy": "tokenize"}, "rules": []},
        })

        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"
        assert result["data"]["requires_approval"] is True

    def test_mask_confidential_approved_succeeds(self, registry):
        """data_mask with confidential data + approval succeeds."""
        result = registry.invoke("data_mask", {
            "pipeline_id": "test-pipe",
            "dataset": {"customers": [{"name": "Alice"}]},
            "contract": {
                "columns": {
                    "customers.name": {"classification": "confidential", "pii": True},
                },
            },
            "policy": {"defaults": {"strategy": "tokenize"}, "rules": []},
            "approval_token": "a" * 64,
        })

        assert result["status"] == "success"

    def test_load_restricted_requires_gate(self, registry):
        """data_load with restricted classification requires human gate."""
        result = registry.invoke("data_load", {
            "pipeline_id": "test-pipe",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "restricted",
        })

        assert result["status"] == "error"
        assert result["data"]["error_code"] == "HUMAN_GATE_REQUIRED"

    def test_load_public_no_gate(self, registry):
        """data_load with public classification does not require gate."""
        result = registry.invoke("data_load", {
            "pipeline_id": "test-pipe",
            "dataset": {"t": [{"a": 1}]},
            "target_tier": "staging",
            "classification": "public",
        })

        assert result["status"] == "success"

    def test_nonexistent_tool_returns_error(self, registry):
        """Invoking a nonexistent tool returns TOOL_NOT_FOUND."""
        result = registry.invoke("nonexistent_tool", {})
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "TOOL_NOT_FOUND"
