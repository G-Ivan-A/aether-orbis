"""Assembly of the acquisition ports for a validated Research Profile."""

from hashlib import sha256
from typing import Any, Mapping
from uuid import uuid4

from aether_orbis.adapters.completion import (
    ConfiguredCompletionEvaluator,
    neighborhood_completeness,
    new_entity_saturation,
    window_coverage,
)
from aether_orbis.adapters.evaluators import (
    ConfiguredEvaluator,
    duplicate_independence,
    keyword_coverage,
    mean_evidence_strength,
    metadata_score,
)
from aether_orbis.adapters.extractors import DictionaryExtractor, EntityDefinition
from aether_orbis.adapters.parsers import HtmlTextParser
from aether_orbis.clock import SystemClock
from aether_orbis.errors import SpecificationError
from aether_orbis.model import Measurement
from aether_orbis.orchestration import ResearchRunOrchestrator
from aether_orbis.pipeline import AcquisitionPipeline
from aether_orbis.ports import SourceFetcher
from aether_orbis.sufficiency import CompletionState, detect_conflicts


def _unresolved_conflicts(state: CompletionState) -> Measurement:
    count = len(detect_conflicts(state.qualified))
    return Measurement(score=count, rationale=f"{count} unresolved conflict(s).")


def build_profile_run(
    profile: Mapping[str, Any],
    runtime: Mapping[str, Any],
    fetcher: SourceFetcher,
) -> ResearchRunOrchestrator:
    """Build a fresh run from validated YAML and a caller-supplied source port."""

    settings = profile.get("offline_adapters")
    if settings is None:
        raise SpecificationError("the profile needs offline_adapters for this entry point")
    specification = profile["specification"]
    topics = tuple(specification["target"].get("topics", ()))
    seeds = tuple(specification["target"].get("seed_entities", ()))
    entity_type = "topic" if topics else "entity"
    dictionary = tuple(
        EntityDefinition(
            id=f"{entity_type}.{sha256(name.casefold().encode()).hexdigest()[:16]}",
            type=entity_type,
            name=name,
        )
        for name in dict.fromkeys(topics or seeds)
    )
    measure_functions = {
        "topic_coverage": keyword_coverage(topics),
        "evidence_strength": mean_evidence_strength(),
        "source_authority": metadata_score(settings.get("source_authority", {}), default=0.0),
        "duplicate_independence": duplicate_independence(),
    }
    evaluator = ConfiguredEvaluator(
        measures={
            dimension: measure_functions[measurement]
            for dimension, measurement in settings["measurements"].items()
            if measurement != "unmeasured"
        },
        triage_dimensions=tuple(settings["triage"]),
        require_all_dimensions=False,
    )
    pipeline = AcquisitionPipeline(
        specification=specification,
        fetcher=fetcher,
        parser=HtmlTextParser(),
        extractor=DictionaryExtractor(
            entities=dictionary,
            claim_markers=tuple(settings["claim_markers"])
        ),
        evaluator=evaluator,
        profile_id=profile["profile_id"],
        run_id=f"run-{uuid4().hex}",
        clock=SystemClock(),
    )
    completion = ConfiguredCompletionEvaluator(
        measures={
            "window_coverage": window_coverage(),
            "neighborhood_completeness": neighborhood_completeness(),
            "new_entity_saturation": new_entity_saturation(),
            "unresolved_conflicts": _unresolved_conflicts,
        }
    )
    return ResearchRunOrchestrator(
        pipeline=pipeline,
        runtime_configuration=runtime,
        completion=completion,
        clock=SystemClock(),
        profile_version=profile["profile_version"],
    )
