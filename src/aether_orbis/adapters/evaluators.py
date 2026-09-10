"""Characteristic evaluators.

The acquisition core never invents characteristics: a Research Specification
declares named dimensions and the evaluator supplies a measurement function per
name. ``ConfiguredEvaluator`` also declares which dimensions are cheap enough
for pre-extraction triage; every other dimension is measured only after
extraction, when the material it needs exists.

Nothing here scores "confidence": ``extraction_confidence``,
``evidence_strength`` and ``source_authority`` stay three separate
characteristics with three separate sources of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from aether_orbis.errors import SpecificationError
from aether_orbis.model import Measurement, NormalizedSource

MeasureFn = Callable[[NormalizedSource, dict[str, Any] | None], Measurement]


def constant(score: float, rationale: str) -> MeasureFn:
    """Return a measure that always reports *score* (fixture baselines)."""

    def measure(source: NormalizedSource, extraction: dict[str, Any] | None) -> Measurement:
        return Measurement(score=score, rationale=rationale)

    return measure


def keyword_coverage(keywords: tuple[str, ...]) -> MeasureFn:
    """Measure which share of *keywords* the normalized text mentions."""

    def measure(source: NormalizedSource, extraction: dict[str, Any] | None) -> Measurement:
        if not keywords:
            return Measurement(score=0.0, rationale="No keywords declared for this dimension.")
        lowered = source.text.lower()
        hit = tuple(keyword for keyword in keywords if keyword.lower() in lowered)
        score = round(len(hit) / len(keywords), 6)
        rationale = (
            f"Matched {len(hit)} of {len(keywords)} declared keywords: "
            f"{', '.join(hit) if hit else 'none'}."
        )
        return Measurement(score=score, rationale=rationale)

    return measure


def metadata_score(
    authority_by_host: Mapping[str, float], default: float = 0.3
) -> MeasureFn:
    """Measure the authority of the publishing host from a declared table.

    Source authority is a property of the origin, so it deliberately ignores how
    confident extraction was and how strong the quoted fragments are.
    """

    def measure(source: NormalizedSource, extraction: dict[str, Any] | None) -> Measurement:
        host = source.canonical_url.split("//", 1)[-1].split("/", 1)[0]
        score = authority_by_host.get(host)
        if score is None:
            return Measurement(
                score=default,
                rationale=f"Host {host} is not in the declared authority table; default applied.",
            )
        return Measurement(score=score, rationale=f"Host {host} has declared authority {score}.")

    return measure


def mean_extraction_confidence(default: float = 0.0) -> MeasureFn:
    """Measure how sure the extractor was, averaged over produced elements."""

    def measure(source: NormalizedSource, extraction: dict[str, Any] | None) -> Measurement:
        scores = _element_scores(extraction, "extraction_confidence")
        if not scores:
            return Measurement(
                score=default,
                rationale="Extraction produced no elements to average.",
            )
        score = round(sum(scores) / len(scores), 6)
        return Measurement(
            score=score,
            rationale=f"Mean extraction_confidence over {len(scores)} extracted elements.",
        )

    return measure


def mean_evidence_strength(default: float = 0.0) -> MeasureFn:
    """Measure how strongly the verified fragments support the extraction."""

    def measure(source: NormalizedSource, extraction: dict[str, Any] | None) -> Measurement:
        scores = _evidence_scores(extraction)
        if not scores:
            return Measurement(
                score=default,
                rationale="Extraction produced no verified evidence fragments.",
            )
        score = round(sum(scores) / len(scores), 6)
        return Measurement(
            score=score,
            rationale=f"Mean evidence_strength over {len(scores)} verified fragments.",
        )

    return measure


def duplicate_independence() -> MeasureFn:
    """Measure independence as "no exact duplicate was detected" (Phase 1).

    Phase 1 detects duplicates only by an identical canonical URL or an exact
    content hash. Semantically similar material is never merged, so it keeps the
    independent score.
    """

    seen: dict[str, tuple[str, str]] = {}

    def measure(source: NormalizedSource, extraction: dict[str, Any] | None) -> Measurement:
        known = seen.get(source.source_id)
        if known is None:
            duplicate = any(
                url == source.canonical_url or digest == source.content_hash
                for url, digest in seen.values()
            )
            seen[source.source_id] = (source.canonical_url, source.content_hash)
        else:
            duplicate = any(
                source_id != source.source_id
                and (url == source.canonical_url or digest == source.content_hash)
                for source_id, (url, digest) in seen.items()
            )
        if duplicate:
            return Measurement(
                score=0.0,
                rationale=(
                    "An exact duplicate (identical canonical URL or content hash) was "
                    "already observed in this run."
                ),
            )
        return Measurement(
            score=1.0,
            rationale="No exact duplicate (canonical URL or content hash) was detected.",
        )

    return measure


def _elements(extraction: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not extraction:
        return []
    return [
        *extraction.get("entities", []),
        *extraction.get("relations", []),
        *extraction.get("claims", []),
    ]


def _element_scores(extraction: dict[str, Any] | None, key: str) -> list[float]:
    return [element[key] for element in _elements(extraction) if key in element]


def _evidence_scores(extraction: dict[str, Any] | None) -> list[float]:
    return [
        element["evidence"]["evidence_strength"]
        for element in _elements(extraction)
        if "evidence" in element
    ]


@dataclass
class ConfiguredEvaluator:
    """Measures declared characteristics with explicitly configured functions."""

    measures: dict[str, MeasureFn] = field(default_factory=dict)
    triage_dimensions: tuple[str, ...] = ()

    def measure(
        self,
        stage: str,
        source: NormalizedSource,
        extraction: dict[str, Any] | None,
        dimensions: tuple[str, ...],
    ) -> dict[str, Measurement]:
        """Return a measurement per characteristic available at *stage*."""

        unknown = sorted(set(dimensions) - set(self.measures))
        if stage == "full" and unknown:
            raise SpecificationError(
                "no measurement function is configured for declared dimensions: "
                + ", ".join(unknown)
            )
        selected = [
            name
            for name in dimensions
            if name in self.measures
            and (stage != "triage" or name in self.triage_dimensions)
        ]
        return {name: self.measures[name](source, extraction) for name in selected}
