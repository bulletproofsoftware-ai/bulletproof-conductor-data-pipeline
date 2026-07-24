"""Gate registry -- registers quality gates and manages conductor-state.json integration.

Registers the POST-DATA-PIPELINE gate with conductor's quality gate system.
Gates are defined with a trigger point, mode (BLOCKING/WARNING), and
an assigned agent. Integration with conductor-state.json updates the
pipeline's quality_gate field with gate results.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default conductor-state.json path
DEFAULT_STATE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "conductor-state.json"
)


class GateMode(str, Enum):
    """Gate enforcement mode."""
    BLOCKING = "blocking"   # Pipeline cannot progress until gate passes
    WARNING = "warning"     # Log warning but allow pipeline to continue


class GateTrigger(str, Enum):
    """When the gate fires in the pipeline lifecycle."""
    PRE_EXTRACT = "pre_extract"
    POST_EXTRACT = "post_extract"
    PRE_TRANSFORM = "pre_transform"
    POST_TRANSFORM = "post_transform"
    PRE_MASK = "pre_mask"
    POST_MASK = "post_mask"
    PRE_LOAD = "pre_load"
    POST_LOAD = "post_load"
    POST_DATA_PIPELINE = "post_data_pipeline"


@dataclass
class GateDefinition:
    """Definition of a registered quality gate."""
    name: str
    description: str
    trigger: GateTrigger
    mode: GateMode
    agent: str
    checks: list[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.value,
            "mode": self.mode.value,
            "agent": self.agent,
            "checks": self.checks,
            "version": self.version,
        }


@dataclass
class GateExecution:
    """Record of a gate execution."""
    gate_name: str
    pipeline_id: str
    executed_at: float
    verdict: str  # "PASS" or "FAIL"
    mode: str
    check_results: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "pipeline_id": self.pipeline_id,
            "executed_at": self.executed_at,
            "verdict": self.verdict,
            "mode": self.mode,
            "check_results": self.check_results,
            "duration_ms": round(self.duration_ms, 2),
        }


class GateRegistry:
    """Registry for quality gates with conductor-state.json integration.

    Manages gate definitions and their execution results. When a gate
    is executed, results are recorded and optionally written to
    conductor-state.json for the conductor agent to read.
    """

    def __init__(self, state_path: Optional[str] = None):
        """Initialize the gate registry.

        Args:
            state_path: Path to conductor-state.json. None disables file writes.
        """
        self._gates: dict[str, GateDefinition] = {}
        self._executions: list[GateExecution] = []
        self._state_path = state_path

    def register(self, gate: GateDefinition) -> None:
        """Register a gate definition.

        Args:
            gate: The gate definition to register.
        """
        self._gates[gate.name] = gate
        logger.info(
            "Registered gate '%s' (trigger=%s, mode=%s, agent=%s)",
            gate.name,
            gate.trigger.value,
            gate.mode.value,
            gate.agent,
        )

    def get(self, name: str) -> Optional[GateDefinition]:
        """Get a gate definition by name."""
        return self._gates.get(name)

    def list_gates(self) -> list[str]:
        """List all registered gate names."""
        return sorted(self._gates.keys())

    def record_execution(
        self,
        gate_name: str,
        pipeline_id: str,
        verdict: str,
        check_results: dict[str, Any],
        duration_ms: float = 0.0,
    ) -> GateExecution:
        """Record a gate execution result.

        Args:
            gate_name: Name of the gate that was executed.
            pipeline_id: Pipeline that was evaluated.
            verdict: "PASS" or "FAIL".
            check_results: Per-check pass/fail results.
            duration_ms: Execution time in milliseconds.

        Returns:
            The recorded GateExecution.
        """
        gate = self._gates.get(gate_name)
        mode = gate.mode.value if gate else "unknown"

        execution = GateExecution(
            gate_name=gate_name,
            pipeline_id=pipeline_id,
            executed_at=time.time(),
            verdict=verdict,
            mode=mode,
            check_results=check_results,
            duration_ms=duration_ms,
        )
        self._executions.append(execution)

        logger.info(
            "Gate '%s' executed for pipeline=%s: verdict=%s (%.2fms)",
            gate_name,
            pipeline_id,
            verdict,
            duration_ms,
        )

        # Update conductor-state.json if path is configured
        if self._state_path is not None:
            self._update_conductor_state(pipeline_id, execution)

        return execution

    def get_executions(
        self,
        gate_name: Optional[str] = None,
        pipeline_id: Optional[str] = None,
    ) -> list[GateExecution]:
        """Get gate execution history, optionally filtered.

        Args:
            gate_name: Filter by gate name.
            pipeline_id: Filter by pipeline ID.

        Returns:
            List of matching GateExecution records.
        """
        results = self._executions
        if gate_name:
            results = [e for e in results if e.gate_name == gate_name]
        if pipeline_id:
            results = [e for e in results if e.pipeline_id == pipeline_id]
        return results

    def is_blocking(self, gate_name: str) -> bool:
        """Check if a gate is in BLOCKING mode.

        Args:
            gate_name: The gate to check.

        Returns:
            True if the gate is BLOCKING.
        """
        gate = self._gates.get(gate_name)
        if gate is None:
            return False
        return gate.mode == GateMode.BLOCKING

    def _update_conductor_state(
        self,
        pipeline_id: str,
        execution: GateExecution,
    ) -> None:
        """Update conductor-state.json with gate results.

        Reads the existing state file (if any), updates the pipeline's
        quality_gate field, and writes back.

        Args:
            pipeline_id: Pipeline to update.
            execution: Gate execution to record.
        """
        state: dict[str, Any] = {}

        # Read existing state
        if self._state_path and os.path.exists(self._state_path):
            try:
                with open(self._state_path, "r") as f:
                    state = json.load(f)
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning(
                    "Could not read conductor-state.json: %s", exc
                )
                state = {}

        # Ensure pipelines dict exists
        if "pipelines" not in state:
            state["pipelines"] = {}

        # Ensure this pipeline exists
        if pipeline_id not in state["pipelines"]:
            state["pipelines"][pipeline_id] = {}

        # Update quality_gate field
        state["pipelines"][pipeline_id]["quality_gate"] = execution.to_dict()

        # Write back atomically: write to temp file then os.replace() (C9 TOCTOU fix)
        try:
            if self._state_path:
                dir_name = os.path.dirname(os.path.abspath(self._state_path))
                fd, tmp_path = tempfile.mkstemp(
                    dir=dir_name, prefix=".conductor-state-", suffix=".tmp"
                )
                try:
                    with os.fdopen(fd, "w") as f:
                        json.dump(state, f, indent=2)
                    os.replace(tmp_path, self._state_path)
                except BaseException:
                    # Clean up temp file on any failure
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise
                logger.info(
                    "Updated conductor-state.json for pipeline=%s gate=%s verdict=%s",
                    pipeline_id,
                    execution.gate_name,
                    execution.verdict,
                )
        except IOError as exc:
            logger.error(
                "Could not write conductor-state.json: %s", exc
            )


def register_post_data_pipeline_gate(
    registry: Optional[GateRegistry] = None,
    state_path: Optional[str] = None,
) -> tuple[GateRegistry, GateDefinition]:
    """Register the POST-DATA-PIPELINE gate with its 6 checks.

    Convenience function that creates a registry (if not provided),
    registers the gate, and returns both.

    Args:
        registry: Existing registry to use. Creates new one if None.
        state_path: Path for conductor-state.json integration.

    Returns:
        Tuple of (registry, gate_definition).
    """
    if registry is None:
        registry = GateRegistry(state_path=state_path)

    gate = GateDefinition(
        name="POST-DATA-PIPELINE",
        description=(
            "Post-pipeline quality gate validating contract coverage, "
            "quality assertions, masking correctness, lineage completeness, "
            "restricted data checks, and referential integrity."
        ),
        trigger=GateTrigger.POST_DATA_PIPELINE,
        mode=GateMode.BLOCKING,
        agent="conductor-data-steward",
        checks=[
            "contract_coverage",
            "quality_assertions",
            "masking_correctness",
            "lineage_completeness",
            "restricted_data_check",
            "referential_integrity",
        ],
        version="1.0.0",
    )

    registry.register(gate)
    return registry, gate
