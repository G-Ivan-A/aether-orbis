"""The Research Run: one explained, auditable unit of research.

A run is a first-class record, not a log line. ``sufficiency-gate-contract.md``
O-7 requires it to carry the versions it ran with, the content identities it
processed, the full qualification decisions, the iterations it performed, the
budget it consumed and its outcome — enough for a reader to reconstruct why the
run ended the way it did without access to the source content itself.

Numeric limits come only from the Runtime Configuration and research criteria
only from the Research Specification (O-5); the orchestrator supplies neither.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from aether_orbis import sufficiency
from aether_orbis.clock import Clock, StepClock
from aether_orbis.errors import SpecificationError
from aether_orbis.expansion import discovered_entities, next_frontier
from aether_orbis.frontier import build_frontier
from aether_orbis.model import FrontierItem, MaterialOutcome, Measurement
from aether_orbis.pipeline import AcquisitionPipeline, IngestionFailure
from aether_orbis.ports import CompletionEvaluator, GraphStore, TelemetrySink, VectorIndex
from aether_orbis.representations import project_graph, project_vector
from aether_orbis.telemetry import build_event

COMPONENT = "research-run-orchestrator"
QUALIFYING = ("QUALIFIED", "CONDITIONAL")


@dataclass(frozen=True)
class IterationReport:
    """What one expansion iteration processed and measured."""

    iteration: int
    strategy: str
    frontier: tuple[FrontierItem, ...]
    outcomes: tuple[MaterialOutcome, ...]
    coverage: Mapping[str, Measurement]

    @property
    def processed_source_ids(self) -> tuple[str, ...]:
        return tuple(outcome.source.source_id for outcome in self.outcomes)


@dataclass(frozen=True)
class ResearchRun:
    """The result of one orchestrated run, document plus in-memory detail."""

    document: Mapping[str, Any]
    outcomes: tuple[MaterialOutcome, ...]
    iterations: tuple[IterationReport, ...]
    failures: tuple[IngestionFailure, ...]
    events: tuple[dict[str, Any], ...]

    @property
    def status(self) -> str:
        return self.document["outcome"]["status"]

    @property
    def qualified(self) -> tuple[MaterialOutcome, ...]:
        return tuple(
            outcome for outcome in self.outcomes if outcome.final_decision in QUALIFYING
        )


def budgets(runtime_configuration: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the runtime budgets, which the specification must not supply."""

    block = runtime_configuration.get("budgets")
    if not isinstance(block, dict):
        raise SpecificationError("runtime configuration must declare budgets")
    for key in ("max_iterations", "max_cost_rub"):
        if key not in block:
            raise SpecificationError(f"runtime configuration must declare budgets.{key}")
    return block


@dataclass
class ResearchRunOrchestrator:
    """Runs a specification to an explained outcome across expansion iterations.

    Graph and vector indexing are both optional and independent: a run with only
    one configured — or with neither — still completes and still produces the same
    Research Run document, which is what ADR-001 (4) means by parallel
    representations.
    """

    pipeline: AcquisitionPipeline
    runtime_configuration: Mapping[str, Any]
    completion: CompletionEvaluator
    graph_store: GraphStore | None = None
    vector_index: VectorIndex | None = None
    indexed_decisions: tuple[str, ...] = QUALIFYING
    cost_per_iteration_rub: float = 0.0
    clock: Clock = field(default_factory=StepClock)
    telemetry: TelemetrySink | None = None

    def __post_init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self.specification = self.pipeline.specification
        self.budgets = budgets(self.runtime_configuration)

    # -- execution ---------------------------------------------------------

    def execute(self) -> ResearchRun:
        """Execute the run and return its Research Run document and detail."""

        dimensions = sufficiency.completion_dimensions(self.specification)
        conditions = sufficiency.success_conditions(self.specification)
        strategy = self.specification["scope"]["strategy"]
        max_iterations = self.budgets["max_iterations"]
        max_cost = self.budgets["max_cost_rub"]

        frontier = build_frontier(self.specification)
        outcomes: list[MaterialOutcome] = []
        failures: list[IngestionFailure] = []
        reports: list[IterationReport] = []
        processed_values: list[str] = []
        seen_source_ids: set[str] = set()
        coverage: dict[str, Measurement] = {}
        known_entities: tuple[str, ...] = ()
        cost = 0.0
        stop_reason = sufficiency.FRONTIER_EXHAUSTED

        while frontier:
            if len(reports) >= max_iterations or cost + self.cost_per_iteration_rub > max_cost:
                stop_reason = sufficiency.BUDGET_EXHAUSTED
                break

            started = self.clock.now()
            result = self.pipeline.run(frontier, seen_source_ids=seen_source_ids)
            cost += self.cost_per_iteration_rub
            seen_source_ids.update(
                outcome.source.source_id for outcome in result.outcomes
            )
            outcomes.extend(result.outcomes)
            failures.extend(result.failures)
            processed_values.extend(item.value for item in frontier)

            self._index(outcomes)

            before, known_entities = known_entities, discovered_entities(outcomes)
            frontier = next_frontier(
                self.specification, result.outcomes, visited=processed_values
            )
            coverage = dict(
                self.completion.measure_completion(
                    sufficiency.CompletionState(
                        outcomes=tuple(outcomes),
                        qualified=self._qualified(outcomes),
                        processed_frontier=tuple(
                            FrontierItem(strategy=strategy, kind="item", value=value)
                            for value in processed_values
                        ),
                        remaining_frontier=frontier,
                        iterations=len(reports) + 1,
                        ingestion_failures=len(failures),
                        discovered_last_iteration=known_entities,
                        known_before_last_iteration=before,
                    ),
                    dimensions,
                )
            )
            reports.append(
                IterationReport(
                    iteration=len(reports),
                    strategy=strategy,
                    frontier=tuple(frontier),
                    outcomes=result.outcomes,
                    coverage=dict(coverage),
                )
            )
            self._emit("discovery", started)

            if not sufficiency.unmet_conditions(coverage, conditions):
                stop_reason = "success_conditions_met"
                break

        outcome = sufficiency.build_run_outcome(
            self.specification,
            coverage,
            qualified=self._qualified(outcomes),
            stop_reason=stop_reason,
            remaining_frontier=frontier,
        )
        document = self._document(outcome, reports, cost)
        self._emit("run_outcome", self.clock.now(), payload={"outcome": dict(outcome)})
        return ResearchRun(
            document=document,
            outcomes=tuple(outcomes),
            iterations=tuple(reports),
            failures=tuple(failures),
            events=tuple(self._events),
        )

    # -- representations ---------------------------------------------------

    def _qualified(self, outcomes: Sequence[MaterialOutcome]) -> tuple[MaterialOutcome, ...]:
        return tuple(
            outcome
            for outcome in outcomes
            if outcome.final_decision in self.indexed_decisions
        )

    def _index(self, outcomes: Sequence[MaterialOutcome]) -> None:
        """Index the qualified stream into whichever representations exist.

        Both calls re-index the full stream, which the stores make idempotent;
        neither call is a precondition of the other.
        """

        stream = self._qualified(outcomes)
        if self.graph_store is not None:
            self.graph_store.index_graph(project_graph(stream))
        if self.vector_index is not None:
            self.vector_index.index_chunks(project_vector(stream))

    # -- document ----------------------------------------------------------

    def model_versions(self) -> dict[str, str]:
        """Return the versions the run actually executed with."""

        versions = {
            f"{role}_model": str(name)
            for role, name in (self.runtime_configuration.get("models") or {}).items()
        }
        versions["parser"] = self.pipeline.parser.parser_version
        versions["extractor"] = self.pipeline.extractor.extractor_version
        versions["extraction_adapter"] = self.pipeline.extractor.model
        return versions

    def _decisions(self, outcomes: Iterable[MaterialOutcome]) -> list[dict[str, Any]]:
        decisions = []
        for outcome in outcomes:
            decision = outcome.decision or outcome.triage_decision
            if decision is not None:
                decisions.append(dict(decision))
        return decisions

    def _document(
        self,
        outcome: Mapping[str, Any],
        reports: Sequence[IterationReport],
        cost: float,
    ) -> dict[str, Any]:
        outcomes = [material for report in reports for material in report.outcomes]
        return {
            "schema_version": "1.0",
            "run_id": self.pipeline.run_id,
            "specification": {
                "id": self.specification["specification_id"],
                "version": self.specification["specification_version"],
            },
            "runtime_configuration": {
                "id": self.runtime_configuration["runtime_id"],
                "version": self.runtime_configuration["runtime_version"],
            },
            "model_versions": self.model_versions(),
            "processed_sources": [
                {
                    "source_id": material.source.source_id,
                    "canonical_url": material.source.canonical_url,
                    "content_hash": material.source.content_hash,
                }
                for material in outcomes
            ],
            "decisions": self._decisions(outcomes),
            "expansion_iterations": [
                {
                    "iteration": report.iteration,
                    "strategy": report.strategy,
                    "processed_source_ids": list(report.processed_source_ids),
                }
                for report in reports
            ],
            "consumed_budget": {
                "iterations": len(reports),
                "cost_rub": round(cost, 2),
            },
            "outcome": dict(outcome),
        }

    def _emit(
        self, operation_role: str, started: Any, *, payload: dict[str, Any] | None = None
    ) -> None:
        """Emit one event of the minimal Phase 1 telemetry surface.

        The roles and payloads are the ones ``telemetry-event.schema.json``
        already defines; the orchestrator adds no vocabulary of its own, since
        the production telemetry contract belongs to Phase 3.
        """

        event = build_event(
            run_id=self.pipeline.run_id,
            profile_id=self.pipeline.profile_id,
            component=COMPONENT,
            operation_role=operation_role,
            started_at=started,
            finished_at=self.clock.now(),
            status="ok",
            payload=payload,
        )
        self._events.append(event)
        if self.telemetry is not None:
            self.telemetry.emit(event)
