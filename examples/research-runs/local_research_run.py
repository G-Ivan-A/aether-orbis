"""End-to-end Research Runs: one codebase, two Research Specifications.

Run both models from the repository root::

    python3 examples/research-runs/local_research_run.py

AM-1 monitors an enumerated window and AM-2 expands a relationship
neighbourhood. The difference between them lives entirely in the Research
Specification and in the adapters wired for each profile — the orchestrator,
the gate and the two representations are the same objects in both runs, with no
per-model branching anywhere in the pipeline.

Everything is local: a directory of files stands in for the network, the parser
and the extractor are dependency free, and both representations are in-memory,
so the run needs neither credentials nor a server and writes nothing outside the
process. The test suite imports this module, which keeps the example and the
end-to-end expectations from drifting apart.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "examples" / "acquisition") not in sys.path:
    sys.path.insert(0, str(ROOT / "examples" / "acquisition"))

import yaml
from local_acquisition_run import MODELS, build_pipeline

from aether_orbis.adapters.completion import (
    ConfiguredCompletionEvaluator,
    neighborhood_completeness,
    new_entity_saturation,
    window_coverage,
)
from aether_orbis.adapters.representations import InMemoryGraphStore, InMemoryVectorIndex
from aether_orbis.context import build_context_package
from aether_orbis.orchestration import ResearchRun, ResearchRunOrchestrator
from aether_orbis.pipeline import InMemoryRecordStore
from aether_orbis.ports import CollectingTelemetrySink

RUNTIME = ROOT / "configs" / "runtime" / "default.yaml"

COMPLETION_MEASURES = {
    "window_coverage": window_coverage(),
    "neighborhood_completeness": neighborhood_completeness(),
    "new_entity_saturation": new_entity_saturation(),
}


def load_runtime_configuration(path: Path = RUNTIME) -> dict[str, Any]:
    """Load the Runtime Configuration that supplies the budgets."""

    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def build_orchestrator(
    model: str,
    *,
    runtime_configuration: dict[str, Any] | None = None,
    graph_store: InMemoryGraphStore | None = None,
    vector_index: InMemoryVectorIndex | None = None,
    **pipeline_overrides: Any,
) -> ResearchRunOrchestrator:
    """Wire one orchestrated run for the given fixture model.

    Passing ``graph_store=None`` or ``vector_index=None`` disables that
    representation; the run still completes, which is the independence the two
    parallel representations are supposed to have.
    """

    return ResearchRunOrchestrator(
        pipeline=build_pipeline(model, **pipeline_overrides),
        runtime_configuration=runtime_configuration or load_runtime_configuration(),
        completion=ConfiguredCompletionEvaluator(measures=COMPLETION_MEASURES),
        graph_store=graph_store,
        vector_index=vector_index,
    )


def run(model: str, **overrides: Any) -> tuple[ResearchRun, dict[str, Any], InMemoryGraphStore, InMemoryVectorIndex]:
    """Execute one end-to-end run and return the run, package and both indexes."""

    graph_store = InMemoryGraphStore()
    vector_index = InMemoryVectorIndex()
    telemetry = CollectingTelemetrySink()
    store = InMemoryRecordStore()
    orchestrator = build_orchestrator(
        model,
        graph_store=graph_store,
        vector_index=vector_index,
        telemetry=telemetry,
        store=store,
        **overrides,
    )
    result = orchestrator.execute()
    package = build_context_package(
        result.document,
        result.qualified,
        graph_nodes=len(graph_store.nodes),
        graph_edges=len(graph_store.edges),
        vector_chunks=len(vector_index.chunks),
    )
    return result, package, graph_store, vector_index


def main() -> int:
    """Run both specifications end to end and report what each produced."""

    for model in MODELS:
        result, package, graph_store, vector_index = run(model)
        document = result.document
        print(f"{model}: {document['outcome']['status']}")
        print(
            f"  {len(document['expansion_iterations'])} iteration(s), "
            f"{len(document['processed_sources'])} source(s), "
            f"{len(document['decisions'])} recorded decision(s)"
        )
        print(f"  coverage: {json.dumps(document['outcome']['coverage'], sort_keys=True)}")
        for gap in document["outcome"]["gaps"]:
            print(f"  gap: {gap}")
        for conflict in document["outcome"]["conflicts"]:
            print(f"  conflict: {conflict['description']}")
        print(
            f"  graph: {len(graph_store.nodes)} node(s), {len(graph_store.edges)} edge(s); "
            f"vector: {len(vector_index.chunks)} chunk(s)"
        )
        print(f"  context package: {len(package['claims'])} claim(s) with evidence")
        print(f"  rationale: {document['outcome']['rationale']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
