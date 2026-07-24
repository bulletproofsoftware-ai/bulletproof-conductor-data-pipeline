"""
Test suite for Workflow Phases (TODO-010).

Validates 3 new conductor phases (data-pipeline-design, data-governance-review,
data-pipeline-execute) per SPEC.md Section 8.1.
"""

import pytest

from agents import (
    load_workflow_phases,
    get_phases,
    is_phase_active,
    WORKFLOW_YAML,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workflow():
    """Load workflow phases definition."""
    return load_workflow_phases()


@pytest.fixture
def phases():
    """Get ordered phases list."""
    return get_phases()


# ===================================================================
# YAML LOADING
# ===================================================================

class TestWorkflowLoading:
    """Tests for workflow phases YAML loading."""

    def test_workflow_yaml_exists(self):
        assert WORKFLOW_YAML.exists(), f"Missing: {WORKFLOW_YAML}"

    def test_workflow_parses(self, workflow):
        assert isinstance(workflow, dict)

    def test_has_phases(self, workflow):
        assert "phases" in workflow

    def test_has_ordering(self, workflow):
        assert "ordering" in workflow

    def test_has_activation(self, workflow):
        assert "activation" in workflow

    def test_has_tier_definitions(self, workflow):
        assert "tier_definitions" in workflow


# ===================================================================
# THREE PHASES DEFINED
# ===================================================================

class TestPhaseDefinitions:
    """Tests for the 3 data pipeline phases."""

    def test_three_phases_defined(self, phases):
        assert len(phases) == 3

    def test_phase_ids(self, phases):
        ids = [p["id"] for p in phases]
        assert "data-pipeline-design" in ids
        assert "data-governance-review" in ids
        assert "data-pipeline-execute" in ids

    def test_design_phase(self, phases):
        phase = next(p for p in phases if p["id"] == "data-pipeline-design")
        assert phase["agent"] == "conductor-data-engineer"
        assert phase["gate"] is None
        assert "pipeline-definition" in phase["produces"]

    def test_review_phase(self, phases):
        phase = next(p for p in phases if p["id"] == "data-governance-review")
        assert phase["agent"] == "conductor-data-steward"
        assert phase["gate"]["name"] == "POST-DATA-PIPELINE"
        assert phase["gate"]["mode"] == "BLOCKING"
        assert "data-contract" in phase["produces"]

    def test_execute_phase(self, phases):
        phase = next(p for p in phases if p["id"] == "data-pipeline-execute")
        assert phase["agent"] == "conductor-data-engineer"
        assert phase["gate"]["name"] == "POST-DATA-PIPELINE"
        assert phase["gate"]["mode"] == "BLOCKING"
        assert "extraction-report" in phase["produces"]

    def test_review_phase_human_gate(self, phases):
        phase = next(p for p in phases if p["id"] == "data-governance-review")
        assert phase["human_gate"]["enabled"] is True
        assert phase["human_gate"]["condition"] == "confidential_or_higher"


# ===================================================================
# PHASE ORDERING
# ===================================================================

class TestPhaseOrdering:
    """Tests for phase ordering: design -> review -> execute."""

    def test_order_numbers_sequential(self, phases):
        orders = [p["order"] for p in phases]
        assert orders == [1, 2, 3]

    def test_design_before_review(self, phases):
        design = next(p for p in phases if p["id"] == "data-pipeline-design")
        review = next(p for p in phases if p["id"] == "data-governance-review")
        assert design["order"] < review["order"]

    def test_review_before_execute(self, phases):
        review = next(p for p in phases if p["id"] == "data-governance-review")
        execute = next(p for p in phases if p["id"] == "data-pipeline-execute")
        assert review["order"] < execute["order"]

    def test_ordering_after_architecture(self, workflow):
        ordering = workflow["ordering"]
        assert ordering["after"] == "architecture"

    def test_ordering_before_implementation(self, workflow):
        ordering = workflow["ordering"]
        assert ordering["before"] == "implementation"

    def test_sequence_matches_phase_order(self, workflow):
        ordering = workflow["ordering"]
        expected_sequence = [
            "data-pipeline-design",
            "data-governance-review",
            "data-pipeline-execute",
        ]
        assert ordering["sequence"] == expected_sequence


# ===================================================================
# CONDITIONAL ACTIVATION
# ===================================================================

class TestConditionalActivation:
    """Tests for conditional phase activation on STANDARD+ tier."""

    def test_basic_tier_not_active(self):
        assert is_phase_active("BASIC", data_required=True) is False

    def test_standard_tier_active(self):
        assert is_phase_active("STANDARD", data_required=True) is True

    def test_complex_tier_active(self):
        assert is_phase_active("COMPLEX", data_required=True) is True

    def test_enterprise_tier_active(self):
        assert is_phase_active("ENTERPRISE", data_required=True) is True

    def test_standard_tier_no_data_not_active(self):
        assert is_phase_active("STANDARD", data_required=False) is False

    def test_enterprise_tier_no_data_not_active(self):
        assert is_phase_active("ENTERPRISE", data_required=False) is False

    def test_case_insensitive_tier(self):
        assert is_phase_active("standard", data_required=True) is True
        assert is_phase_active("Standard", data_required=True) is True

    def test_activation_condition(self, workflow):
        activation = workflow["activation"]
        assert activation["condition"] == "data_required"
        assert activation["minimum_tier"] == "STANDARD"

    def test_tier_definitions_complete(self, workflow):
        tier_defs = workflow["tier_definitions"]
        assert "BASIC" in tier_defs
        assert "STANDARD" in tier_defs
        assert "COMPLEX" in tier_defs
        assert "ENTERPRISE" in tier_defs

    def test_basic_disabled(self, workflow):
        assert workflow["tier_definitions"]["BASIC"]["data_phases_enabled"] is False

    def test_standard_enabled(self, workflow):
        assert workflow["tier_definitions"]["STANDARD"]["data_phases_enabled"] is True


# ===================================================================
# PHASE AGENT ASSIGNMENTS
# ===================================================================

class TestPhaseAgentAssignments:
    """Tests for correct agent assignment to phases."""

    def test_design_agent_is_engineer(self, phases):
        phase = next(p for p in phases if p["id"] == "data-pipeline-design")
        assert phase["agent"] == "conductor-data-engineer"

    def test_review_agent_is_steward(self, phases):
        phase = next(p for p in phases if p["id"] == "data-governance-review")
        assert phase["agent"] == "conductor-data-steward"

    def test_execute_agent_is_engineer(self, phases):
        phase = next(p for p in phases if p["id"] == "data-pipeline-execute")
        assert phase["agent"] == "conductor-data-engineer"

    def test_each_phase_has_description(self, phases):
        for phase in phases:
            assert "description" in phase, f"Phase {phase['id']} missing description"
            assert len(phase["description"]) > 10

    def test_each_phase_has_produces(self, phases):
        for phase in phases:
            assert "produces" in phase, f"Phase {phase['id']} missing produces"
            assert isinstance(phase["produces"], list)
            assert len(phase["produces"]) > 0
