"""
Conductor Data Pipeline -- Agent Definitions & Handoff Protocol.

Provides YAML-based agent definitions for conductor-data-engineer (Agent 15)
and conductor-data-steward (Agent 16), handoff routes between data agents and
existing roster, workflow phase definitions, classification pattern matching,
and existing agent data awareness updates.

Spec references: SPEC.md Sections 4.1, 4.2, 4.3, 8.1, 8.4
Requirements: REQ-DP-017, REQ-DP-018, REQ-DP-029, REQ-DP-030
"""

import re
from pathlib import Path
from typing import Any, Optional

import yaml


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

AGENTS_DIR = Path(__file__).resolve().parent

ENGINEER_YAML = AGENTS_DIR / "conductor-data-engineer.yaml"
STEWARD_YAML = AGENTS_DIR / "conductor-data-steward.yaml"
HANDOFF_YAML = AGENTS_DIR / "handoff-protocol.yaml"
WORKFLOW_YAML = AGENTS_DIR / "workflow-phases.yaml"
EXISTING_UPDATES_YAML = AGENTS_DIR / "existing-agent-updates.yaml"
CLASSIFICATION_PATTERNS_YAML = AGENTS_DIR / "classification-patterns.yaml"


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """Load and parse a YAML file. Raises FileNotFoundError if missing."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Agent definition loaders
# ---------------------------------------------------------------------------

def load_agent_definition(agent_name: str) -> dict:
    """
    Load a single agent definition by name.

    Args:
        agent_name: Either 'conductor-data-engineer' or 'conductor-data-steward'.

    Returns:
        Parsed YAML dict for the agent definition.

    Raises:
        ValueError: If agent_name is not a recognized data agent.
        FileNotFoundError: If the YAML file is missing.
    """
    mapping = {
        "conductor-data-engineer": ENGINEER_YAML,
        "conductor-data-steward": STEWARD_YAML,
    }
    if agent_name not in mapping:
        raise ValueError(
            f"Unknown agent '{agent_name}'. "
            f"Valid agents: {sorted(mapping.keys())}"
        )
    return _load_yaml(mapping[agent_name])


def load_all_agent_definitions() -> dict[str, dict]:
    """
    Load both data agent definitions.

    Returns:
        Dict mapping agent name to its parsed YAML definition.
    """
    return {
        "conductor-data-engineer": _load_yaml(ENGINEER_YAML),
        "conductor-data-steward": _load_yaml(STEWARD_YAML),
    }


# ---------------------------------------------------------------------------
# Required field validation
# ---------------------------------------------------------------------------

REQUIRED_AGENT_FIELDS = [
    "name",
    "model",
    "role",
    "accepts",
    "produces",
    "requires",
    "constraints",
    "intent_constraints",
]


def validate_agent_definition(definition: dict) -> list[str]:
    """
    Validate that an agent definition has all required fields.

    Args:
        definition: Parsed agent definition dict.

    Returns:
        List of error messages. Empty list means valid.
    """
    errors = []
    for field in REQUIRED_AGENT_FIELDS:
        if field not in definition:
            errors.append(f"Missing required field: {field}")
        elif field in ("accepts", "produces", "requires", "constraints", "intent_constraints"):
            val = definition[field]
            if not isinstance(val, list):
                errors.append(f"Field '{field}' must be a list, got {type(val).__name__}")
            elif len(val) == 0:
                errors.append(f"Field '{field}' must not be empty")

    # Validate model format
    if "model" in definition:
        model = definition["model"]
        if not isinstance(model, str) or len(model) == 0:
            errors.append("Field 'model' must be a non-empty string")

    return errors


# ---------------------------------------------------------------------------
# Handoff protocol loaders
# ---------------------------------------------------------------------------

def load_handoff_protocol() -> dict:
    """
    Load the handoff protocol definition.

    Returns:
        Parsed YAML dict with routes, artifact_type_registry, and validation_rules.
    """
    return _load_yaml(HANDOFF_YAML)


def get_handoff_routes() -> list[dict]:
    """
    Get all handoff routes from the protocol.

    Returns:
        List of route dicts.
    """
    protocol = load_handoff_protocol()
    return protocol.get("routes", [])


def get_artifact_type_registry() -> list[dict]:
    """
    Get the artifact type registry from the handoff protocol.

    Returns:
        List of artifact type dicts.
    """
    protocol = load_handoff_protocol()
    return protocol.get("artifact_type_registry", [])


def validate_handoff_route(route: dict, agents: dict[str, dict]) -> list[str]:
    """
    Validate a single handoff route against agent definitions.

    Checks that source.produces contains the artifact_type and
    target.accepts contains the artifact_type.

    Args:
        route: A single handoff route dict.
        agents: Dict mapping agent name to its definition.

    Returns:
        List of error messages. Empty means valid.
    """
    errors = []

    source_name = route.get("source")
    target_name = route.get("target")
    artifact_type = route.get("artifact_type")

    # Direct tool calls and return routes skip standard agent validation.
    # Return routes (e.g. steward returning data-contract to engineer for
    # execution) are response flows, not new work handoffs.
    if route.get("direction") in ("direct", "return"):
        return errors

    if source_name and source_name in agents:
        source_def = agents[source_name]
        produces = source_def.get("produces", [])
        if artifact_type and artifact_type not in produces:
            errors.append(
                f"Route {route.get('id')}: source '{source_name}' does not "
                f"produce '{artifact_type}'. Produces: {produces}"
            )

    if target_name and target_name in agents:
        target_def = agents[target_name]
        accepts = target_def.get("accepts", [])
        if artifact_type and artifact_type not in accepts:
            errors.append(
                f"Route {route.get('id')}: target '{target_name}' does not "
                f"accept '{artifact_type}'. Accepts: {accepts}"
            )

    return errors


def detect_handoff_cycles(routes: list[dict]) -> list[list[str]]:
    """
    Detect circular dependencies in the handoff route graph.

    Builds a directed graph from routes and uses DFS to find cycles.

    Args:
        routes: List of handoff route dicts.

    Returns:
        List of cycles found. Each cycle is a list of agent names.
        Empty list means no cycles (valid DAG).
    """
    # Build adjacency list from forward-only routes.
    # Direct (tool calls) and return (response flows) routes are excluded
    # because they don't represent new work handoffs that could form cycles.
    graph: dict[str, list[str]] = {}
    for route in routes:
        if route.get("direction") in ("direct", "return"):
            continue
        source = route.get("source")
        target = route.get("target")
        if source and target:
            graph.setdefault(source, []).append(target)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    all_nodes = set(graph.keys())
    for targets in graph.values():
        all_nodes.update(targets)
    for node in all_nodes:
        color[node] = WHITE

    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, []):
            if color[neighbor] == GRAY:
                # Found a cycle: extract from where neighbor appears in path
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif color[neighbor] == WHITE:
                dfs(neighbor)
        path.pop()
        color[node] = BLACK

    for node in all_nodes:
        if color[node] == WHITE:
            dfs(node)

    return cycles


# ---------------------------------------------------------------------------
# Workflow phase loaders
# ---------------------------------------------------------------------------

def load_workflow_phases() -> dict:
    """
    Load workflow phase definitions.

    Returns:
        Parsed YAML dict with phases, ordering, activation, and tier definitions.
    """
    return _load_yaml(WORKFLOW_YAML)


def get_phases() -> list[dict]:
    """
    Get the ordered list of data pipeline workflow phases.

    Returns:
        List of phase dicts sorted by order field.
    """
    data = load_workflow_phases()
    phases = data.get("phases", [])
    return sorted(phases, key=lambda p: p.get("order", 0))


def is_phase_active(tier: str, data_required: bool) -> bool:
    """
    Determine whether data pipeline phases should be activated.

    Phases activate for STANDARD+ tier tasks that require data.

    Args:
        tier: Task tier (BASIC, STANDARD, COMPLEX, ENTERPRISE).
        data_required: Whether the task requires data extraction/transformation.

    Returns:
        True if data pipeline phases should be activated.
    """
    if not data_required:
        return False

    data = load_workflow_phases()
    tier_defs = data.get("tier_definitions", {})
    tier_upper = tier.upper()
    tier_config = tier_defs.get(tier_upper, {})
    return tier_config.get("data_phases_enabled", False)


# ---------------------------------------------------------------------------
# Existing agent updates
# ---------------------------------------------------------------------------

def load_existing_agent_updates() -> dict:
    """
    Load the existing agent data awareness updates.

    Returns:
        Parsed YAML dict with update entries for existing agents.
    """
    return _load_yaml(EXISTING_UPDATES_YAML)


def get_agent_readable_artifacts(agent_name: str) -> list[str]:
    """
    Get the new readable artifact types for an existing agent.

    Args:
        agent_name: Name of an existing agent (e.g. 'conductor-ciso').

    Returns:
        List of new artifact type names the agent can read.
        Empty list if agent has no data awareness updates.
    """
    data = load_existing_agent_updates()
    for update in data.get("updates", []):
        if update.get("agent") == agent_name:
            return update.get("new_readable_artifacts", [])
    return []


# ---------------------------------------------------------------------------
# Classification pattern matching
# ---------------------------------------------------------------------------

def load_classification_patterns() -> dict:
    """
    Load classification patterns.

    Returns:
        Parsed YAML dict with patterns and metadata.
    """
    return _load_yaml(CLASSIFICATION_PATTERNS_YAML)


def get_patterns() -> list[dict]:
    """
    Get all classification patterns.

    Returns:
        List of pattern dicts.
    """
    data = load_classification_patterns()
    return data.get("patterns", [])


def _pattern_to_regex(pattern: str) -> str:
    """
    Convert a classification pattern to a regex string.

    Patterns use glob-like syntax:
    - '*' matches any sequence of characters (within a segment)
    - '*.' prefix matches any table prefix (e.g. '*.email' matches 'customers.email')
    - '*_id' suffix matches columns ending in _id

    Args:
        pattern: Glob-like pattern string.

    Returns:
        Regex pattern string.
    """
    # Escape regex special chars except * and .
    escaped = ""
    for ch in pattern:
        if ch == "*":
            escaped += ".*"
        elif ch in r"\+?^${}()|[]":
            escaped += "\\" + ch
        else:
            escaped += ch
    return f"^{escaped}$"


def classify_column(column_name: str, patterns: Optional[list[dict]] = None) -> Optional[dict]:
    """
    Classify a column name against the pattern registry.

    Tries each pattern in order. First match wins. Returns None if no pattern matches.

    Args:
        column_name: Fully qualified column name (e.g. 'customers.email').
        patterns: Optional list of patterns to match against. If None, loads from YAML.

    Returns:
        Dict with classification, pii, and optional pii_type. None if no match.
    """
    if patterns is None:
        patterns = get_patterns()

    for pat in patterns:
        pat_str = pat["pattern"]
        regex = _pattern_to_regex(pat_str)
        if re.match(regex, column_name, re.IGNORECASE):
            result: dict[str, Any] = {
                "classification": pat["classification"],
                "pii": pat["pii"],
            }
            if pat.get("pii_type"):
                result["pii_type"] = pat["pii_type"]
            return result

    return None


def classify_columns(column_names: list[str], patterns: Optional[list[dict]] = None) -> dict[str, Optional[dict]]:
    """
    Classify multiple columns against the pattern registry.

    Args:
        column_names: List of fully qualified column names.
        patterns: Optional patterns list. Loaded from YAML if None.

    Returns:
        Dict mapping column name to classification result (or None if unmatched).
    """
    if patterns is None:
        patterns = get_patterns()
    return {col: classify_column(col, patterns) for col in column_names}


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "AGENTS_DIR",
    "ENGINEER_YAML",
    "STEWARD_YAML",
    "HANDOFF_YAML",
    "WORKFLOW_YAML",
    "EXISTING_UPDATES_YAML",
    "CLASSIFICATION_PATTERNS_YAML",
    "REQUIRED_AGENT_FIELDS",
    # Agent loaders
    "load_agent_definition",
    "load_all_agent_definitions",
    "validate_agent_definition",
    # Handoff
    "load_handoff_protocol",
    "get_handoff_routes",
    "get_artifact_type_registry",
    "validate_handoff_route",
    "detect_handoff_cycles",
    # Workflow
    "load_workflow_phases",
    "get_phases",
    "is_phase_active",
    # Existing agents
    "load_existing_agent_updates",
    "get_agent_readable_artifacts",
    # Classification
    "load_classification_patterns",
    "get_patterns",
    "classify_column",
    "classify_columns",
]
