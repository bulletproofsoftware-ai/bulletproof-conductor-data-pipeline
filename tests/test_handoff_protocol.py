"""
Test suite for Handoff Protocol (TODO-010).

Validates 5 handoff routes, artifact type registry, handoff validation
rules, and cycle detection per SPEC.md Section 4.3.
"""

import pytest

from agents import (
    load_handoff_protocol,
    get_handoff_routes,
    get_artifact_type_registry,
    validate_handoff_route,
    detect_handoff_cycles,
    load_all_agent_definitions,
    HANDOFF_YAML,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def protocol():
    """Load the handoff protocol."""
    return load_handoff_protocol()


@pytest.fixture
def routes():
    """Get all handoff routes."""
    return get_handoff_routes()


@pytest.fixture
def registry():
    """Get the artifact type registry."""
    return get_artifact_type_registry()


@pytest.fixture
def agents():
    """Load both data agent definitions."""
    return load_all_agent_definitions()


# ===================================================================
# PROTOCOL LOADING
# ===================================================================

class TestProtocolLoading:
    """Tests for handoff protocol YAML loading."""

    def test_handoff_yaml_exists(self):
        assert HANDOFF_YAML.exists(), f"Missing: {HANDOFF_YAML}"

    def test_protocol_parses(self, protocol):
        assert isinstance(protocol, dict)

    def test_has_routes(self, protocol):
        assert "routes" in protocol

    def test_has_artifact_type_registry(self, protocol):
        assert "artifact_type_registry" in protocol

    def test_has_validation_rules(self, protocol):
        assert "validation_rules" in protocol


# ===================================================================
# ROUTE DEFINITIONS (5 routes per Spec Section 4.3)
# ===================================================================

class TestHandoffRoutes:
    """Tests for the 5 handoff routes."""

    def test_five_routes_defined(self, routes):
        assert len(routes) == 5

    def test_route_001_architect_to_engineer(self, routes):
        r = routes[0]
        assert r["id"] == "route-001"
        assert r["source"] == "conductor-architect"
        assert r["target"] == "conductor-data-engineer"
        assert r["artifact_type"] == "data-requirements"

    def test_route_002_engineer_to_steward(self, routes):
        r = routes[1]
        assert r["id"] == "route-002"
        assert r["source"] == "conductor-data-engineer"
        assert r["target"] == "conductor-data-steward"
        assert r["artifact_type"] == "pipeline-definition"

    def test_route_003_steward_to_engineer(self, routes):
        r = routes[2]
        assert r["id"] == "route-003"
        assert r["source"] == "conductor-data-steward"
        assert r["target"] == "conductor-data-engineer"
        assert r["artifact_type"] == "data-contract"
        assert r["direction"] == "return"  # Response flow, not new work

    def test_route_004_engineer_to_builder(self, routes):
        r = routes[3]
        assert r["id"] == "route-004"
        assert r["source"] == "conductor-data-engineer"
        assert r["target"] == "conductor-builder"
        assert r["artifact_type"] == "extraction-report"

    def test_route_005_builder_direct_tool(self, routes):
        r = routes[4]
        assert r["id"] == "route-005"
        assert r["source"] == "conductor-builder"
        assert r["direction"] == "direct"
        assert r["tool_call"] == "data_extract"

    def test_all_routes_have_required_fields(self, routes):
        for r in routes:
            assert "id" in r, f"Route missing id: {r}"
            assert "source" in r, f"Route {r.get('id')} missing source"
            assert "description" in r, f"Route {r.get('id')} missing description"
            assert "direction" in r, f"Route {r.get('id')} missing direction"

    def test_all_route_ids_unique(self, routes):
        ids = [r["id"] for r in routes]
        assert len(ids) == len(set(ids)), f"Duplicate route ids: {ids}"


# ===================================================================
# HANDOFF VALIDATION
# ===================================================================

class TestHandoffValidation:
    """Tests for handoff route validation against agent definitions."""

    def test_route_002_engineer_produces_pipeline_definition(self, routes, agents):
        """Engineer produces pipeline-definition, steward accepts it."""
        route = routes[1]  # route-002
        errors = validate_handoff_route(route, agents)
        assert errors == [], f"Validation errors: {errors}"

    def test_route_003_return_route_passes(self, routes, agents):
        """Return route (steward -> engineer) skips standard accepts validation."""
        route = routes[2]  # route-003 (direction: return)
        errors = validate_handoff_route(route, agents)
        assert errors == [], f"Validation errors: {errors}"

    def test_invalid_route_source_not_producing(self, agents):
        """A route where source doesn't produce the artifact should fail."""
        bad_route = {
            "id": "route-bad",
            "source": "conductor-data-steward",
            "target": "conductor-data-engineer",
            "artifact_type": "pipeline-definition",  # steward doesn't produce this
            "direction": "forward",
        }
        errors = validate_handoff_route(bad_route, agents)
        assert len(errors) > 0
        assert "pipeline-definition" in errors[0]

    def test_invalid_route_target_not_accepting(self, agents):
        """A route where target doesn't accept the artifact should fail."""
        bad_route = {
            "id": "route-bad2",
            "source": "conductor-data-engineer",
            "target": "conductor-data-steward",
            "artifact_type": "extraction-report",  # steward doesn't accept this
            "direction": "forward",
        }
        errors = validate_handoff_route(bad_route, agents)
        assert len(errors) > 0
        assert "extraction-report" in errors[0]

    def test_direct_route_skips_validation(self, agents):
        """Direct tool call routes skip agent-level validation."""
        direct_route = {
            "id": "route-direct",
            "source": "conductor-builder",
            "target": None,
            "artifact_type": None,
            "tool_call": "data_extract",
            "direction": "direct",
        }
        errors = validate_handoff_route(direct_route, agents)
        assert errors == []

    def test_unknown_agent_passes_gracefully(self, agents):
        """Routes with agents not in the definitions dict are skipped."""
        route = {
            "id": "route-external",
            "source": "conductor-architect",
            "target": "conductor-data-engineer",
            "artifact_type": "data-requirements",
            "direction": "forward",
        }
        # conductor-architect is not in the data agents dict, so no error
        errors = validate_handoff_route(route, agents)
        assert errors == []


# ===================================================================
# CYCLE DETECTION
# ===================================================================

class TestCycleDetection:
    """Tests for cycle detection in handoff routes."""

    def test_no_cycles_in_protocol(self, routes):
        """The actual handoff routes should have no cycles."""
        cycles = detect_handoff_cycles(routes)
        assert cycles == [], f"Cycles found: {cycles}"

    def test_detects_simple_cycle(self):
        """Two-node cycle should be detected."""
        cyclic_routes = [
            {"source": "A", "target": "B", "direction": "forward"},
            {"source": "B", "target": "A", "direction": "forward"},
        ]
        cycles = detect_handoff_cycles(cyclic_routes)
        assert len(cycles) > 0

    def test_detects_three_node_cycle(self):
        """Three-node cycle: A -> B -> C -> A."""
        cyclic_routes = [
            {"source": "A", "target": "B", "direction": "forward"},
            {"source": "B", "target": "C", "direction": "forward"},
            {"source": "C", "target": "A", "direction": "forward"},
        ]
        cycles = detect_handoff_cycles(cyclic_routes)
        assert len(cycles) > 0

    def test_no_cycle_in_dag(self):
        """Linear chain: A -> B -> C has no cycles."""
        dag_routes = [
            {"source": "A", "target": "B", "direction": "forward"},
            {"source": "B", "target": "C", "direction": "forward"},
        ]
        cycles = detect_handoff_cycles(dag_routes)
        assert cycles == []

    def test_direct_routes_excluded_from_cycle_check(self):
        """Direct routes (tool calls) should not participate in cycle detection."""
        routes = [
            {"source": "A", "target": "B", "direction": "forward"},
            {"source": "B", "target": "A", "direction": "direct", "tool_call": "something"},
        ]
        cycles = detect_handoff_cycles(routes)
        assert cycles == []

    def test_return_routes_excluded_from_cycle_check(self):
        """Return routes (response flows) should not participate in cycle detection."""
        routes = [
            {"source": "A", "target": "B", "direction": "forward"},
            {"source": "B", "target": "A", "direction": "return"},
        ]
        cycles = detect_handoff_cycles(routes)
        assert cycles == []

    def test_empty_routes_no_cycles(self):
        cycles = detect_handoff_cycles([])
        assert cycles == []


# ===================================================================
# ARTIFACT TYPE REGISTRY
# ===================================================================

class TestArtifactTypeRegistry:
    """Tests for the artifact type registry."""

    EXPECTED_ARTIFACT_TYPES = {
        "pipeline-definition",
        "data-contract",
        "schema-profile",
        "extraction-report",
        "masking-recommendation",
        "lineage-report",
        "classification-audit",
    }

    def test_all_artifact_types_registered(self, registry):
        registered = {art["name"] for art in registry}
        assert self.EXPECTED_ARTIFACT_TYPES == registered

    def test_each_artifact_has_producer(self, registry):
        for art in registry:
            assert "producer" in art, f"Artifact '{art['name']}' missing producer"
            assert isinstance(art["producer"], str)

    def test_each_artifact_has_consumers(self, registry):
        for art in registry:
            assert "consumers" in art, f"Artifact '{art['name']}' missing consumers"
            assert isinstance(art["consumers"], list)
            assert len(art["consumers"]) > 0

    def test_each_artifact_has_description(self, registry):
        for art in registry:
            assert "description" in art, f"Artifact '{art['name']}' missing description"
            assert len(art["description"]) > 10

    def test_pipeline_definition_producer(self, registry):
        art = next(a for a in registry if a["name"] == "pipeline-definition")
        assert art["producer"] == "conductor-data-engineer"

    def test_data_contract_producer(self, registry):
        art = next(a for a in registry if a["name"] == "data-contract")
        assert art["producer"] == "conductor-data-steward"

    def test_pipeline_definition_schema_ref(self, registry):
        art = next(a for a in registry if a["name"] == "pipeline-definition")
        assert art["schema_ref"] == "pipeline.schema.json"

    def test_data_contract_schema_ref(self, registry):
        art = next(a for a in registry if a["name"] == "data-contract")
        assert art["schema_ref"] == "contract.schema.json"

    def test_route_artifacts_in_registry(self, routes, registry):
        """All artifact types from routes must be in the registry."""
        registered = {art["name"] for art in registry}
        for route in routes:
            artifact = route.get("artifact_type")
            if artifact is not None:
                assert artifact in registered or artifact == "data-requirements", \
                    f"Route {route['id']} artifact '{artifact}' not in registry"


# ===================================================================
# VALIDATION RULES
# ===================================================================

class TestValidationRules:
    """Tests for the protocol validation rules."""

    def test_three_validation_rules(self, protocol):
        rules = protocol["validation_rules"]
        assert len(rules) == 3

    def test_source_produces_rule(self, protocol):
        rules = protocol["validation_rules"]
        rule_names = [r["rule"] for r in rules]
        assert "source_produces_artifact" in rule_names

    def test_target_accepts_rule(self, protocol):
        rules = protocol["validation_rules"]
        rule_names = [r["rule"] for r in rules]
        assert "target_accepts_artifact" in rule_names

    def test_no_circular_rule(self, protocol):
        rules = protocol["validation_rules"]
        rule_names = [r["rule"] for r in rules]
        assert "no_circular_dependencies" in rule_names
