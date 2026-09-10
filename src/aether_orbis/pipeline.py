"""Local acquisition run: specification → preserved, qualified knowledge.

The pipeline owns the order of the stages and nothing else. Every research
criterion — which characteristics are measured, which thresholds qualify a
material and what is preserved — comes from the Research Specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from aether_orbis import evaluation as evaluation_stage
from aether_orbis.clock import Clock, StepClock, to_rfc3339
from aether_orbis.errors import MalformedSourceError
from aether_orbis.extraction import build_extraction_result, extraction_telemetry
from aether_orbis.frontier import build_frontier
from aether_orbis.grouping import SourceGrouper
from aether_orbis.ingestion import ingest_material
from aether_orbis.model import FrontierItem, MaterialOutcome, NormalizedSource
from aether_orbis.ports import (
    CharacteristicEvaluator,
    ContentParser,
    KnowledgeExtractor,
    SourceFetcher,
    TelemetrySink,
)
from aether_orbis.preservation import build_preserved_record
from aether_orbis.telemetry import build_event

COMPONENT = "acquisition-core"


@runtime_checkable
class RecordStore(Protocol):
    """Stores everything produced for one material, qualified or rejected."""

    def save(self, outcome: MaterialOutcome) -> None:
        """Persist one material outcome."""


@dataclass
class InMemoryRecordStore:
    """Offline record store used by tests and local integration runs."""

    outcomes: list[MaterialOutcome] = field(default_factory=list)

    def save(self, outcome: MaterialOutcome) -> None:
        self.outcomes.append(outcome)

    def by_decision(self, decision: str) -> list[MaterialOutcome]:
        """Return every stored outcome with the given final decision."""

        return [outcome for outcome in self.outcomes if outcome.final_decision == decision]


@dataclass(frozen=True)
class IngestionFailure:
    """Material that could not be normalized into a contractual identity."""

    item: FrontierItem
    url: str
    reason: str


@dataclass(frozen=True)
class AcquisitionRun:
    """Result of one local acquisition run."""

    frontier: tuple[FrontierItem, ...]
    outcomes: tuple[MaterialOutcome, ...]
    failures: tuple[IngestionFailure, ...]
    events: tuple[dict[str, Any], ...]

    def by_decision(self, decision: str) -> tuple[MaterialOutcome, ...]:
        return tuple(
            outcome for outcome in self.outcomes if outcome.final_decision == decision
        )

    @property
    def source_group_ids(self) -> tuple[str, ...]:
        return tuple(outcome.source.source_group_id for outcome in self.outcomes)


@dataclass
class AcquisitionPipeline:
    """Executes one Research Specification against injected ports."""

    specification: Mapping[str, Any]
    fetcher: SourceFetcher
    parser: ContentParser
    extractor: KnowledgeExtractor
    evaluator: CharacteristicEvaluator
    run_id: str = "run-local"
    profile_id: str = "profile-local"
    clock: Clock = field(default_factory=StepClock)
    telemetry: TelemetrySink | None = None
    store: RecordStore | None = None
    grouper: SourceGrouper = field(default_factory=SourceGrouper)

    def __post_init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._dimensions = evaluation_stage.declared_dimensions(self.specification)
        self._policy = evaluation_stage.decision_policy(self.specification)

    def run(self) -> AcquisitionRun:
        """Acquire, evaluate and preserve every material on the frontier."""

        frontier = build_frontier(self.specification)
        outcomes: list[MaterialOutcome] = []
        failures: list[IngestionFailure] = []

        for item in frontier:
            for material in self.fetcher.fetch(item):
                started = self.clock.now()
                try:
                    source = ingest_material(material, self.parser, self.grouper)
                except MalformedSourceError as error:
                    self._emit(
                        "parsing",
                        started,
                        status="error",
                        error_code="malformed_source",
                    )
                    failures.append(
                        IngestionFailure(item=item, url=material.url, reason=str(error))
                    )
                    continue
                self._emit("parsing", started, status="ok")
                outcome = self._process(source)
                outcomes.append(outcome)
                if self.store is not None:
                    self.store.save(outcome)

        return AcquisitionRun(
            frontier=frontier,
            outcomes=tuple(outcomes),
            failures=tuple(failures),
            events=tuple(self._events),
        )

    def _process(self, source: NormalizedSource) -> MaterialOutcome:
        triage = self._evaluate(source, stage="triage", extraction=None)
        decision, matched_rule = evaluation_stage.match_decision_rule(triage, self._policy)
        if matched_rule is not None and decision == "REJECTED":
            triage_decision = self._qualify(triage)
            return self._preserve(
                source, triage_evaluation=triage, triage_decision=triage_decision
            )

        extraction = self._extract(source)
        full = self._evaluate(source, stage="full", extraction=extraction)
        full_decision = self._qualify(full)
        return self._preserve(
            source,
            triage_evaluation=triage,
            extraction=extraction,
            evaluation=full,
            decision=full_decision,
        )

    def _extract(self, source: NormalizedSource) -> dict[str, Any]:
        started = self.clock.now()
        candidates = self.extractor.extract(source)
        outcome = build_extraction_result(
            source,
            candidates,
            model=self.extractor.model,
            extractor_version=self.extractor.extractor_version,
            extracted_at=to_rfc3339(started),
        )
        status = outcome.status
        error_code = outcome.error_code
        if status == "partial" and error_code is None:
            error_code = outcome.dropped[0].reason
        if status == "error" and error_code is None:
            error_code = "extraction_failed"
        payload = (
            {"extraction": extraction_telemetry(outcome.document)}
            if status != "error"
            else None
        )
        self._emit(
            "extraction",
            started,
            status=status,
            error_code=error_code,
            payload=payload,
        )
        return outcome.document

    def _evaluate(
        self,
        source: NormalizedSource,
        *,
        stage: str,
        extraction: dict[str, Any] | None,
    ) -> dict[str, Any]:
        started = self.clock.now()
        measurements = self.evaluator.measure(stage, source, extraction, self._dimensions)
        result = evaluation_stage.build_evaluation_result(
            source,
            self.specification,
            measurements,
            stage=stage,
            evaluated_at=to_rfc3339(started),
        )
        self._emit(
            "triage" if stage == "triage" else "full_evaluation",
            started,
            status="ok",
            payload={"evaluation": evaluation_stage.evaluation_telemetry(result)},
        )
        return result

    def _qualify(self, evaluation: Mapping[str, Any]) -> dict[str, Any]:
        started = self.clock.now()
        decision = evaluation_stage.build_qualification_decision(
            evaluation, self._policy, decided_at=to_rfc3339(started)
        )
        missing = self._unmeasured_dimensions(evaluation)
        status = "partial" if missing and evaluation["evaluation_stage"] == "full" else "ok"
        self._emit(
            "qualification",
            started,
            status=status,
            error_code="configuration_incomplete" if status == "partial" else None,
            payload={"qualification": evaluation_stage.qualification_telemetry(decision)},
        )
        return decision

    def _unmeasured_dimensions(self, evaluation: Mapping[str, Any]) -> tuple[str, ...]:
        measured = set(evaluation["characteristics"])
        referenced = {
            condition["dimension"]
            for rule in self._policy["rules"]
            for condition in rule["all"]
        }
        return tuple(sorted(referenced - measured))

    def _preserve(
        self,
        source: NormalizedSource,
        *,
        triage_evaluation: dict[str, Any],
        triage_decision: dict[str, Any] | None = None,
        extraction: dict[str, Any] | None = None,
        evaluation: dict[str, Any] | None = None,
        decision: dict[str, Any] | None = None,
    ) -> MaterialOutcome:
        started = self.clock.now()
        record = build_preserved_record(
            self.specification["preservation"],
            source,
            extractor_version=self.extractor.extractor_version,
            extraction=extraction,
        )
        self._emit("knowledge_building", started, status="ok")
        return MaterialOutcome(
            source=source,
            triage_evaluation=triage_evaluation,
            triage_decision=triage_decision,
            extraction=extraction,
            evaluation=evaluation,
            decision=decision,
            record=record,
        )

    def _emit(
        self,
        operation_role: str,
        started: Any,
        *,
        status: str,
        error_code: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = build_event(
            run_id=self.run_id,
            profile_id=self.profile_id,
            component=COMPONENT,
            operation_role=operation_role,
            started_at=started,
            finished_at=self.clock.now(),
            status=status,
            error_code=error_code,
            payload=payload,
        )
        self._events.append(event)
        if self.telemetry is not None:
            self.telemetry.emit(event)
