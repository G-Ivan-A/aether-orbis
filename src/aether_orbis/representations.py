"""Graph and vector projections of one qualified knowledge stream.

ADR-001 (4) keeps the two representations **parallel**: neither is derived from
the other and neither is a stage of the other. This module therefore produces
two independent projections of the same ``MaterialOutcome`` stream, and both
carry the full provenance block, so that a consumer of either representation can
walk back from an entity, a relation or a claim to the exact content identity it
came from (``preservation-contract.md`` O-2, ``extraction-contract.md`` O-3).

Nothing here decides *what* is worth indexing: the caller passes the outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping

from aether_orbis.model import MaterialOutcome

SOURCE = "source"
ENTITY = "entity"
CLAIM = "claim"

MENTIONED_IN = "mentioned_in"
STATED_IN = "stated_in"
ABOUT = "about"

OBSERVED = "OBSERVED"


@dataclass(frozen=True)
class GraphNode:
    """One node of the knowledge graph."""

    id: str
    type: str
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    """One directed, evidence-backed edge of the knowledge graph.

    ``provenance`` is mandatory: an edge without a traceable content identity
    would be knowledge the system cannot defend.
    """

    subject: str
    predicate: str
    object: str
    state: str
    provenance: Mapping[str, Any]
    evidence: Mapping[str, Any] | None = None

    @property
    def key(self) -> tuple[str, str, str, str]:
        """Return the identity of the edge within one source."""

        return (self.subject, self.predicate, self.object, self.provenance["source_id"])


@dataclass(frozen=True)
class GraphProjection:
    """Nodes and edges produced for a stream of material outcomes."""

    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()

    def node(self, node_id: str) -> GraphNode | None:
        return next((node for node in self.nodes if node.id == node_id), None)


@dataclass(frozen=True)
class VectorChunk:
    """One retrievable text chunk with the provenance of its source."""

    chunk_id: str
    text: str
    kind: str
    provenance: Mapping[str, Any]


def _digest(*parts: str) -> str:
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def source_node_id(source_id: str) -> str:
    return f"{SOURCE}:{source_id}"


def entity_node_id(entity_id: str) -> str:
    return f"{ENTITY}:{entity_id}"


def claim_node_id(source_id: str, claim: str) -> str:
    return f"{CLAIM}:{_digest(source_id, claim)}"


def provenance_of(outcome: MaterialOutcome) -> dict[str, Any]:
    """Return the provenance block shared by both representations."""

    source = outcome.source
    decision = outcome.decision or outcome.triage_decision
    provenance = {
        "source_id": source.source_id,
        "source_group_id": source.source_group_id,
        "canonical_url": source.canonical_url,
        "content_hash": source.content_hash,
        "retrieved_at": source.retrieved_at,
        "decision": outcome.final_decision,
    }
    if decision is not None:
        provenance["decision_id"] = decision["decision_id"]
        provenance["evaluation_id"] = decision["evaluation_id"]
    return provenance


def project_graph(outcomes: Iterable[MaterialOutcome]) -> GraphProjection:
    """Return the graph projection of every outcome that produced knowledge.

    An outcome stopped at triage carries no extraction and therefore no
    knowledge; it is preserved as a Preserved Record, not as a graph element.
    """

    nodes: dict[str, GraphNode] = {}
    edges: dict[tuple[str, str, str, str], GraphEdge] = {}

    for outcome in outcomes:
        extraction = outcome.extraction
        if extraction is None:
            continue
        provenance = provenance_of(outcome)
        source_id = source_node_id(outcome.source.source_id)
        nodes[source_id] = GraphNode(
            id=source_id,
            type=SOURCE,
            properties={
                **outcome.source.identity(extraction["source"]["extractor_version"]),
                "source_group_id": outcome.source.source_group_id,
                "decision": outcome.final_decision,
            },
        )

        for entity in extraction["entities"]:
            node_id = entity_node_id(entity["id"])
            nodes.setdefault(
                node_id,
                GraphNode(
                    id=node_id,
                    type=ENTITY,
                    properties={"entity_id": entity["id"], "type": entity["type"], "name": entity["name"]},
                ),
            )
            _add(
                edges,
                GraphEdge(
                    subject=node_id,
                    predicate=MENTIONED_IN,
                    object=source_id,
                    state=OBSERVED,
                    provenance=provenance,
                    evidence=entity["evidence"],
                ),
            )

        for relation in extraction["relations"]:
            _add(
                edges,
                GraphEdge(
                    subject=entity_node_id(relation["subject"]),
                    predicate=relation["predicate"],
                    object=entity_node_id(relation["object"]),
                    state=relation["state"],
                    provenance=provenance,
                    evidence=relation["evidence"],
                ),
            )

        for claim in extraction["claims"]:
            node_id = claim_node_id(outcome.source.source_id, claim["claim"])
            nodes[node_id] = GraphNode(
                id=node_id,
                type=CLAIM,
                properties={"claim": claim["claim"], "entity_ids": list(claim["entity_ids"])},
            )
            _add(
                edges,
                GraphEdge(
                    subject=node_id,
                    predicate=STATED_IN,
                    object=source_id,
                    state=OBSERVED,
                    provenance=provenance,
                    evidence=claim["evidence"],
                ),
            )
            for entity_id in claim["entity_ids"]:
                _add(
                    edges,
                    GraphEdge(
                        subject=node_id,
                        predicate=ABOUT,
                        object=entity_node_id(entity_id),
                        state=OBSERVED,
                        provenance=provenance,
                        evidence=claim["evidence"],
                    ),
                )

    return GraphProjection(nodes=tuple(nodes.values()), edges=tuple(edges.values()))


def _add(edges: dict[tuple[str, str, str, str], GraphEdge], edge: GraphEdge) -> None:
    edges.setdefault(edge.key, edge)


def project_vector(outcomes: Iterable[MaterialOutcome]) -> tuple[VectorChunk, ...]:
    """Return the retrievable chunks of every outcome that produced knowledge.

    Chunks are the verified evidence fragments themselves: retrieval that cannot
    quote its own support is retrieval the consumer cannot check.
    """

    chunks: dict[str, VectorChunk] = {}
    for outcome in outcomes:
        extraction = outcome.extraction
        if extraction is None:
            continue
        provenance = provenance_of(outcome)
        for kind, key in ((ENTITY, "entities"), ("relation", "relations"), (CLAIM, "claims")):
            for element in extraction[key]:
                fragment = element["evidence"]["fragment"]
                chunk_id = f"chunk-{_digest(outcome.source.source_id, fragment)}"
                chunks.setdefault(
                    chunk_id,
                    VectorChunk(
                        chunk_id=chunk_id,
                        text=fragment,
                        kind=kind,
                        provenance={
                            **provenance,
                            "evidence_strength": element["evidence"]["evidence_strength"],
                        },
                    ),
                )
    return tuple(chunks.values())
