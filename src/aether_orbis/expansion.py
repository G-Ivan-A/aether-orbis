"""Frontier expansion from what the qualified knowledge stream discovered.

Only the ``expand`` strategy grows its own frontier: an enumerated window and a
query template are fully described by the specification, while a neighbourhood is
discovered one hop at a time. The seeds proposed here are entity names taken from
qualified extractions, so expansion never leaves the evidence behind
(``sufficiency-gate-contract.md`` O-4).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from aether_orbis.model import FrontierItem, MaterialOutcome

EXPAND = "expand"


def discovered_entities(outcomes: Iterable[MaterialOutcome]) -> tuple[str, ...]:
    """Return the entity names named by qualified extractions, in order."""

    names: dict[str, None] = {}
    for outcome in outcomes:
        if outcome.extraction is None:
            continue
        for entity in outcome.extraction["entities"]:
            names.setdefault(entity["name"], None)
    return tuple(names)


def next_frontier(
    specification: Mapping[str, Any],
    outcomes: Sequence[MaterialOutcome],
    *,
    visited: Iterable[str] = (),
) -> tuple[FrontierItem, ...]:
    """Return the next frontier batch, empty when the frontier is exhausted.

    A strategy other than ``expand`` yields nothing: repeating an already
    complete frontier would be an iteration without progress, which O-4 says
    SHOULD NOT happen.
    """

    scope = specification["scope"]
    if scope.get("strategy") != EXPAND:
        return ()

    hints = tuple(scope.get("frontier", {}).get("relation_hints") or ())
    seen = set(visited)
    return tuple(
        FrontierItem(strategy=EXPAND, kind="seed", value=name, hints=hints)
        for name in discovered_entities(outcomes)
        if name not in seen
    )
