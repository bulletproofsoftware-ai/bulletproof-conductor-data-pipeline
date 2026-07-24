"""
PostgreSQL Relational Lineage Writer.

Writes lineage events to PostgreSQL tables for relational DAG
traversal, compliance reporting, and joins against existing
memory_audit / memory_links tables.

For tests: uses an in-memory dict-based store implementing the
same interface (PgLineageWriter protocol). The real asyncpg
implementation is used in production.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PgWriteResult:
    """Result of a PostgreSQL write operation."""
    event_id: str
    success: bool
    error: Optional[str] = None


@dataclass
class DagEdge:
    """A parent-child relationship in the lineage DAG."""
    id: str
    parent_event_id: str
    child_event_id: str
    relationship_type: str
    created_at: str


@dataclass
class ContractVersion:
    """A stored data contract version."""
    id: str
    pipeline_ref: str
    version: int
    contract_yaml: str
    contract_hash: str
    created_at: str


class PgLineageWriter:
    """
    In-memory implementation of the PostgreSQL lineage writer.

    In production, this class would use asyncpg to connect to a real
    PostgreSQL instance. For testing and development, it stores
    everything in Python dicts with the same query interface.

    The interface is kept synchronous for simplicity in the emitter's
    dual-write flow. The production variant would use async methods
    behind an adapter.
    """

    def __init__(self, dsn: Optional[str] = None):
        """
        Initialize the PG writer.

        Args:
            dsn: PostgreSQL connection string. If None, uses in-memory store.
        """
        self._dsn = dsn
        # In-memory storage tables
        self._events: dict[str, dict] = {}
        self._dag: dict[str, DagEdge] = {}
        self._contracts: dict[str, ContractVersion] = {}

    def write_event(self, event: dict) -> PgWriteResult:
        """
        Write a lineage event to the data_lineage_events table.

        Args:
            event: Validated lineage event dict (with 'event' wrapper).

        Returns:
            PgWriteResult with the generated event_id.
        """
        ev = event.get("event", event)
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        row = {
            "id": event_id,
            "pipeline_id": ev["pipeline_id"],
            "operation": ev["operation"],
            "gov_agent_id": ev["gov_agent_id"],
            "gov_session_id": ev["gov_session_id"],
            "gov_classification": ev["gov_classification"],
            "gov_timestamp": ev["gov_timestamp"],
            "source_json": ev.get("source", {}),
            "target_json": ev.get("target", {}),
            "transformation_json": ev.get("transformation"),
            "quality_json": ev.get("quality"),
            "content_hash": ev["content_hash"],
            "created_at": now,
        }
        self._events[event_id] = row

        logger.info(
            "Wrote lineage event to PG: id=%s pipeline=%s op=%s",
            event_id,
            ev["pipeline_id"],
            ev["operation"],
        )
        return PgWriteResult(event_id=event_id, success=True)

    def add_dag_edge(
        self,
        parent_event_id: str,
        child_event_id: str,
        relationship_type: str,
    ) -> str:
        """
        Add an edge to the lineage DAG.

        Args:
            parent_event_id: ID of the parent event.
            child_event_id: ID of the child event.
            relationship_type: One of 'derived_from', 'masked_from', 'loaded_to'.

        Returns:
            The generated edge ID.

        Raises:
            ValueError: If relationship_type is invalid, or parent/child
                        event IDs are not found.
        """
        valid_types = {"derived_from", "masked_from", "loaded_to"}
        if relationship_type not in valid_types:
            raise ValueError(
                f"Invalid relationship_type '{relationship_type}'. "
                f"Must be one of: {valid_types}"
            )
        if parent_event_id not in self._events:
            raise ValueError(f"Parent event not found: {parent_event_id}")
        if child_event_id not in self._events:
            raise ValueError(f"Child event not found: {child_event_id}")

        edge_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        edge = DagEdge(
            id=edge_id,
            parent_event_id=parent_event_id,
            child_event_id=child_event_id,
            relationship_type=relationship_type,
            created_at=now,
        )
        self._dag[edge_id] = edge

        logger.info(
            "Added DAG edge: %s -[%s]-> %s",
            parent_event_id,
            relationship_type,
            child_event_id,
        )
        return edge_id

    def store_contract_version(
        self,
        pipeline_ref: str,
        version: int,
        contract_yaml: str,
        contract_hash: str,
    ) -> str:
        """
        Store a data contract version (immutable — never updated or deleted).

        Args:
            pipeline_ref: Pipeline ID this contract belongs to.
            version: Integer version number (must be >= 1).
            contract_yaml: Full YAML text of the contract.
            contract_hash: SHA-256 hash of the contract content.

        Returns:
            The generated contract version ID.
        """
        contract_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        cv = ContractVersion(
            id=contract_id,
            pipeline_ref=pipeline_ref,
            version=version,
            contract_yaml=contract_yaml,
            contract_hash=contract_hash,
            created_at=now,
        )
        self._contracts[contract_id] = cv

        logger.info(
            "Stored contract version: pipeline=%s v=%d hash=%s",
            pipeline_ref,
            version,
            contract_hash[:16],
        )
        return contract_id

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_event(self, event_id: str) -> Optional[dict]:
        """Retrieve a single lineage event by ID."""
        return self._events.get(event_id)

    def get_events_by_pipeline(self, pipeline_id: str) -> list[dict]:
        """Get all lineage events for a pipeline, sorted by gov_timestamp."""
        events = [
            e for e in self._events.values()
            if e["pipeline_id"] == pipeline_id
        ]
        events.sort(key=lambda e: e["gov_timestamp"])
        return events

    def get_events_by_classification(
        self,
        classifications: list[str],
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> list[dict]:
        """
        Get all events matching given classifications within a time range.

        Args:
            classifications: List of classification levels to match.
            start_time: ISO-format start timestamp (inclusive).
            end_time: ISO-format end timestamp (inclusive).

        Returns:
            List of matching events sorted by gov_timestamp.
        """
        results = []
        for e in self._events.values():
            if e["gov_classification"] not in classifications:
                continue
            ts = e["gov_timestamp"]
            if start_time and ts < start_time:
                continue
            if end_time and ts > end_time:
                continue
            results.append(e)
        results.sort(key=lambda e: e["gov_timestamp"])
        return results

    def get_children(self, event_id: str) -> list[DagEdge]:
        """Get all child edges of an event (forward traversal)."""
        return [
            edge for edge in self._dag.values()
            if edge.parent_event_id == event_id
        ]

    def get_parents(self, event_id: str) -> list[DagEdge]:
        """Get all parent edges of an event (backward traversal)."""
        return [
            edge for edge in self._dag.values()
            if edge.child_event_id == event_id
        ]

    def trace_ancestry(self, event_id: str) -> list[dict]:
        """
        Walk the DAG backward from an event to all ancestors (sources).
        Returns events in traversal order (target first, source last).
        """
        visited = set()
        result = []
        stack = [event_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            event = self._events.get(current)
            if event:
                result.append(event)
            for edge in self.get_parents(current):
                stack.append(edge.parent_event_id)

        return result

    def trace_descendants(self, event_id: str) -> list[dict]:
        """
        Walk the DAG forward from an event to all descendants (targets).
        Returns events in traversal order (source first, target last).
        """
        visited = set()
        result = []
        stack = [event_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            event = self._events.get(current)
            if event:
                result.append(event)
            for edge in self.get_children(current):
                stack.append(edge.child_event_id)

        return result

    def get_events_by_source_table(self, table_name: str) -> list[dict]:
        """Get all events where the source table matches."""
        return [
            e for e in self._events.values()
            if e.get("source_json", {}).get("table") == table_name
        ]

    def get_events_by_target(
        self,
        target_table: Optional[str] = None,
        target_tier: Optional[str] = None,
    ) -> list[dict]:
        """Get events matching target table and/or tier."""
        results = []
        for e in self._events.values():
            tj = e.get("target_json", {})
            if target_table and tj.get("table") != target_table:
                continue
            if target_tier and tj.get("tier") != target_tier:
                continue
            results.append(e)
        return results

    def get_contract_versions(self, pipeline_ref: str) -> list[ContractVersion]:
        """Get all contract versions for a pipeline, sorted by version."""
        versions = [
            cv for cv in self._contracts.values()
            if cv.pipeline_ref == pipeline_ref
        ]
        versions.sort(key=lambda cv: cv.version)
        return versions

    def get_latest_contract(self, pipeline_ref: str) -> Optional[ContractVersion]:
        """Get the latest contract version for a pipeline."""
        versions = self.get_contract_versions(pipeline_ref)
        return versions[-1] if versions else None
