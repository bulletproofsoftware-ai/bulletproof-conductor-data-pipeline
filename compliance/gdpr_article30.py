"""
GDPR Article 30 Processing Record Generator.

Maps pipeline lineage fields to Article 30 fields per SPEC Section 13.5:

| Article 30 Field              | Lineage Source                                        |
|-------------------------------|-------------------------------------------------------|
| Controller                    | gov_agent_id (orchestrating agent NHI)                |
| Processor                     | masking-engine container identity                     |
| Processing purposes           | pipeline.metadata.brd_refs -> BRD descriptions        |
| Categories of data subjects   | Source table names + contract classifications          |
| Categories of personal data   | contract.columns[*].pii_type where pii: true          |
| Recipients                    | target.tier + target.connector per pipeline target    |
| Retention periods             | contract.governance.retention_days                    |
| Technical safeguards          | masking_strategy per column + referential_integrity   |

Output: structured dict/JSON suitable for compliance reporting.
Used by conductor-compliance agent via lineage query tool.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Article30Record:
    """A GDPR Article 30(1) processing record derived from pipeline lineage.

    All fields correspond to Article 30(1) sub-paragraphs:
    (a) name and contact details of the controller
    (b) purposes of the processing
    (c) categories of data subjects
    (d) categories of personal data
    (e) categories of recipients
    (f) transfers to third countries (not populated -- out of scope v1)
    (g) envisaged time limits for erasure (retention)
    (h) general description of technical/organisational security measures
    """

    pipeline_id: str
    generated_at: str = ""
    controller: str = ""
    processor: str = ""
    processing_purposes: list[str] = field(default_factory=list)
    categories_of_data_subjects: list[str] = field(default_factory=list)
    categories_of_personal_data: list[str] = field(default_factory=list)
    recipients: list[dict[str, str]] = field(default_factory=list)
    retention_days: Optional[int] = None
    technical_safeguards: list[str] = field(default_factory=list)
    referential_integrity: str = "not_verified"
    completeness_flags: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Return True if all required Article 30 fields are populated."""
        return len(self.completeness_flags) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record for JSON output / compliance reporting."""
        return {
            "pipeline_id": self.pipeline_id,
            "generated_at": self.generated_at,
            "article30_fields": {
                "controller": self.controller,
                "processor": self.processor,
                "processing_purposes": self.processing_purposes,
                "categories_of_data_subjects": self.categories_of_data_subjects,
                "categories_of_personal_data": self.categories_of_personal_data,
                "recipients": self.recipients,
                "retention_days": self.retention_days,
                "technical_safeguards": self.technical_safeguards,
                "referential_integrity": self.referential_integrity,
            },
            "completeness": {
                "is_complete": self.is_complete,
                "missing_fields": self.completeness_flags,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @property
    def record_hash(self) -> str:
        """SHA-256 hash of the record for tamper detection."""
        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


class Article30Generator:
    """Generates GDPR Article 30 processing records from pipeline lineage.

    Takes lineage events, pipeline metadata, and data contracts as inputs
    and produces a structured Article30Record with all required fields mapped.
    """

    # Default processor identity when not available from lineage
    DEFAULT_PROCESSOR = "masking-engine/v1"

    def generate(
        self,
        pipeline_definition: dict[str, Any],
        contract: dict[str, Any],
        lineage_events: list[dict[str, Any]],
        processor_identity: Optional[str] = None,
    ) -> Article30Record:
        """Generate an Article 30 record from pipeline execution data.

        Args:
            pipeline_definition: The pipeline YAML (parsed dict).
            contract: The data contract YAML (parsed dict).
            lineage_events: List of lineage events emitted during execution.
            processor_identity: Override for the processor field.
                Defaults to 'masking-engine/v1'.

        Returns:
            Article30Record with all fields populated from available data.
            Missing data is flagged in completeness_flags.
        """
        record = Article30Record(
            pipeline_id=self._extract_pipeline_id(pipeline_definition),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # (a) Controller -- from lineage gov_agent_id
        record.controller = self._extract_controller(lineage_events)
        if not record.controller:
            record.completeness_flags.append("controller")

        # Processor -- masking-engine container identity
        record.processor = processor_identity or self._extract_processor(
            lineage_events
        )
        if not record.processor:
            record.processor = self.DEFAULT_PROCESSOR

        # (b) Processing purposes -- from pipeline.metadata.brd_refs
        record.processing_purposes = self._extract_purposes(pipeline_definition)
        if not record.processing_purposes:
            record.completeness_flags.append("processing_purposes")

        # (c) Categories of data subjects -- from source tables + contract
        record.categories_of_data_subjects = self._extract_data_subjects(
            pipeline_definition, contract
        )
        if not record.categories_of_data_subjects:
            record.completeness_flags.append("categories_of_data_subjects")

        # (d) Categories of personal data -- from contract columns where pii=true
        record.categories_of_personal_data = self._extract_personal_data_categories(
            contract
        )
        if not record.categories_of_personal_data:
            record.completeness_flags.append("categories_of_personal_data")

        # (e) Recipients -- from pipeline targets
        record.recipients = self._extract_recipients(pipeline_definition)
        if not record.recipients:
            record.completeness_flags.append("recipients")

        # (g) Retention periods -- from contract governance
        record.retention_days = self._extract_retention(contract)
        if record.retention_days is None:
            record.completeness_flags.append("retention_days")

        # (h) Technical safeguards -- from masking strategies + integrity
        record.technical_safeguards = self._extract_safeguards(
            contract, lineage_events
        )
        record.referential_integrity = self._extract_integrity_status(
            lineage_events
        )
        if not record.technical_safeguards:
            record.completeness_flags.append("technical_safeguards")

        logger.info(
            "Article 30 record generated for pipeline %s (complete=%s, gaps=%s)",
            record.pipeline_id,
            record.is_complete,
            record.completeness_flags,
        )

        return record

    def _extract_pipeline_id(self, pipeline_def: dict[str, Any]) -> str:
        """Extract pipeline ID from pipeline definition."""
        metadata = pipeline_def.get("metadata", {})
        return metadata.get("id", "unknown")

    def _extract_controller(self, lineage_events: list[dict[str, Any]]) -> str:
        """Extract controller (gov_agent_id) from lineage events.

        Returns the gov_agent_id from the first event, as the orchestrating
        agent is consistent across a pipeline execution.
        """
        for event in lineage_events:
            ev = event.get("event", event)
            agent_id = ev.get("gov_agent_id")
            if agent_id:
                return agent_id
        return ""

    def _extract_processor(self, lineage_events: list[dict[str, Any]]) -> str:
        """Extract processor identity from masking lineage events.

        Looks for 'mask' operation events to identify the masking engine.
        """
        for event in lineage_events:
            ev = event.get("event", event)
            if ev.get("operation") == "mask":
                # Check for transformation metadata
                transformation = ev.get("transformation", {})
                if transformation:
                    return "masking-engine/v1"
        return self.DEFAULT_PROCESSOR

    def _extract_purposes(self, pipeline_def: dict[str, Any]) -> list[str]:
        """Extract processing purposes from pipeline BRD references."""
        metadata = pipeline_def.get("metadata", {})
        brd_refs = metadata.get("brd_refs", [])
        if brd_refs:
            return [
                f"BRD requirement: {ref}" for ref in brd_refs
            ]
        # Fall back to pipeline name as purpose description
        name = metadata.get("name", "")
        if name:
            return [f"Pipeline: {name}"]
        return []

    def _extract_data_subjects(
        self,
        pipeline_def: dict[str, Any],
        contract: dict[str, Any],
    ) -> list[str]:
        """Extract categories of data subjects from source tables and contract.

        Combines source table names with classification tiers to describe
        the categories of individuals whose data is processed.
        """
        subjects: list[str] = []

        # From pipeline source tables
        source = pipeline_def.get("source", {})
        extraction = source.get("extraction", {})
        tables = extraction.get("tables", [])
        for table_spec in tables:
            table_name = table_spec.get("name", "") if isinstance(table_spec, dict) else str(table_spec)
            if table_name:
                subjects.append(f"Records from table: {table_name}")

        # Enrich from contract columns -- identify unique PII types
        columns = contract.get("columns", {})
        pii_types_seen: set[str] = set()
        for col_name, col_def in columns.items():
            if isinstance(col_def, dict) and col_def.get("pii"):
                pii_type = col_def.get("pii_type", "UNKNOWN")
                table_prefix = col_name.split(".")[0] if "." in col_name else "unknown"
                key = f"{table_prefix}:{pii_type}"
                if key not in pii_types_seen:
                    pii_types_seen.add(key)

        return subjects

    def _extract_personal_data_categories(
        self, contract: dict[str, Any]
    ) -> list[str]:
        """Extract categories of personal data from contract columns.

        Returns unique pii_type values from columns where pii=true.
        """
        columns = contract.get("columns", {})
        pii_types: set[str] = set()

        for col_name, col_def in columns.items():
            if isinstance(col_def, dict) and col_def.get("pii"):
                pii_type = col_def.get("pii_type")
                if pii_type:
                    pii_types.add(pii_type)

        return sorted(pii_types)

    def _extract_recipients(
        self, pipeline_def: dict[str, Any]
    ) -> list[dict[str, str]]:
        """Extract recipient categories from pipeline targets.

        Each target tier + connector represents a recipient category.
        """
        recipients: list[dict[str, str]] = []
        targets = pipeline_def.get("targets", [])

        for target in targets:
            tier = target.get("tier", "unknown")
            connector = target.get("connector", "unknown")
            masking = target.get("masking", "none")
            recipients.append({
                "tier": tier,
                "connector": connector,
                "masking_policy": masking,
            })

        return recipients

    def _extract_retention(self, contract: dict[str, Any]) -> Optional[int]:
        """Extract retention period from contract governance section."""
        governance = contract.get("governance", {})
        retention = governance.get("retention_days")
        if isinstance(retention, int) and retention > 0:
            return retention
        return None

    def _extract_safeguards(
        self,
        contract: dict[str, Any],
        lineage_events: list[dict[str, Any]],
    ) -> list[str]:
        """Extract technical safeguards from masking strategies and lineage.

        Combines:
        - Masking strategies per column from contract classifications
        - Strategy map from mask lineage events
        """
        safeguards: set[str] = set()

        # From lineage events -- look for mask operations with strategy maps
        for event in lineage_events:
            ev = event.get("event", event)
            if ev.get("operation") == "mask":
                transformation = ev.get("transformation", {})
                strategy_map = transformation.get("strategy_map", {})
                for col, strategy in strategy_map.items():
                    safeguards.add(f"{col}: {strategy}")
                integrity = transformation.get("referential_integrity")
                if integrity:
                    safeguards.add(f"referential_integrity: {integrity}")

        # From contract -- infer safeguards from PII classifications
        columns = contract.get("columns", {})
        for col_name, col_def in columns.items():
            if isinstance(col_def, dict):
                classification = col_def.get("classification", "")
                if classification in ("confidential", "restricted"):
                    safeguards.add(
                        f"{col_name}: classification={classification}"
                    )

        return sorted(safeguards)

    def _extract_integrity_status(
        self, lineage_events: list[dict[str, Any]]
    ) -> str:
        """Extract referential integrity status from mask lineage events."""
        for event in lineage_events:
            ev = event.get("event", event)
            if ev.get("operation") == "mask":
                transformation = ev.get("transformation", {})
                status = transformation.get("referential_integrity")
                if status:
                    return status
        return "not_verified"
