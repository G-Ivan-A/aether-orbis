"""Context Package: what one Research Run hands to its consumer.

``docs/concept.md`` places the Context Package at the end of the object
hierarchy, as the contract for the consumer. Phase 1 assembles it by composition
from parts that already have contracts — the Research Run, the preserved records
and the evidence behind each claim — rather than by inventing a new schema, so
nothing here can drift away from those contracts.

The package never hides an insufficient result: ``status``, ``gaps``,
``conflicts`` and ``rationale`` travel with the knowledge, and a ``ZERO`` run
produces a package with no claims rather than a generated answer
(``sufficiency-gate-contract.md`` O-6).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aether_orbis.model import MaterialOutcome
from aether_orbis.representations import provenance_of


def _claims(outcomes: Sequence[MaterialOutcome]) -> list[dict[str, Any]]:
    claims = []
    for outcome in outcomes:
        if outcome.extraction is None:
            continue
        provenance = provenance_of(outcome)
        for claim in outcome.extraction["claims"]:
            claims.append(
                {
                    "claim": claim["claim"],
                    "entity_ids": list(claim["entity_ids"]),
                    "extraction_confidence": claim["extraction_confidence"],
                    "evidence": dict(claim["evidence"]),
                    "provenance": provenance,
                }
            )
    return claims


def build_context_package(
    run: Mapping[str, Any],
    outcomes: Sequence[MaterialOutcome],
    *,
    graph_nodes: int = 0,
    graph_edges: int = 0,
    vector_chunks: int = 0,
) -> dict[str, Any]:
    """Return the Context Package of one Research Run.

    *outcomes* are the qualified materials the run indexed; the representation
    counts describe what was indexed and stay optional, because a run with one
    representation disabled still produces a complete package.
    """

    outcome = run["outcome"]
    return {
        "schema_version": "1.0",
        "run_id": run["run_id"],
        "specification": dict(run["specification"]),
        "status": outcome["status"],
        "coverage": dict(outcome["coverage"]),
        "gaps": list(outcome["gaps"]),
        "conflicts": [dict(conflict) for conflict in outcome["conflicts"]],
        "recommended_expansion": list(outcome["recommended_expansion"]),
        "rationale": outcome["rationale"],
        "claims": _claims(outcomes),
        "sources": [
            {
                **provenance_of(outcome_item),
                "preserved_record": outcome_item.record,
            }
            for outcome_item in outcomes
        ],
        "representations": {
            "graph": {"nodes": graph_nodes, "edges": graph_edges},
            "vector": {"chunks": vector_chunks},
        },
    }
