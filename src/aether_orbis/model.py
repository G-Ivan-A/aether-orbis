"""In-memory value objects exchanged between acquisition core stages.

Contract documents (ExtractionResult, EvaluationResult, QualificationDecision,
PreservedRecord, TelemetryEvent) are represented as plain dictionaries so that
they can be validated directly against the executable schemas in
``configs/schemas/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FrontierItem:
    """One unit of work derived from ``specification.scope``.

    ``kind`` follows the strategy: ``item`` for ``enumerate``, ``seed`` for
    ``expand`` and ``query`` for ``query``.
    """

    strategy: str
    kind: str
    value: str
    source_type: str | None = None
    hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class RawMaterial:
    """Material as acquired, before normalization."""

    url: str
    payload: bytes
    media_type: str
    retrieved_at: str
    published_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedSource:
    """Normalized material carrying the mandatory content identity."""

    source_id: str
    source_group_id: str
    canonical_url: str
    content_hash: str
    retrieved_at: str
    published_at: str
    parser_version: str
    media_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def identity(self, extractor_version: str) -> dict[str, Any]:
        """Return the identity block required by extraction and preservation."""

        return {
            "source_id": self.source_id,
            "canonical_url": self.canonical_url,
            "content_hash": self.content_hash,
            "retrieved_at": self.retrieved_at,
            "published_at": self.published_at,
            "parser_version": self.parser_version,
            "extractor_version": extractor_version,
        }


@dataclass(frozen=True)
class EvidenceCandidate:
    """Evidence proposed by an extractor before verbatim verification."""

    fragment: str
    evidence_strength: float


@dataclass(frozen=True)
class EntityCandidate:
    id: str
    type: str
    name: str
    extraction_confidence: float
    evidence: EvidenceCandidate


@dataclass(frozen=True)
class RelationCandidate:
    subject: str
    predicate: str
    object: str
    state: str
    extraction_confidence: float
    evidence: EvidenceCandidate


@dataclass(frozen=True)
class ClaimCandidate:
    claim: str
    entity_ids: tuple[str, ...]
    extraction_confidence: float
    evidence: EvidenceCandidate


@dataclass(frozen=True)
class ExtractionCandidates:
    """Raw extractor output.

    ``failed`` marks an extractor that could not produce a contractual result at
    all; the core then emits ``extraction_meta.status: error`` instead of
    synthesizing elements.
    """

    entities: tuple[EntityCandidate, ...] = ()
    relations: tuple[RelationCandidate, ...] = ()
    claims: tuple[ClaimCandidate, ...] = ()
    failed: bool = False
    error_code: str | None = None


@dataclass(frozen=True)
class Measurement:
    """One measured characteristic of an evaluated material."""

    score: float
    rationale: str


@dataclass(frozen=True)
class MaterialOutcome:
    """Everything the acquisition core produced for a single material."""

    source: NormalizedSource
    triage_evaluation: dict[str, Any]
    record: dict[str, Any]
    triage_decision: dict[str, Any] | None = None
    extraction: dict[str, Any] | None = None
    evaluation: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None

    @property
    def final_decision(self) -> str:
        """Return the decision that qualifies the material.

        A material stopped by triage carries the triage decision; every other
        material carries the decision taken after the full evaluation.
        """

        decision = self.decision or self.triage_decision
        if decision is None:
            raise ValueError(f"material {self.source.source_id} has no decision")
        return decision["decision"]

    @property
    def stopped_at_triage(self) -> bool:
        """Return whether the material never reached extraction."""

        return self.extraction is None
