"""
Core Lineage Emitter — dual-writes PROV-AGENT events to Qdrant and PostgreSQL.

Classification-aware error handling:
- Confidential/Restricted: BOTH stores must succeed or LineageWriteError raised
  (pipeline blocks — no audit trail for sensitive data is unacceptable).
- Public/Internal: if one store fails, log LINEAGE_GAP warning and continue.

Thread-safe: uses a threading lock for concurrent pipeline operations.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Optional

from jsonschema import validate, Draft202012Validator

from lineage.qdrant_writer import QdrantLineageWriter, QdrantWriteResult
from lineage.pg_writer import PgLineageWriter, PgWriteResult

logger = logging.getLogger(__name__)

# Classifications that require both stores to succeed
SENSITIVE_CLASSIFICATIONS = {"confidential", "restricted"}

# Load schema once at module level
_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "schemas", "lineage-event.schema.json"
)


def _load_schema() -> dict:
    """Load the lineage event JSON schema."""
    with open(_SCHEMA_PATH) as f:
        return json.load(f)


# Eager-load schema at import time — eliminates TOCTOU race on lazy init (C11).
_SCHEMA: dict = _load_schema()


def _get_schema() -> dict:
    """Return the pre-loaded schema."""
    return _SCHEMA


class LineageWriteError(Exception):
    """
    Raised when lineage write fails for Confidential/Restricted data.
    Pipeline MUST block when this is raised.
    """

    def __init__(self, message: str, classification: str, failed_store: str):
        super().__init__(message)
        self.classification = classification
        self.failed_store = failed_store


@dataclass
class EmitResult:
    """Result of an emit operation."""
    success: bool
    qdrant_result: Optional[QdrantWriteResult] = None
    pg_result: Optional[PgWriteResult] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class LineageEmitter:
    """
    Core lineage emitter that validates events and dual-writes to
    Qdrant and PostgreSQL with classification-aware error handling.
    """

    def __init__(
        self,
        qdrant_writer: QdrantLineageWriter,
        pg_writer: PgLineageWriter,
        skip_validation: bool = False,
    ):
        """
        Initialize the emitter.

        Args:
            qdrant_writer: Qdrant lineage writer instance.
            pg_writer: PostgreSQL lineage writer instance.
            skip_validation: Skip JSON schema validation (for testing edge cases).
        """
        self._qdrant = qdrant_writer
        self._pg = pg_writer
        self._skip_validation = skip_validation
        self._lock = threading.Lock()

    def _validate_event(self, event: dict) -> None:
        """
        Validate event against lineage-event.schema.json.

        Raises:
            ValidationError: If the event does not conform to the schema.
        """
        schema = _get_schema()
        validate(instance=event, schema=schema, cls=Draft202012Validator)

    def emit(self, event: dict) -> EmitResult:
        """
        Validate and dual-write a lineage event.

        Thread-safe: acquires a lock for the duration of the write.

        Args:
            event: Lineage event dict conforming to lineage-event.schema.json.

        Returns:
            EmitResult with results from both stores.

        Raises:
            ValidationError: If the event fails schema validation.
            LineageWriteError: If a sensitive event fails to write to either store.
        """
        # Step 1: Validate
        if not self._skip_validation:
            self._validate_event(event)

        ev = event.get("event", event)
        classification = ev.get("gov_classification", "public")
        is_sensitive = classification in SENSITIVE_CLASSIFICATIONS
        pipeline_id = ev.get("pipeline_id", "unknown")
        operation = ev.get("operation", "unknown")

        warnings: list[str] = []
        qdrant_result: Optional[QdrantWriteResult] = None
        pg_result: Optional[PgWriteResult] = None
        qdrant_error: Optional[Exception] = None
        pg_error: Optional[Exception] = None

        # C17 fix: I/O operations (Qdrant write with retry/sleep, PG write) run
        # outside the lock.  The lock only serialises access to shared mutable
        # state; all variables above are local so no lock is needed here.
        # This prevents Qdrant retry back-off from blocking every other pipeline.

        # Step 2: Write to Qdrant
        try:
            qdrant_result = self._qdrant.write(event)
        except Exception as exc:
            qdrant_error = exc
            logger.error(
                "Qdrant write failed for pipeline=%s op=%s classification=%s: %s",
                pipeline_id,
                operation,
                classification,
                str(exc),
            )

        # Step 3: Write to PostgreSQL
        try:
            pg_result = self._pg.write_event(event)
        except Exception as exc:
            pg_error = exc
            logger.error(
                "PG write failed for pipeline=%s op=%s classification=%s: %s",
                pipeline_id,
                operation,
                classification,
                str(exc),
            )

        # Step 4: Classification-aware error handling
        if is_sensitive:
            # Confidential/Restricted: BOTH must succeed
            if qdrant_error:
                raise LineageWriteError(
                    f"Qdrant write failed for {classification} data: {qdrant_error}",
                    classification=classification,
                    failed_store="qdrant",
                )
            if pg_error:
                raise LineageWriteError(
                    f"PostgreSQL write failed for {classification} data: {pg_error}",
                    classification=classification,
                    failed_store="postgresql",
                )
        else:
            # Public/Internal: log LINEAGE_GAP warning if one fails
            if qdrant_error and pg_error:
                # Both failed — even for non-sensitive, this is a serious problem
                msg = (
                    f"LINEAGE_GAP: Both stores failed for pipeline={pipeline_id} "
                    f"op={operation} classification={classification}. "
                    f"Qdrant: {qdrant_error}. PG: {pg_error}."
                )
                logger.warning(msg)
                warnings.append(msg)
            elif qdrant_error:
                msg = (
                    f"LINEAGE_GAP: Qdrant write failed for pipeline={pipeline_id} "
                    f"op={operation} classification={classification}. "
                    f"Continuing with PG only. Error: {qdrant_error}"
                )
                logger.warning(msg)
                warnings.append(msg)
            elif pg_error:
                msg = (
                    f"LINEAGE_GAP: PG write failed for pipeline={pipeline_id} "
                    f"op={operation} classification={classification}. "
                    f"Continuing with Qdrant only. Error: {pg_error}"
                )
                logger.warning(msg)
                warnings.append(msg)

        success = (qdrant_error is None) and (pg_error is None)
        return EmitResult(
            success=success,
            qdrant_result=qdrant_result,
            pg_result=pg_result,
            warnings=warnings,
        )
