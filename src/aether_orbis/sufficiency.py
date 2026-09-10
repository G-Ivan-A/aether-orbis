"""Research Run outcome: five explicit statuses, each with an explanation.

``sufficiency-gate-contract.md`` O-1 forbids one status from masking another, so
the classification below separates "nothing qualified" (``ZERO``), "qualified
sources contradict each other" (``CONFLICT``), "a runtime limit stopped the run"
(``EXHAUSTED``) and "everything reachable was collected and gaps remain"
(``PARTIAL``). Coverage names come from ``termination.completion_dimensions`` of
the Research Specification and never from this module (O-3); numeric limits come
from the Runtime Configuration and never from the specification (O-5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from aether_orbis.errors import SpecificationError
from aether_orbis.evaluation import OPERATORS
from aether_orbis.model import FrontierItem, MaterialOutcome, Measurement

SUFFICIENT = "SUFFICIENT"
PARTIAL = "PARTIAL"
ZERO = "ZERO"
CONFLICT = "CONFLICT"
EXHAUSTED = "EXHAUSTED"
STATUSES = (SUFFICIENT, PARTIAL, ZERO, CONFLICT, EXHAUSTED)

BUDGET_EXHAUSTED = "budget_exhausted"
FRONTIER_EXHAUSTED = "frontier_exhausted"

NO_KNOWLEDGE_GAP = (
    "No material produced knowledge that the Decision Policy qualifies; the run has "
    "no analytical answer to offer."
)
NO_EXPANSION = (
    "No further frontier item is available within scope.frontier; widen the scope or "
    "relax termination.success_conditions."
)

MATERIALLY_DIFFERENT = {
    frozenset({"OBSERVED", "CONTRADICTED"}),
    frozenset({"OBSERVED", "NOT_OBSERVED"}),
}


@dataclass(frozen=True)
class CompletionState:
    """What a completion evaluator is allowed to look at.

    Completion is measured over the run as a whole — not over a single material —
    so the state carries the qualified stream, the frontier already processed and
    the frontier still reachable.
    """

    outcomes: tuple[MaterialOutcome, ...] = ()
    qualified: tuple[MaterialOutcome, ...] = ()
    processed_frontier: tuple[FrontierItem, ...] = ()
    remaining_frontier: tuple[FrontierItem, ...] = ()
    iterations: int = 0
    discovered_last_iteration: tuple[str, ...] = ()
    known_before_last_iteration: tuple[str, ...] = ()


def termination(specification: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the ``termination`` block declared by *specification*."""

    block = specification.get("termination")
    if not isinstance(block, dict):
        raise SpecificationError("specification.termination is required")
    return block


def completion_dimensions(specification: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the declared completion dimensions."""

    dimensions = termination(specification).get("completion_dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise SpecificationError(
            "specification.termination.completion_dimensions is required"
        )
    return tuple(dimensions)


def success_conditions(specification: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Return the declared success conditions, all of which must be declared."""

    conditions = termination(specification).get("success_conditions")
    if not isinstance(conditions, list) or not conditions:
        raise SpecificationError(
            "specification.termination.success_conditions is required"
        )
    declared = set(completion_dimensions(specification))
    undeclared = sorted(
        {condition["dimension"] for condition in conditions} - declared
    )
    if undeclared:
        raise SpecificationError(
            "success conditions reference dimensions that are not declared in "
            "termination.completion_dimensions: " + ", ".join(undeclared)
        )
    return tuple(conditions)


def detect_conflicts(qualified: Sequence[MaterialOutcome]) -> tuple[dict[str, Any], ...]:
    """Return the material contradictions between independent source groups.

    Two qualified source groups conflict when they assert the same relation with
    materially different states. Phase 1 recognizes the pairs declared in
    ``MATERIALLY_DIFFERENT``; ``UNCERTAIN`` is hedging, not a contradiction.
    """

    by_relation: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    for outcome in qualified:
        if outcome.extraction is None:
            continue
        group = outcome.source.source_group_id
        for relation in outcome.extraction["relations"]:
            key = (relation["subject"], relation["predicate"], relation["object"])
            by_relation.setdefault(key, {}).setdefault(relation["state"], set()).add(group)

    conflicts: list[dict[str, Any]] = []
    for (subject, predicate, obj), by_state in sorted(by_relation.items()):
        states = set(by_state)
        if not any(pair <= states for pair in MATERIALLY_DIFFERENT):
            continue
        groups = sorted({group for holders in by_state.values() for group in holders})
        if len(groups) < 2:
            continue
        stated = ", ".join(
            f"{state} in {', '.join(sorted(holders))}"
            for state, holders in sorted(by_state.items())
        )
        conflicts.append(
            {
                "dimension": predicate,
                "description": (
                    f"Independent source groups disagree on {subject} {predicate} {obj}: "
                    f"{stated}."
                ),
                "source_group_ids": groups,
            }
        )
    return tuple(conflicts)


def _unmet(
    coverage: Mapping[str, Measurement], conditions: Sequence[Mapping[str, Any]]
) -> tuple[str, ...]:
    gaps: list[str] = []
    for condition in conditions:
        dimension = condition["dimension"]
        measurement = coverage.get(dimension)
        if measurement is None:
            gaps.append(
                f"{dimension} was never measured; no completion evaluator is configured "
                "for it."
            )
            continue
        if not OPERATORS[condition["operator"]](measurement.score, condition["value"]):
            gaps.append(
                f"{dimension} is {measurement.score} and does not satisfy "
                f"{condition['operator']} {condition['value']}: {measurement.rationale}"
            )
    return tuple(gaps)


def _recommendations(
    remaining: Sequence[FrontierItem], conflicts: Sequence[Mapping[str, Any]], status: str
) -> list[str]:
    recommendations = [
        f"Acquire an independent source group for {conflict['dimension']}."
        for conflict in conflicts
    ]
    recommendations.extend(
        f"{item.strategy}: {item.value}" for item in remaining
    )
    if not recommendations and status != SUFFICIENT:
        recommendations.append(NO_EXPANSION)
    return list(dict.fromkeys(recommendations))


def build_run_outcome(
    specification: Mapping[str, Any],
    coverage: Mapping[str, Measurement],
    *,
    qualified: Sequence[MaterialOutcome],
    stop_reason: str,
    remaining_frontier: Sequence[FrontierItem] = (),
) -> dict[str, Any]:
    """Return the explained Research Run Outcome.

    ``ZERO`` is checked first: without qualified knowledge there is nothing to
    contradict and nothing to call sufficient. The run reports it as a result
    rather than compensating for it (ADR-006, decision 6).
    """

    declared = set(completion_dimensions(specification))
    undeclared = sorted(set(coverage) - declared)
    if undeclared:
        raise SpecificationError(
            "coverage reports dimensions that are not declared in "
            "termination.completion_dimensions: " + ", ".join(undeclared)
        )

    conditions = success_conditions(specification)
    gaps = list(_unmet(coverage, conditions))
    conflicts = detect_conflicts(qualified)

    if not qualified:
        status = ZERO
        gaps.insert(0, NO_KNOWLEDGE_GAP)
    elif conflicts:
        status = CONFLICT
    elif not gaps:
        status = SUFFICIENT
    elif stop_reason == BUDGET_EXHAUSTED:
        status = EXHAUSTED
    else:
        status = PARTIAL

    return {
        "schema_version": "1.0",
        "status": status,
        "coverage": {name: measurement.score for name, measurement in coverage.items()},
        "gaps": list(dict.fromkeys(gaps)),
        "conflicts": list(conflicts),
        "recommended_expansion": _recommendations(remaining_frontier, conflicts, status),
        "rationale": _rationale(status, coverage, qualified, stop_reason, conflicts),
    }


def _rationale(
    status: str,
    coverage: Mapping[str, Measurement],
    qualified: Sequence[MaterialOutcome],
    stop_reason: str,
    conflicts: Sequence[Mapping[str, Any]],
) -> str:
    measured = ", ".join(
        f"{name}={measurement.score}" for name, measurement in sorted(coverage.items())
    )
    groups = len({outcome.source.source_group_id for outcome in qualified})
    if status == ZERO:
        return (
            f"No source group produced qualified knowledge; the run stopped because "
            f"{stop_reason}. Coverage: {measured or 'not measured'}."
        )
    if status == CONFLICT:
        return (
            f"{len(conflicts)} contradiction(s) between independent qualified source "
            f"groups block a single answer. Coverage: {measured}."
        )
    if status == SUFFICIENT:
        return (
            f"Every success condition is satisfied over {groups} qualified source "
            f"group(s). Coverage: {measured}."
        )
    if status == EXHAUSTED:
        return (
            f"The runtime budget was exhausted before the success conditions were "
            f"satisfied over {groups} qualified source group(s). Coverage: {measured}."
        )
    return (
        f"Useful knowledge was qualified from {groups} source group(s), but the run "
        f"stopped because {stop_reason} with gaps remaining. Coverage: {measured}."
    )
