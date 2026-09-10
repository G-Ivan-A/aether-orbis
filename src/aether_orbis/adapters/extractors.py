"""Knowledge extractors.

``DictionaryExtractor`` is deterministic and dependency free: it recognizes
entities from a declared dictionary, proposes a relation when two entities share
a sentence and a predicate marker, and proposes a claim when a sentence carries
a declared claim marker. Every candidate quotes the sentence it came from
verbatim, which lets the core verify evidence instead of trusting the extractor.

An LLM adapter (ScrapeGraphAI, see ADR-001) implements the same port and returns
the same candidate objects, so the verification, scoring and preservation rules
never depend on which extractor produced the candidates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from aether_orbis.model import (
    ClaimCandidate,
    EntityCandidate,
    EvidenceCandidate,
    ExtractionCandidates,
    NormalizedSource,
    RelationCandidate,
)

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")

NEGATIONS = ("не ", "нет ", "not ", "no ", "never ")
UNCERTAINTY = ("возможно", "вероятно", "может", "maybe", "likely", "reportedly")
CONTRADICTION = ("опровергает", "опроверг", "denies", "denied", "refutes")


@dataclass(frozen=True)
class EntityDefinition:
    """One dictionary entry the extractor is able to recognize."""

    id: str
    type: str
    name: str
    aliases: tuple[str, ...] = ()

    @property
    def surface_forms(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_BOUNDARY.split(text) if sentence.strip()]


def _relation_state(sentence: str) -> str:
    lowered = sentence.lower()
    if any(marker in lowered for marker in CONTRADICTION):
        return "CONTRADICTED"
    if any(marker in lowered for marker in UNCERTAINTY):
        return "UNCERTAIN"
    if any(lowered.startswith(marker) or f" {marker}" in lowered for marker in NEGATIONS):
        return "NOT_OBSERVED"
    return "OBSERVED"


@dataclass
class DictionaryExtractor:
    """Deterministic rule based extractor used for offline runs and tests."""

    entities: tuple[EntityDefinition, ...] = ()
    predicates: dict[str, tuple[str, ...]] = field(default_factory=dict)
    claim_markers: tuple[str, ...] = ()
    extractor_version: str = "dictionary-extractor/1.0"
    model: str = "rule-based/dictionary"
    base_confidence: float = 0.8
    fail_on: tuple[str, ...] = ()
    error_code: str = "extraction_failed"

    def extract(self, source: NormalizedSource) -> ExtractionCandidates:
        if any(marker in source.text for marker in self.fail_on):
            return ExtractionCandidates(failed=True, error_code=self.error_code)

        sentences = _sentences(source.text)
        entities: dict[str, EntityCandidate] = {}
        relations: list[RelationCandidate] = []
        claims: list[ClaimCandidate] = []

        for sentence in sentences:
            present = self._present_entities(sentence)
            for definition in present:
                entities.setdefault(
                    definition.id,
                    EntityCandidate(
                        id=definition.id,
                        type=definition.type,
                        name=definition.name,
                        extraction_confidence=self.base_confidence,
                        evidence=EvidenceCandidate(
                            fragment=sentence,
                            evidence_strength=self._evidence_strength(sentence),
                        ),
                    ),
                )
            relations.extend(self._relations(sentence, present))
            claim = self._claim(sentence, present)
            if claim is not None:
                claims.append(claim)

        return ExtractionCandidates(
            entities=tuple(entities.values()),
            relations=tuple(relations),
            claims=tuple(claims),
        )

    def _present_entities(self, sentence: str) -> tuple[EntityDefinition, ...]:
        lowered = sentence.lower()
        return tuple(
            definition
            for definition in self.entities
            if any(form.lower() in lowered for form in definition.surface_forms)
        )

    def _relations(
        self, sentence: str, present: tuple[EntityDefinition, ...]
    ) -> list[RelationCandidate]:
        if len(present) < 2:
            return []
        lowered = sentence.lower()
        found: list[RelationCandidate] = []
        for predicate, markers in self.predicates.items():
            if not any(marker.lower() in lowered for marker in markers):
                continue
            subject, obj = present[0], present[1]
            found.append(
                RelationCandidate(
                    subject=subject.id,
                    predicate=predicate,
                    object=obj.id,
                    state=_relation_state(sentence),
                    extraction_confidence=self.base_confidence,
                    evidence=EvidenceCandidate(
                        fragment=sentence,
                        evidence_strength=self._evidence_strength(sentence),
                    ),
                )
            )
        return found

    def _claim(
        self, sentence: str, present: tuple[EntityDefinition, ...]
    ) -> ClaimCandidate | None:
        lowered = sentence.lower()
        if not any(marker.lower() in lowered for marker in self.claim_markers):
            return None
        return ClaimCandidate(
            claim=sentence,
            entity_ids=tuple(definition.id for definition in present),
            extraction_confidence=self.base_confidence,
            evidence=EvidenceCandidate(
                fragment=sentence,
                evidence_strength=self._evidence_strength(sentence),
            ),
        )

    def _evidence_strength(self, sentence: str) -> float:
        """Score the fragment itself, independently of extraction confidence.

        Evidence strength answers "how much does this fragment support the
        statement", so it depends on the fragment, not on how sure the extractor
        was: hedged wording weakens it, a longer self contained sentence
        strengthens it.
        """

        lowered = sentence.lower()
        strength = 0.5 + min(len(sentence), 200) / 500
        if any(marker in lowered for marker in UNCERTAINTY):
            strength -= 0.25
        return round(max(0.0, min(1.0, strength)), 6)


@dataclass
class FailingExtractor:
    """Extractor that always reports failure (used to exercise error paths)."""

    extractor_version: str = "failing-extractor/1.0"
    model: str = "rule-based/failing"
    error_code: str = "extraction_failed"

    def extract(self, source: NormalizedSource) -> ExtractionCandidates:
        return ExtractionCandidates(failed=True, error_code=self.error_code)
