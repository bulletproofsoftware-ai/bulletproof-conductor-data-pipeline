"""Presidio analyzer client contract for the masking engine.

This module defines the **interface** the masking-engine service exposes for
named-entity (PII) detection, plus the small data type it returns. It is the
contract that :class:`gates.pii_validator.PIIValidator` codes against via
dependency injection — the validator receives *a* ``BasePresidioClient`` and
only calls :meth:`BasePresidioClient.analyze`, reading
:attr:`RecognizedEntity.entity_type` and :attr:`RecognizedEntity.score` off the
returned entities.

Two things live here:

* :class:`RecognizedEntity` — the detected-entity data type (mirrors the shape
  of Microsoft Presidio's ``RecognizerResult``: entity type, character span,
  and confidence score).
* :class:`BasePresidioClient` — the abstract client contract. The **concrete**
  implementation (a real Presidio ``AnalyzerEngine`` wrapper backed by spaCy
  models) is provided by the masking-engine FastAPI service at runtime and
  built into that service's container image; it is intentionally not vendored
  into this published tree so that importing / testing the pipeline gates does
  not require the heavy Presidio + model dependencies.

:class:`MockPresidioClient` is a lightweight, dependency-free implementation of
the contract used by the test suite (and usable for local dry-runs) that
recognises a couple of common entity types with simple heuristics.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class RecognizedEntity:
    """A single PII entity detected in a piece of text.

    Mirrors the fields of Microsoft Presidio's ``RecognizerResult`` that the
    pipeline consumes.

    Attributes:
        entity_type: The Presidio entity label, e.g. ``"PERSON"``, ``"EMAIL"``,
            ``"US_SSN"``, ``"PHONE_NUMBER"``.
        start: Start character offset of the entity within the analysed text.
        end: End character offset (exclusive) of the entity within the text.
        score: Detection confidence in the ``[0.0, 1.0]`` range. The validator
            filters entities below its configured confidence threshold.
    """

    entity_type: str
    start: int = 0
    end: int = 0
    score: float = 1.0


class BasePresidioClient(ABC):
    """Abstract Presidio analyzer client — the PII-detection contract.

    Concrete implementations wrap a Presidio ``AnalyzerEngine`` (the real one
    ships inside the masking-engine service container). Consumers such as
    :class:`gates.pii_validator.PIIValidator` depend only on this interface and
    receive a concrete client via constructor injection, so they can run
    against either the real analyzer or a test double.
    """

    @abstractmethod
    def analyze(
        self,
        text: str,
        language: str = "en",
        entities: Optional[list[str]] = None,
    ) -> list[RecognizedEntity]:
        """Analyze ``text`` and return the PII entities detected in it.

        Args:
            text: The value to scan for PII.
            language: ISO language code passed through to the analyzer.
            entities: Optional allow-list of entity types to detect; ``None``
                means detect all supported types.

        Returns:
            A list of :class:`RecognizedEntity` (empty if no PII is found).
        """
        raise NotImplementedError


# --- Simple heuristics used by the dependency-free mock client ---------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
# A person name: two or more capitalised words (e.g. "John Doe"). Deliberately
# conservative so that masked tokens like "NAME_a1b2c3" are NOT matched.
_PERSON_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


class MockPresidioClient(BasePresidioClient):
    """Dependency-free :class:`BasePresidioClient` for tests and dry-runs.

    Detects a handful of common entity types (``EMAIL``, ``US_SSN``,
    ``PHONE_NUMBER``, ``PERSON``) using regular expressions. It intentionally
    does **not** flag masked tokens (``NAME_...``, ``EMAIL_...``, ``TOK-...``)
    or redacted placeholders. This is not a substitute for the real Presidio
    analyzer — it exists so the pipeline's PII validator can be exercised
    without the masking-engine service's model dependencies.
    """

    def __init__(self, default_score: float = 0.95) -> None:
        self._default_score = default_score

    def analyze(
        self,
        text: str,
        language: str = "en",
        entities: Optional[list[str]] = None,
    ) -> list[RecognizedEntity]:
        if not text or not isinstance(text, str):
            return []

        found: list[RecognizedEntity] = []

        for match in _EMAIL_RE.finditer(text):
            found.append(
                RecognizedEntity(
                    entity_type="EMAIL",
                    start=match.start(),
                    end=match.end(),
                    score=self._default_score,
                )
            )
        for match in _SSN_RE.finditer(text):
            found.append(
                RecognizedEntity(
                    entity_type="US_SSN",
                    start=match.start(),
                    end=match.end(),
                    score=self._default_score,
                )
            )
        for match in _PHONE_RE.finditer(text):
            # Avoid double-flagging an SSN as a phone number.
            if _SSN_RE.match(text[match.start():match.end()]):
                continue
            found.append(
                RecognizedEntity(
                    entity_type="PHONE_NUMBER",
                    start=match.start(),
                    end=match.end(),
                    score=self._default_score,
                )
            )
        for match in _PERSON_RE.finditer(text):
            found.append(
                RecognizedEntity(
                    entity_type="PERSON",
                    start=match.start(),
                    end=match.end(),
                    score=self._default_score,
                )
            )

        if entities is not None:
            allowed = set(entities)
            found = [e for e in found if e.entity_type in allowed]

        return found
