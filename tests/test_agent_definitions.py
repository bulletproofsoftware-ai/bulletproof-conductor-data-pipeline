"""
Test suite for Agent Definitions (TODO-010).

Validates conductor-data-engineer and conductor-data-steward YAML definitions
against spec requirements from SPEC.md Sections 4.1 and 4.2.
"""

import pytest

from agents import (
    load_agent_definition,
    load_all_agent_definitions,
    validate_agent_definition,
    REQUIRED_AGENT_FIELDS,
    ENGINEER_YAML,
    STEWARD_YAML,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engineer():
    """Load conductor-data-engineer definition."""
    return load_agent_definition("conductor-data-engineer")


@pytest.fixture
def steward():
    """Load conductor-data-steward definition."""
    return load_agent_definition("conductor-data-steward")


@pytest.fixture
def all_agents():
    """Load all agent definitions."""
    return load_all_agent_definitions()


# ===================================================================
# YAML LOADING TESTS
# ===================================================================

class TestAgentYAMLLoading:
    """Tests that YAML files load and parse correctly."""

    def test_engineer_yaml_exists(self):
        assert ENGINEER_YAML.exists(), f"Missing: {ENGINEER_YAML}"

    def test_steward_yaml_exists(self):
        assert STEWARD_YAML.exists(), f"Missing: {STEWARD_YAML}"

    def test_engineer_yaml_parses(self, engineer):
        assert isinstance(engineer, dict)
        assert len(engineer) > 0

    def test_steward_yaml_parses(self, steward):
        assert isinstance(steward, dict)
        assert len(steward) > 0

    def test_load_all_returns_both(self, all_agents):
        assert "conductor-data-engineer" in all_agents
        assert "conductor-data-steward" in all_agents

    def test_load_unknown_agent_raises(self):
        with pytest.raises(ValueError, match="Unknown agent"):
            load_agent_definition("conductor-janitor")


# ===================================================================
# CONDUCTOR-DATA-ENGINEER TESTS (Spec Section 4.1)
# ===================================================================

class TestDataEngineerDefinition:
    """Tests for Agent 15: conductor-data-engineer per SPEC.md 4.1."""

    def test_name(self, engineer):
        assert engineer["name"] == "conductor-data-engineer"

    def test_agent_id(self, engineer):
        assert engineer["agent_id"] == 15

    def test_model(self, engineer):
        assert engineer["model"] == "opus[1m]"

    def test_role(self, engineer):
        assert engineer["role"] == "Designs and executes data pipelines for conductor workflows"

    def test_accepts(self, engineer):
        expected = {"data-requirements", "schema-analysis-request", "pipeline-revision"}
        assert set(engineer["accepts"]) == expected

    def test_produces(self, engineer):
        expected = {"pipeline-definition", "schema-profile", "extraction-report"}
        assert set(engineer["produces"]) == expected

    def test_requires(self, engineer):
        expected = {"BRD-tracker.json", "source-connection-config"}
        assert set(engineer["requires"]) == expected

    def test_four_hard_constraints(self, engineer):
        assert len(engineer["constraints"]) == 4

    def test_constraint_no_credentials(self, engineer):
        assert any("credential" in c.lower() for c in engineer["constraints"])

    def test_constraint_no_extract_without_contract(self, engineer):
        assert any("contract" in c.lower() and "extract" in c.lower()
                    for c in engineer["constraints"])

    def test_constraint_incremental_preferred(self, engineer):
        assert any("incremental" in c.lower() for c in engineer["constraints"])

    def test_constraint_assertions_pass(self, engineer):
        assert any("assertion" in c.lower() for c in engineer["constraints"])

    def test_two_intent_constraints(self, engineer):
        assert len(engineer["intent_constraints"]) == 2

    def test_intent_minimize_surface(self, engineer):
        assert any("minimize" in ic.lower() or "surface" in ic.lower()
                    for ic in engineer["intent_constraints"])

    def test_intent_narrow_filters(self, engineer):
        assert any("narrow" in ic.lower() or "filter" in ic.lower()
                    for ic in engineer["intent_constraints"])

    def test_tools_all_eight(self, engineer):
        expected_tools = {
            "data_connect", "data_extract", "data_transform", "data_mask",
            "data_load", "data_profile", "data_contract_validate", "data_lineage_query",
        }
        assert set(engineer["tools"]) == expected_tools

    def test_gate_participation(self, engineer):
        gate = engineer["gate_participation"]
        assert gate["produces_for"] == "POST-DATA-PIPELINE"
        assert gate["receives_results"] is True

    def test_validation_passes(self, engineer):
        errors = validate_agent_definition(engineer)
        assert errors == [], f"Validation errors: {errors}"


# ===================================================================
# CONDUCTOR-DATA-STEWARD TESTS (Spec Section 4.2)
# ===================================================================

class TestDataStewardDefinition:
    """Tests for Agent 16: conductor-data-steward per SPEC.md 4.2."""

    def test_name(self, steward):
        assert steward["name"] == "conductor-data-steward"

    def test_agent_id(self, steward):
        assert steward["agent_id"] == 16

    def test_model(self, steward):
        assert steward["model"] == "opus[1m]"

    def test_role(self, steward):
        assert steward["role"] == "Classifies data, governs masking policies, validates lineage"

    def test_accepts(self, steward):
        expected = {"pipeline-definition", "classification-request", "lineage-query"}
        assert set(steward["accepts"]) == expected

    def test_produces(self, steward):
        expected = {"data-contract", "masking-recommendation", "lineage-report", "classification-audit"}
        assert set(steward["produces"]) == expected

    def test_requires(self, steward):
        expected = {"pipeline-definition", "classification-patterns.yaml", "masking-policies/"}
        assert set(steward["requires"]) == expected

    def test_four_hard_constraints(self, steward):
        assert len(steward["constraints"]) == 4

    def test_constraint_every_column_classified(self, steward):
        assert any("every column" in c.lower() or "classified" in c.lower()
                    for c in steward["constraints"])

    def test_constraint_restricted_human_gate(self, steward):
        assert any("restricted" in c.lower() and "human" in c.lower()
                    for c in steward["constraints"])

    def test_constraint_classification_reasoning(self, steward):
        assert any("reasoning" in c.lower() for c in steward["constraints"])

    def test_constraint_referential_integrity(self, steward):
        assert any("referential integrity" in c.lower() for c in steward["constraints"])

    def test_two_intent_constraints(self, steward):
        assert len(steward["intent_constraints"]) == 2

    def test_intent_escalate_uncertain(self, steward):
        assert any("uncertain" in ic.lower() or "escalate" in ic.lower()
                    for ic in steward["intent_constraints"])

    def test_intent_prefer_tokenization(self, steward):
        assert any("tokenization" in ic.lower() for ic in steward["intent_constraints"])

    def test_tools_four(self, steward):
        expected_tools = {"data_profile", "data_mask", "data_contract_validate", "data_lineage_query"}
        assert set(steward["tools"]) == expected_tools

    def test_gate_agent_for_post_data_pipeline(self, steward):
        gate = steward["gate_participation"]
        assert gate["gate_agent_for"] == "POST-DATA-PIPELINE"
        assert gate["mode"] == "BLOCKING"

    def test_validation_passes(self, steward):
        errors = validate_agent_definition(steward)
        assert errors == [], f"Validation errors: {errors}"


# ===================================================================
# VALIDATION FUNCTION TESTS
# ===================================================================

class TestAgentValidation:
    """Tests for the validate_agent_definition function."""

    def test_empty_dict_fails(self):
        errors = validate_agent_definition({})
        assert len(errors) == len(REQUIRED_AGENT_FIELDS)

    def test_missing_single_field(self, engineer):
        incomplete = dict(engineer)
        del incomplete["intent_constraints"]
        errors = validate_agent_definition(incomplete)
        assert any("intent_constraints" in e for e in errors)

    def test_empty_list_field_fails(self, engineer):
        bad = dict(engineer)
        bad["constraints"] = []
        errors = validate_agent_definition(bad)
        assert any("constraints" in e for e in errors)

    def test_non_list_field_fails(self, engineer):
        bad = dict(engineer)
        bad["produces"] = "pipeline-definition"
        errors = validate_agent_definition(bad)
        assert any("produces" in e for e in errors)

    def test_empty_model_fails(self):
        defn = {
            "name": "test",
            "model": "",
            "role": "test role",
            "accepts": ["a"],
            "produces": ["b"],
            "requires": ["c"],
            "constraints": ["d"],
            "intent_constraints": ["e"],
        }
        errors = validate_agent_definition(defn)
        assert any("model" in e for e in errors)

    def test_valid_minimal_definition(self):
        defn = {
            "name": "test-agent",
            "model": "sonnet[500k]",
            "role": "A test agent",
            "accepts": ["request"],
            "produces": ["result"],
            "requires": ["config"],
            "constraints": ["must do X"],
            "intent_constraints": ["prefer Y"],
        }
        errors = validate_agent_definition(defn)
        assert errors == []


# ===================================================================
# CROSS-AGENT CONSISTENCY TESTS
# ===================================================================

class TestCrossAgentConsistency:
    """Tests for consistency between the two agent definitions."""

    def test_both_use_same_api_version(self, engineer, steward):
        assert engineer["apiVersion"] == steward["apiVersion"]

    def test_both_use_same_kind(self, engineer, steward):
        assert engineer["kind"] == steward["kind"] == "AgentDefinition"

    def test_engineer_produces_what_steward_accepts(self, engineer, steward):
        """pipeline-definition must flow from engineer to steward."""
        assert "pipeline-definition" in engineer["produces"]
        assert "pipeline-definition" in steward["accepts"]

    def test_steward_produces_what_engineer_needs(self, engineer, steward):
        """data-contract must flow from steward back to engineer for execution."""
        assert "data-contract" in steward["produces"]
        # Engineer consumes via data-contract (handoff protocol, not accepts list)

    def test_unique_agent_ids(self, engineer, steward):
        assert engineer["agent_id"] != steward["agent_id"]

    def test_steward_tools_subset_of_engineer(self, engineer, steward):
        """Steward has 4 tools, all of which engineer also has."""
        steward_tools = set(steward["tools"])
        engineer_tools = set(engineer["tools"])
        assert steward_tools.issubset(engineer_tools)
