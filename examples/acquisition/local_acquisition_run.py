"""Local acquisition run: Research Specification in, preserved knowledge out.

Run it from the repository root::

    python3 examples/acquisition/local_acquisition_run.py

Everything is local: the corpus is a directory of files, the parser and the
extractor are dependency free and the evaluator only implements the
characteristics that the specifications declare. No network access, no
credentials and no production store are involved, so the run is reproducible on
any checkout. The test suite executes this same module, which keeps the example
and the integration expectations from drifting apart.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import yaml

from aether_orbis.adapters import (
    ConfiguredEvaluator,
    CorpusFetcher,
    DictionaryExtractor,
    EntityDefinition,
    HtmlTextParser,
    duplicate_independence,
    keyword_coverage,
    mean_evidence_strength,
    metadata_score,
)
from aether_orbis.pipeline import AcquisitionPipeline, InMemoryRecordStore
from aether_orbis.ports import CollectingTelemetrySink

ACQUISITION = ROOT / "tests" / "fixtures" / "acquisition"
MODELS = ("am-1", "am-2")

AM1_KEYWORDS = (
    "software architecture",
    "modular monolith",
    "service boundaries",
    "deployment",
)
AM1_ENTITIES = (
    EntityDefinition(id="org.example-systems", type="organization", name="Example Systems"),
    EntityDefinition(id="product.example-platform", type="product", name="Example Platform"),
)
AM2_ENTITIES = (
    EntityDefinition(
        id="org.example-organization", type="organization", name="Example Organization"
    ),
    EntityDefinition(id="org.example-registry", type="organization", name="Example Registry"),
)
AM2_AUTHORITY = {
    "registry.example.org": 0.9,
    "mirror.example.net": 0.8,
}


def load_specification(model: str) -> dict[str, Any]:
    """Load one fixture Research Specification."""

    path = ACQUISITION / model / "specification.yaml"
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _am1_pipeline(specification: dict[str, Any], **overrides: Any) -> AcquisitionPipeline:
    return AcquisitionPipeline(
        specification=specification,
        fetcher=CorpusFetcher.from_directory(ACQUISITION / "am-1" / "corpus"),
        parser=HtmlTextParser(),
        extractor=DictionaryExtractor(
            entities=AM1_ENTITIES,
            predicates={"reported_on": ("reported that", "published")},
            claim_markers=("confirmed", "reported that"),
        ),
        evaluator=ConfiguredEvaluator(
            measures={
                "topic_match": keyword_coverage(AM1_KEYWORDS),
                "evidence_strength": mean_evidence_strength(),
            },
            triage_dimensions=("topic_match",),
        ),
        run_id="run-am1-fixture",
        profile_id="profile-am1-fixture",
        **overrides,
    )


def _am2_pipeline(specification: dict[str, Any], **overrides: Any) -> AcquisitionPipeline:
    return AcquisitionPipeline(
        specification=specification,
        fetcher=CorpusFetcher.from_directory(ACQUISITION / "am-2" / "corpus"),
        parser=HtmlTextParser(),
        extractor=DictionaryExtractor(
            entities=AM2_ENTITIES,
            predicates={"partnered_with": ("partnered with", "agreement with")},
            claim_markers=("confirmed", "partnered with"),
        ),
        evaluator=ConfiguredEvaluator(
            measures={
                "source_authority": metadata_score(AM2_AUTHORITY, default=0.1),
                "evidence_strength": mean_evidence_strength(),
                "independence": duplicate_independence(),
            },
            triage_dimensions=("source_authority", "independence"),
        ),
        run_id="run-am2-fixture",
        profile_id="profile-am2-fixture",
        **overrides,
    )


BUILDERS = {"am-1": _am1_pipeline, "am-2": _am2_pipeline}


def build_pipeline(model: str, **overrides: Any) -> AcquisitionPipeline:
    """Return the offline pipeline configured for the given fixture model."""

    specification = load_specification(model)
    return BUILDERS[model](specification, **overrides)


def run(model: str) -> tuple[Any, CollectingTelemetrySink, InMemoryRecordStore]:
    """Execute one fixture acquisition run and return its artifacts."""

    telemetry = CollectingTelemetrySink()
    store = InMemoryRecordStore()
    pipeline = build_pipeline(model, telemetry=telemetry, store=store)
    return pipeline.run(), telemetry, store


def main() -> int:
    """Run both fixture specifications and report what each produced."""

    for model in MODELS:
        result, telemetry, store = run(model)
        print(f"{model}: {len(result.frontier)} frontier item(s), "
              f"{len(result.outcomes)} material(s), {len(result.failures)} rejected as malformed")
        for outcome in result.outcomes:
            stage = "triage" if outcome.stopped_at_triage else "full evaluation"
            print(
                f"  {outcome.final_decision:<11} {outcome.source.canonical_url}\n"
                f"    decided after {stage}, group {outcome.source.source_group_id}, "
                f"preserved keys {sorted(outcome.record)}"
            )
        for failure in result.failures:
            print(f"  MALFORMED   {failure.url}\n    {failure.reason}")
        print(f"  telemetry events: {len(telemetry.events)}, stored outcomes: {len(store.outcomes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
