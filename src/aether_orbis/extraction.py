"""Extraction: evidence-backed entities, relations and claims.

The core never synthesizes knowledge. It accepts candidates from a
:class:`~aether_orbis.ports.KnowledgeExtractor` and keeps only those whose
evidence fragment occurs verbatim in the normalized source
(``extraction-contract.md`` O-3, O-6, escalation rule 2). Extraction quality,
evidence strength and source authority stay three separate characteristics
(O-4): this module writes ``extraction_confidence`` and ``evidence_strength``
and never a generic ``confidence``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from aether_orbis.model import (
    ClaimCandidate,
    EntityCandidate,
    EvidenceCandidate,
    ExtractionCandidates,
    NormalizedSource,
    RelationCandidate,
)

IDENTIFIER = re.compile(r"^[A-Za-z0-9]+(?:[._:-][A-Za-z0-9]+)*$")

EVIDENCE_MISMATCH = "evidence_mismatch"
IDENTIFIER_INVALID = "identifier_invalid"
UNKNOWN_ENTITY = "unknown_entity"


@dataclass(frozen=True)
class DroppedElement:
    """An element removed by verification, kept for telemetry and audit."""

    kind: str
    reason: str
    detail: str


@dataclass
class ExtractionOutcome:
    """Verified ExtractionResult document plus what verification removed."""

    document: dict[str, Any]
    dropped: tuple[DroppedElement, ...] = ()
    error_code: str | None = None

    @property
    def status(self) -> str:
        return self.document["extraction_meta"]["status"]


def extraction_id_for(source: NormalizedSource, extracted_at: str) -> str:
    digest = sha256(f"{source.source_id}\n{extracted_at}".encode("utf-8")).hexdigest()
    return f"ext-{digest[:16]}"


def _evidence_document(
    source: NormalizedSource, evidence: EvidenceCandidate
) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "fragment": evidence.fragment,
        "retrieved_at": source.retrieved_at,
        "evidence_strength": evidence.evidence_strength,
    }


def verify_fragment(source: NormalizedSource, fragment: str) -> bool:
    """Return whether *fragment* occurs verbatim in the normalized source."""

    return bool(fragment) and fragment in source.text


def build_extraction_result(
    source: NormalizedSource,
    candidates: ExtractionCandidates,
    *,
    model: str,
    extractor_version: str,
    extracted_at: str,
) -> ExtractionOutcome:
    """Return a verified ExtractionResult for *source*.

    A correctly processed source without extractable elements returns empty
    arrays and ``status: ok``; a partially valid result is ``partial``; an
    extractor that could not produce a contractual result is ``error`` with empty
    arrays (``extraction-contract.md`` O-7).
    """

    dropped: list[DroppedElement] = []
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []

    if not candidates.failed:
        entities = _verified_entities(source, candidates.entities, dropped)
        known_ids = {entity["id"] for entity in entities}
        relations = _verified_relations(source, candidates.relations, known_ids, dropped)
        claims = _verified_claims(source, candidates.claims, known_ids, dropped)

    if candidates.failed:
        status = "error"
    elif dropped:
        status = "partial"
    else:
        status = "ok"

    document = {
        "schema_version": "1.0",
        "extraction_id": extraction_id_for(source, extracted_at),
        "source": source.identity(extractor_version),
        "entities": entities,
        "relations": relations,
        "claims": claims,
        "extraction_meta": {
            "status": status,
            "model": model,
            "operation_role": "extraction",
            "extracted_at": extracted_at,
        },
    }
    return ExtractionOutcome(
        document=document,
        dropped=tuple(dropped),
        error_code=candidates.error_code if candidates.failed else None,
    )


def _drop(
    dropped: list[DroppedElement], kind: str, reason: str, detail: str
) -> None:
    dropped.append(DroppedElement(kind=kind, reason=reason, detail=detail))


def _rejects_evidence(
    source: NormalizedSource,
    dropped: list[DroppedElement],
    kind: str,
    detail: str,
    evidence: EvidenceCandidate,
) -> bool:
    if verify_fragment(source, evidence.fragment):
        return False
    _drop(dropped, kind, EVIDENCE_MISMATCH, detail)
    return True


def _verified_entities(
    source: NormalizedSource,
    candidates: tuple[EntityCandidate, ...],
    dropped: list[DroppedElement],
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for candidate in candidates:
        if not IDENTIFIER.match(candidate.id):
            _drop(dropped, "entity", IDENTIFIER_INVALID, candidate.id)
            continue
        if _rejects_evidence(source, dropped, "entity", candidate.id, candidate.evidence):
            continue
        verified.append(
            {
                "id": candidate.id,
                "type": candidate.type,
                "name": candidate.name,
                "extraction_confidence": candidate.extraction_confidence,
                "evidence": _evidence_document(source, candidate.evidence),
            }
        )
    return verified


def _verified_relations(
    source: NormalizedSource,
    candidates: tuple[RelationCandidate, ...],
    known_ids: set[str],
    dropped: list[DroppedElement],
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for candidate in candidates:
        detail = f"{candidate.subject} {candidate.predicate} {candidate.object}"
        if not known_ids.issuperset({candidate.subject, candidate.object}):
            _drop(dropped, "relation", UNKNOWN_ENTITY, detail)
            continue
        if _rejects_evidence(source, dropped, "relation", detail, candidate.evidence):
            continue
        verified.append(
            {
                "subject": candidate.subject,
                "predicate": candidate.predicate,
                "object": candidate.object,
                "state": candidate.state,
                "extraction_confidence": candidate.extraction_confidence,
                "evidence": _evidence_document(source, candidate.evidence),
            }
        )
    return verified


def _verified_claims(
    source: NormalizedSource,
    candidates: tuple[ClaimCandidate, ...],
    known_ids: set[str],
    dropped: list[DroppedElement],
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for candidate in candidates:
        if not known_ids.issuperset(candidate.entity_ids) or not candidate.entity_ids:
            _drop(dropped, "claim", UNKNOWN_ENTITY, candidate.claim)
            continue
        if _rejects_evidence(source, dropped, "claim", candidate.claim, candidate.evidence):
            continue
        verified.append(
            {
                "claim": candidate.claim,
                "entity_ids": list(candidate.entity_ids),
                "extraction_confidence": candidate.extraction_confidence,
                "evidence": _evidence_document(source, candidate.evidence),
            }
        )
    return verified


def extraction_telemetry(document: dict[str, Any]) -> dict[str, Any]:
    """Return the telemetry ``extraction`` block for an ExtractionResult."""

    elements = document["entities"] + document["relations"] + document["claims"]
    block: dict[str, Any] = {
        "entity_count": len(document["entities"]),
        "relation_count": len(document["relations"]),
        "claim_count": len(document["claims"]),
    }
    if elements:
        block["mean_extraction_confidence"] = _mean(
            element["extraction_confidence"] for element in elements
        )
        block["mean_evidence_strength"] = _mean(
            element["evidence"]["evidence_strength"] for element in elements
        )
    return block


def _mean(values: Any) -> float:
    collected = list(values)
    return round(sum(collected) / len(collected), 6)
