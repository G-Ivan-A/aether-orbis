"""Offline completion evaluators.

Completion dimensions are named by ``termination.completion_dimensions`` of each
Research Specification, so this module supplies measure functions and a
configured evaluator that maps names to them — the same shape as
:mod:`aether_orbis.adapters.evaluators`. Nothing here decides sufficiency; it
only measures, and the gate compares against the declared success conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from aether_orbis.model import Measurement
from aether_orbis.sufficiency import CompletionState

CompletionFn = Callable[[CompletionState], Measurement]


def window_coverage() -> CompletionFn:
    """Share of the window's material that the run could actually evaluate.

    AM-1 monitors a window, and what makes the window incompletely covered is
    material the run could not turn into a decision at all — a source that failed
    to normalize is a hole in the observation, while a source that was evaluated
    and rejected is a result.
    """

    def measure(state: CompletionState) -> Measurement:
        evaluated = len(state.outcomes)
        total = evaluated + state.ingestion_failures
        if not total:
            return Measurement(
                score=0.0, rationale="No material was retrieved for the window."
            )
        return Measurement(
            score=round(evaluated / total, 4),
            rationale=(
                f"{evaluated} of {total} retrieved material(s) reached a decision; "
                f"{state.ingestion_failures} could not be normalized."
            ),
        )

    return measure


def neighborhood_completeness() -> CompletionFn:
    """Fraction of the discovered entities that were themselves expanded.

    AM-2 builds a neighbourhood, which is complete when no discovered entity is
    still waiting on the frontier.
    """

    def measure(state: CompletionState) -> Measurement:
        pending = len(state.remaining_frontier)
        expanded = len(state.processed_frontier)
        total = expanded + pending
        if not total:
            return Measurement(
                score=0.0, rationale="No entity was expanded and none is pending."
            )
        return Measurement(
            score=round(expanded / total, 4),
            rationale=f"{expanded} expanded seed(s), {pending} still on the frontier.",
        )

    return measure


def new_entity_saturation() -> CompletionFn:
    """Share of the known entities that the last iteration added.

    Saturation near zero means another iteration would repeat what is already
    known, which O-4 asks the orchestrator to avoid.
    """

    def measure(state: CompletionState) -> Measurement:
        new = len(set(state.discovered_last_iteration) - set(state.known_before_last_iteration))
        known = len(set(state.discovered_last_iteration) | set(state.known_before_last_iteration))
        if not known:
            return Measurement(score=0.0, rationale="No entity is known yet.")
        return Measurement(
            score=round(new / known, 4),
            rationale=f"{new} new entity(ies) out of {known} known after the last iteration.",
        )

    return measure


@dataclass(frozen=True)
class ConfiguredCompletionEvaluator:
    """Measures exactly the completion dimensions the caller asks for."""

    measures: Mapping[str, CompletionFn]

    def measure_completion(
        self, state: CompletionState, dimensions: tuple[str, ...]
    ) -> dict[str, Measurement]:
        """Return a measurement for every configured dimension name.

        An unconfigured dimension is left out rather than defaulted, so the gate
        reports it as an unmeasured gap instead of silently passing.
        """

        return {
            name: self.measures[name](state)
            for name in dimensions
            if name in self.measures
        }
