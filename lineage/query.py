"""
Lineage Query Engine.

Routes queries to the appropriate store:
- Relational queries (provenance, impact, history) -> PostgreSQL
- Semantic queries ("everything derived from customer table") -> Qdrant

Four query types:
1. trace_provenance: DAG walk from target back to source
2. impact_analysis: Forward walk from source to all targets
3. pii_audit: All Confidential/Restricted events in a time range
4. pipeline_history: All executions for a pipeline, sorted by timestamp
"""

import logging
from dataclasses import dataclass

from lineage.qdrant_writer import QdrantLineageWriter
from lineage.pg_writer import PgLineageWriter

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceResult:
    """Result of a provenance trace query."""
    target_table: str
    target_tier: str
    lineage_chain: list[dict]
    total_events: int


@dataclass
class ImpactResult:
    """Result of an impact analysis query."""
    source_table: str
    affected_targets: list[dict]
    total_affected: int


@dataclass
class PiiAuditResult:
    """Result of a PII audit query."""
    start_time: str
    end_time: str
    events: list[dict]
    total_events: int
    classifications_found: dict[str, int]


@dataclass
class PipelineHistoryResult:
    """Result of a pipeline history query."""
    pipeline_id: str
    executions: list[dict]
    total_executions: int


class LineageQueryEngine:
    """
    Query engine for lineage data. Routes relational queries to PostgreSQL
    and semantic queries to Qdrant.
    """

    def __init__(
        self,
        pg_writer: PgLineageWriter,
        qdrant_writer: QdrantLineageWriter,
    ):
        """
        Initialize the query engine.

        Args:
            pg_writer: PostgreSQL lineage writer (for relational queries).
            qdrant_writer: Qdrant lineage writer (for semantic queries).
        """
        self._pg = pg_writer
        self._qdrant = qdrant_writer

    def trace_provenance(
        self,
        target_table: str,
        target_tier: str,
    ) -> ProvenanceResult:
        """
        Trace provenance: walk the DAG backward from a target to its sources.

        Finds all events where the target matches, then follows parent edges
        to trace back to the original source data.

        Args:
            target_table: Name of the target table.
            target_tier: Tier of the target (e.g. "staging").

        Returns:
            ProvenanceResult with the full lineage chain.
        """
        # Find target events
        target_events = self._pg.get_events_by_target(
            target_table=target_table,
            target_tier=target_tier,
        )

        if not target_events:
            return ProvenanceResult(
                target_table=target_table,
                target_tier=target_tier,
                lineage_chain=[],
                total_events=0,
            )

        # Collect all ancestry for each target event
        all_ancestors = []
        seen_ids = set()

        for te in target_events:
            event_id = te["id"]
            ancestors = self._pg.trace_ancestry(event_id)
            for a in ancestors:
                if a["id"] not in seen_ids:
                    seen_ids.add(a["id"])
                    all_ancestors.append(a)

        # Sort by gov_timestamp to show chronological order
        all_ancestors.sort(key=lambda e: e.get("gov_timestamp", ""))

        return ProvenanceResult(
            target_table=target_table,
            target_tier=target_tier,
            lineage_chain=all_ancestors,
            total_events=len(all_ancestors),
        )

    def impact_analysis(self, source_table: str) -> ImpactResult:
        """
        Impact analysis: forward walk from a source table to all targets.

        Finds all events sourced from the given table, then follows child
        edges to find all downstream targets.

        Args:
            source_table: Name of the source table.

        Returns:
            ImpactResult with all affected downstream targets.
        """
        # Find source events
        source_events = self._pg.get_events_by_source_table(source_table)

        if not source_events:
            return ImpactResult(
                source_table=source_table,
                affected_targets=[],
                total_affected=0,
            )

        # Collect all descendants for each source event
        all_descendants = []
        seen_ids = set()

        for se in source_events:
            event_id = se["id"]
            descendants = self._pg.trace_descendants(event_id)
            for d in descendants:
                if d["id"] not in seen_ids:
                    seen_ids.add(d["id"])
                    all_descendants.append(d)

        # Extract unique target info
        affected = []
        seen_targets = set()
        for d in all_descendants:
            tj = d.get("target_json", {})
            target_key = (tj.get("table", ""), tj.get("tier", ""))
            if target_key not in seen_targets and target_key != ("", ""):
                seen_targets.add(target_key)
                affected.append({
                    "table": tj.get("table"),
                    "tier": tj.get("tier"),
                    "connector": tj.get("connector"),
                    "masking_applied": tj.get("masking_applied"),
                    "event_id": d["id"],
                    "operation": d.get("operation"),
                })

        return ImpactResult(
            source_table=source_table,
            affected_targets=affected,
            total_affected=len(affected),
        )

    def pii_audit(
        self,
        start_time: str,
        end_time: str,
    ) -> PiiAuditResult:
        """
        PII audit: all events with Confidential or Restricted classification
        in the given time range.

        Args:
            start_time: ISO-format start timestamp (inclusive).
            end_time: ISO-format end timestamp (inclusive).

        Returns:
            PiiAuditResult with matching events and classification breakdown.
        """
        events = self._pg.get_events_by_classification(
            classifications=["confidential", "restricted"],
            start_time=start_time,
            end_time=end_time,
        )

        # Count classifications
        classification_counts: dict[str, int] = {}
        for e in events:
            cls = e.get("gov_classification", "unknown")
            classification_counts[cls] = classification_counts.get(cls, 0) + 1

        return PiiAuditResult(
            start_time=start_time,
            end_time=end_time,
            events=events,
            total_events=len(events),
            classifications_found=classification_counts,
        )

    def pipeline_history(self, pipeline_id: str) -> PipelineHistoryResult:
        """
        Pipeline history: all executions for a pipeline, sorted by timestamp.

        Args:
            pipeline_id: Pipeline identifier.

        Returns:
            PipelineHistoryResult with all executions.
        """
        events = self._pg.get_events_by_pipeline(pipeline_id)

        return PipelineHistoryResult(
            pipeline_id=pipeline_id,
            executions=events,
            total_executions=len(events),
        )

    def semantic_search(self, query_text: str, limit: int = 10) -> list[dict]:
        """
        Semantic search over lineage events via Qdrant.

        Args:
            query_text: Natural language query.
            limit: Maximum results.

        Returns:
            List of matching events with scores.
        """
        return self._qdrant.search_semantic(query_text, limit=limit)
