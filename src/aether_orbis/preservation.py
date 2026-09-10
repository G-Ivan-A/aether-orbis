"""Preservation: what is kept after a material has been acquired.

Preservation is determined only by the Preservation Policy of the Research
Specification — never by the source type and never by the qualification
decision (``preservation-contract.md``, ADR-004). The three dimensions are
independent, the payload must match the declared level exactly, and content
identity survives every combination, including three times ``none`` (O-1, O-2).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from aether_orbis.errors import UnsupportedPreservationError
from aether_orbis.model import NormalizedSource

ARTIFACT_LEVELS = ("none", "metadata", "summary", "evidence_fragments", "full_content")
KNOWLEDGE_LEVELS = ("none", "claims", "claims_and_relations", "full_knowledge_product")
HISTORY_LEVELS = ("none", "latest_only", "full_history")
PHASE_1_HISTORY_LEVELS = ("none", "latest_only")
RISK_LEVELS = ("none", "metadata", "summary")

EMPTY_SUMMARY = "No textual content was retrieved for this source."
SUMMARY_LIMIT = 280


def _check_policy(policy: Mapping[str, Any]) -> None:
    artifact = policy.get("acquired_artifact")
    knowledge = policy.get("derived_knowledge")
    history = policy.get("observation_history")

    for value, allowed, name in (
        (artifact, ARTIFACT_LEVELS, "acquired_artifact"),
        (knowledge, KNOWLEDGE_LEVELS, "derived_knowledge"),
        (history, HISTORY_LEVELS, "observation_history"),
    ):
        if value not in allowed:
            raise UnsupportedPreservationError(
                f"preservation.{name} must be one of {allowed}, got {value!r}"
            )

    if artifact in RISK_LEVELS and policy.get("reproducibility_risk_accepted") is not True:
        raise UnsupportedPreservationError(
            f"acquired_artifact {artifact!r} is below 'evidence_fragments' and requires "
            "reproducibility_risk_accepted: true"
        )
    if artifact == "full_content" and policy.get("profile") != "archival":
        raise UnsupportedPreservationError(
            "acquired_artifact 'full_content' requires profile 'archival'"
        )
    if policy.get("profile") == "archival" and artifact != "full_content":
        raise UnsupportedPreservationError(
            "profile 'archival' requires acquired_artifact 'full_content'"
        )
    if history not in PHASE_1_HISTORY_LEVELS:
        raise UnsupportedPreservationError(
            f"observation_history {history!r} is not executable in Phase 1"
        )


def summarize(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """Return a deterministic summary of the normalized source text."""

    paragraph = next((part.strip() for part in text.split("\n\n") if part.strip()), "")
    if not paragraph:
        return EMPTY_SUMMARY
    collapsed = " ".join(paragraph.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rstrip() + "…"


def evidence_fragments(extraction: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Return the deduplicated evidence fragments of an ExtractionResult."""

    if extraction is None:
        return []
    fragments: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in _elements(extraction):
        evidence = element["evidence"]
        if evidence["fragment"] in seen:
            continue
        seen.add(evidence["fragment"])
        fragments.append(
            {
                "fragment": evidence["fragment"],
                "retrieved_at": evidence["retrieved_at"],
                "evidence_strength": evidence["evidence_strength"],
            }
        )
    return fragments


def _elements(extraction: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    return [*extraction["entities"], *extraction["relations"], *extraction["claims"]]


def _metadata(source: NormalizedSource) -> dict[str, Any]:
    metadata = {
        "canonical_url": source.canonical_url,
        "media_type": source.media_type,
        "published_at": source.published_at,
    }
    metadata.update(source.metadata)
    return metadata


def _acquired_artifact(
    policy: Mapping[str, Any], source: NormalizedSource, extraction: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    level = policy["acquired_artifact"]
    if level == "none":
        return None
    if level == "metadata":
        return {"metadata": _metadata(source)}
    if level == "summary":
        return {"metadata": _metadata(source), "summary": summarize(source.text)}
    if level == "evidence_fragments":
        return {
            "metadata": _metadata(source),
            "summary": summarize(source.text),
            "evidence_fragments": evidence_fragments(extraction),
        }
    return {
        "metadata": _metadata(source),
        "media_type": source.media_type,
        "content": source.text or EMPTY_SUMMARY,
    }


def _derived_knowledge(
    policy: Mapping[str, Any], extraction: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    level = policy["derived_knowledge"]
    if level == "none":
        return None
    claims = list(extraction["claims"]) if extraction else []
    if level == "claims":
        return {"claims": claims}
    relations = list(extraction["relations"]) if extraction else []
    if level == "claims_and_relations":
        return {"claims": claims, "relations": relations}
    return {
        "knowledge_product": {
            "entities": list(extraction["entities"]) if extraction else [],
            "relations": relations,
            "claims": claims,
        }
    }


def build_preserved_record(
    policy: Mapping[str, Any],
    source: NormalizedSource,
    *,
    extractor_version: str,
    extraction: Mapping[str, Any] | None = None,
    previous_record_id: str | None = None,
) -> dict[str, Any]:
    """Return the Preserved Record declared by *policy* for *source*.

    The qualification decision is not an input: a ``REJECTED`` material is
    preserved exactly like a qualified one, so that its identity and rationale
    survive (``relevance-gate-contract.md`` O-7). Choosing an artifact level
    below ``evidence_fragments`` is recorded in the result through the embedded
    policy, which then must carry ``reproducibility_risk_accepted: true``.
    """

    _check_policy(policy)

    record: dict[str, Any] = {
        "schema_version": "1.0",
        "policy": dict(policy),
        "identity": source.identity(extractor_version),
    }

    acquired = _acquired_artifact(policy, source, extraction)
    if acquired is not None:
        record["acquired_artifact"] = acquired

    derived = _derived_knowledge(policy, extraction)
    if derived is not None:
        record["derived_knowledge"] = derived

    if previous_record_id is not None:
        if policy["observation_history"] in ("none", "latest_only"):
            raise UnsupportedPreservationError(
                "previous_record_id requires observation_history 'full_history'"
            )
        record["previous_record_id"] = previous_record_id

    return record
