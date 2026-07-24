"""
Qdrant Semantic Lineage Writer.

Writes lineage events to a Qdrant collection with vector embeddings
for semantic search (e.g. "show everything derived from customer table").

Uses a deterministic hash-based embedding for now — real embedding model
integration deferred to production deployment.
"""

import hashlib
import logging
import struct
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

# Collection for data lineage events — separate from conductor memory collections
COLLECTION_NAME = "data_lineage"

# Vector dimension for hash-based embeddings
VECTOR_DIM = 128

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1  # 1s, 3s, 9s


@dataclass
class QdrantWriteResult:
    """Result of a Qdrant write operation."""
    point_id: str
    collection: str
    success: bool
    error: Optional[str] = None


def _generate_embedding(text: str) -> list[float]:
    """
    Generate a deterministic embedding vector from text using SHA-512
    hashing. This produces a consistent 128-dimensional float vector
    suitable for cosine similarity search.

    In production, this would be replaced by a real embedding model
    (e.g. nomic-embed-text via Ollama or OpenAI embeddings).
    """
    # Hash the text with SHA-512 to get 64 bytes
    h = hashlib.sha512(text.encode("utf-8")).digest()
    # Extend to 128 floats by double-hashing
    h2 = hashlib.sha512(h).digest()
    raw_bytes = h + h2  # 128 bytes
    # Convert each byte pair to a float in [-1, 1] range
    vec = []
    for i in range(VECTOR_DIM):
        # Use pairs of bytes to get 16-bit values
        val = struct.unpack("B", raw_bytes[i : i + 1])[0]
        # Normalize to [-1, 1]
        vec.append((val / 127.5) - 1.0)
    # Normalize the vector to unit length for cosine similarity
    magnitude = sum(v * v for v in vec) ** 0.5
    if magnitude > 0:
        vec = [v / magnitude for v in vec]
    return vec


def _event_to_description(event: dict) -> str:
    """
    Build a searchable description string from a lineage event.
    Includes operation, source, target, classification, and
    transformation metadata. Never includes actual data values.
    """
    ev = event.get("event", event)
    parts = [
        f"operation:{ev.get('operation', 'unknown')}",
        f"pipeline:{ev.get('pipeline_id', 'unknown')}",
        f"classification:{ev.get('gov_classification', 'unknown')}",
    ]
    source = ev.get("source", {})
    if source:
        parts.append(f"source_connector:{source.get('connector', '')}")
        parts.append(f"source_table:{source.get('table', '')}")
        cols = source.get("columns", [])
        if cols:
            parts.append(f"source_columns:{','.join(cols)}")
    target = ev.get("target", {})
    if target:
        parts.append(f"target_connector:{target.get('connector', '')}")
        parts.append(f"target_table:{target.get('table', '')}")
        parts.append(f"target_tier:{target.get('tier', '')}")
    transformation = ev.get("transformation", {})
    if transformation:
        parts.append(f"transform_type:{transformation.get('type', '')}")
        strategy_map = transformation.get("strategy_map", {})
        if strategy_map:
            strategies = ",".join(f"{k}={v}" for k, v in strategy_map.items())
            parts.append(f"strategies:{strategies}")
    return " ".join(parts)


def _point_id_from_hash(content_hash: str) -> str:
    """
    Generate a deterministic UUID from the content_hash field.
    Same content_hash always maps to the same point ID, enabling
    idempotent upserts.
    """
    # Hash the content_hash string to get a stable 32 hex-char UUID input.
    # MD5 used for content fingerprinting (deterministic UUID generation), not security.
    # Changing to SHA-256 would break existing Qdrant point IDs.
    digest = hashlib.md5(content_hash.encode("utf-8")).hexdigest()  # noqa: S324 — content fingerprinting, not cryptographic security
    return str(uuid.UUID(digest))


class QdrantLineageWriter:
    """
    Writes lineage events to a Qdrant collection with vector
    embeddings for semantic search capability.
    """

    def __init__(self, client: Optional[QdrantClient] = None, url: Optional[str] = None):
        """
        Initialize the Qdrant writer.

        Args:
            client: Pre-configured QdrantClient (used in tests with :memory: mode).
            url: Qdrant server URL. Ignored if client is provided.
        """
        if client is not None:
            self._client = client
        elif url:
            self._client = QdrantClient(url=url)
        else:
            # Default: in-memory for development/testing
            self._client = QdrantClient(location=":memory:")

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create the data_lineage collection if it does not exist."""
        collections = self._client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qmodels.VectorParams(
                    size=VECTOR_DIM,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", COLLECTION_NAME)

    def write(self, event: dict) -> QdrantWriteResult:
        """
        Write a lineage event to Qdrant with retry on connection failure.

        Args:
            event: Validated lineage event dict (with 'event' wrapper).

        Returns:
            QdrantWriteResult with point_id and success status.

        Raises:
            Exception: If all retry attempts fail.
        """
        ev = event.get("event", event)
        content_hash = ev.get("content_hash", "")
        point_id = _point_id_from_hash(content_hash)
        description = _event_to_description(event)
        vector = _generate_embedding(description)

        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                self._client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        qmodels.PointStruct(
                            id=point_id,
                            vector=vector,
                            payload={
                                "event": ev,
                                "description": description,
                                "content_hash": content_hash,
                                "pipeline_id": ev.get("pipeline_id", ""),
                                "operation": ev.get("operation", ""),
                                "gov_classification": ev.get("gov_classification", ""),
                                "gov_timestamp": ev.get("gov_timestamp", ""),
                                "source_table": ev.get("source", {}).get("table", ""),
                                "target_table": ev.get("target", {}).get("table", ""),
                                "target_tier": ev.get("target", {}).get("tier", ""),
                            },
                        )
                    ],
                )
                logger.info(
                    "Wrote lineage event to Qdrant: point_id=%s pipeline=%s op=%s",
                    point_id,
                    ev.get("pipeline_id"),
                    ev.get("operation"),
                )
                return QdrantWriteResult(
                    point_id=point_id,
                    collection=COLLECTION_NAME,
                    success=True,
                )
            except Exception as exc:
                last_error = exc
                backoff = BACKOFF_BASE_SECONDS * (3 ** attempt)
                logger.warning(
                    "Qdrant write attempt %d/%d failed: %s. Retrying in %ds.",
                    attempt + 1,
                    MAX_RETRIES,
                    str(exc),
                    backoff,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)

        error_msg = f"Qdrant write failed after {MAX_RETRIES} attempts: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def search_semantic(self, query_text: str, limit: int = 10) -> list[dict]:
        """
        Search lineage events by semantic similarity.

        Args:
            query_text: Natural language query.
            limit: Maximum results to return.

        Returns:
            List of matching event payloads with scores.
        """
        vector = _generate_embedding(query_text)
        results = self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=limit,
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results.points
        ]

    def search_by_filter(
        self,
        pipeline_id: Optional[str] = None,
        operation: Optional[str] = None,
        gov_classification: Optional[str] = None,
        source_table: Optional[str] = None,
        target_tier: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Search lineage events by exact payload filters.

        Args:
            pipeline_id: Filter by pipeline ID.
            operation: Filter by operation type.
            gov_classification: Filter by classification level.
            source_table: Filter by source table name.
            target_tier: Filter by target tier.
            limit: Maximum results to return.

        Returns:
            List of matching event payloads.
        """
        conditions = []
        if pipeline_id:
            conditions.append(
                qmodels.FieldCondition(
                    key="pipeline_id",
                    match=qmodels.MatchValue(value=pipeline_id),
                )
            )
        if operation:
            conditions.append(
                qmodels.FieldCondition(
                    key="operation",
                    match=qmodels.MatchValue(value=operation),
                )
            )
        if gov_classification:
            conditions.append(
                qmodels.FieldCondition(
                    key="gov_classification",
                    match=qmodels.MatchValue(value=gov_classification),
                )
            )
        if source_table:
            conditions.append(
                qmodels.FieldCondition(
                    key="source_table",
                    match=qmodels.MatchValue(value=source_table),
                )
            )
        if target_tier:
            conditions.append(
                qmodels.FieldCondition(
                    key="target_tier",
                    match=qmodels.MatchValue(value=target_tier),
                )
            )

        if not conditions:
            # No filters — scroll all points
            result = self._client.scroll(
                collection_name=COLLECTION_NAME,
                limit=limit,
            )
            points = result[0]
        else:
            result = self._client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=qmodels.Filter(must=conditions),
                limit=limit,
            )
            points = result[0]

        return [
            {
                "id": str(p.id),
                "payload": p.payload,
            }
            for p in points
        ]
