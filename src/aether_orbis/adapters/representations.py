"""Offline graph and vector adapters.

The defaults are in-memory and dependency free so that tests and CI never need a
server, a database file or a model download. ``KuzuGraphStore`` is the optional
production-shaped adapter for the embedded graph engine selected in ADR-001; it
imports its dependency lazily, exactly like ``TrafilaturaParser``, so the core
keeps passing ``PortIsolationTests``.

Both stores are independent by construction: neither imports the other and
neither is required for the other to work, which is what
``docs/adr/2026-08-adr-001-tech-stack.md`` (4) means by parallel representations.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from aether_orbis.representations import (
    GraphEdge,
    GraphNode,
    GraphProjection,
    VectorChunk,
)

TOKEN = re.compile(r"[0-9a-zа-яё]+")


def tokenize(text: str) -> tuple[str, ...]:
    """Return the lowercased word tokens of *text*."""

    return tuple(TOKEN.findall(text.lower()))


@dataclass
class InMemoryGraphStore:
    """Stdlib graph store: adjacency plus provenance, no server involved.

    Phase 1 needs three operations from the graph representation — index,
    traverse a neighbourhood and walk back to the source — and all three are
    expressible over plain dictionaries. The store is the CI default; the
    embedded engine below implements the same port for larger graphs.
    """

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: dict[tuple[str, str, str, str], GraphEdge] = field(default_factory=dict)

    def index_graph(self, projection: GraphProjection) -> None:
        """Index *projection*; re-indexing the same run changes nothing."""

        for node in projection.nodes:
            self.nodes[node.id] = node
        for edge in projection.edges:
            self.edges[edge.key] = edge

    def neighbours(self, node_id: str, *, depth: int = 1) -> tuple[str, ...]:
        """Return the node ids reachable from *node_id* within *depth* hops."""

        seen = {node_id}
        frontier = {node_id}
        for _ in range(max(depth, 0)):
            nxt: set[str] = set()
            for edge in self.edges.values():
                if edge.subject in frontier:
                    nxt.add(edge.object)
                if edge.object in frontier:
                    nxt.add(edge.subject)
            frontier = nxt - seen
            seen |= nxt
            if not frontier:
                break
        return tuple(sorted(seen - {node_id}))

    def provenance(self, node_id: str) -> tuple[dict[str, Any], ...]:
        """Return the provenance of every edge that touches *node_id*."""

        found: dict[str, dict[str, Any]] = {}
        for edge in self.edges.values():
            if node_id not in (edge.subject, edge.object):
                continue
            found.setdefault(edge.provenance["source_id"], dict(edge.provenance))
        return tuple(found[key] for key in sorted(found))

    def evidence(self, node_id: str) -> tuple[dict[str, Any], ...]:
        """Return the evidence backing every edge that touches *node_id*."""

        return tuple(
            dict(edge.evidence)
            for _, edge in sorted(self.edges.items())
            if edge.evidence is not None and node_id in (edge.subject, edge.object)
        )


@dataclass
class KuzuGraphStore:
    """Embedded graph store backed by Kuzu, the engine chosen in ADR-001.

    The dependency is imported on first use and the database path is supplied by
    the caller, so importing this module never requires Kuzu and never creates a
    file. Runtime databases stay outside the repository (CONTRIBUTING).
    """

    database_path: str
    _connection: Any = field(default=None, init=False, repr=False)

    def connect(self) -> Any:
        """Return the Kuzu connection, creating the schema on first use."""

        if self._connection is not None:
            return self._connection
        try:
            import kuzu
        except ImportError as error:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "KuzuGraphStore needs the optional 'kuzu' package; the in-memory "
                "store is the dependency-free default."
            ) from error
        connection = kuzu.Connection(kuzu.Database(self.database_path))
        connection.execute(
            "CREATE NODE TABLE IF NOT EXISTS Node("
            "id STRING, type STRING, properties STRING, PRIMARY KEY (id))"
        )
        connection.execute(
            "CREATE REL TABLE IF NOT EXISTS Edge(FROM Node TO Node, "
            "predicate STRING, state STRING, source_id STRING, provenance STRING, "
            "evidence STRING)"
        )
        self._connection = connection
        return connection

    def index_graph(self, projection: GraphProjection) -> None:
        """Index *projection* into the embedded database idempotently."""

        import json

        connection = self.connect()
        for node in projection.nodes:
            connection.execute(
                "MERGE (n:Node {id: $id}) SET n.type = $type, n.properties = $properties",
                {
                    "id": node.id,
                    "type": node.type,
                    "properties": json.dumps(dict(node.properties), sort_keys=True),
                },
            )
        for edge in projection.edges:
            connection.execute(
                "MATCH (s:Node {id: $subject}), (o:Node {id: $object}) "
                "MERGE (s)-[e:Edge {predicate: $predicate, source_id: $source_id}]->(o) "
                "SET e.state = $state, e.provenance = $provenance, e.evidence = $evidence",
                {
                    "subject": edge.subject,
                    "object": edge.object,
                    "predicate": edge.predicate,
                    "source_id": edge.provenance["source_id"],
                    "state": edge.state,
                    "provenance": json.dumps(dict(edge.provenance), sort_keys=True),
                    "evidence": json.dumps(
                        dict(edge.evidence) if edge.evidence else {}, sort_keys=True
                    ),
                },
            )

    def provenance(self, node_id: str) -> tuple[dict[str, Any], ...]:
        """Return the provenance of every edge that touches *node_id*."""

        import json

        result = self.connect().execute(
            "MATCH (a:Node)-[e:Edge]->(b:Node) "
            "WHERE a.id = $id OR b.id = $id RETURN DISTINCT e.provenance",
            {"id": node_id},
        )
        found = {}
        while result.has_next():
            provenance = json.loads(result.get_next()[0])
            found.setdefault(provenance["source_id"], provenance)
        return tuple(found[key] for key in sorted(found))


@dataclass
class InMemoryVectorIndex:
    """Deterministic bag-of-words retrieval over evidence chunks.

    Phase 1 needs retrieval to be reproducible and offline more than it needs it
    to be semantic, so similarity is cosine over token counts. Swapping in a real
    embedding model is an adapter change: the port and the chunks stay the same.
    """

    chunks: dict[str, VectorChunk] = field(default_factory=dict)
    _vectors: dict[str, Counter[str]] = field(default_factory=dict, repr=False)

    def index_chunks(self, chunks: Iterable[VectorChunk]) -> None:
        """Index *chunks*; re-indexing the same chunk ids changes nothing."""

        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk
            self._vectors[chunk.chunk_id] = Counter(tokenize(chunk.text))

    def search(self, query: str, limit: int = 5) -> tuple[VectorChunk, ...]:
        """Return the chunks most similar to *query*, best match first."""

        wanted = Counter(tokenize(query))
        scored = [
            (score, chunk_id)
            for chunk_id in sorted(self.chunks)
            if (score := _cosine(wanted, self._vectors[chunk_id])) > 0.0
        ]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return tuple(self.chunks[chunk_id] for _, chunk_id in scored[:limit])

    def by_source(self, source_id: str) -> tuple[VectorChunk, ...]:
        """Return every chunk that traces back to *source_id*."""

        return tuple(
            self.chunks[chunk_id]
            for chunk_id in sorted(self.chunks)
            if self.chunks[chunk_id].provenance["source_id"] == source_id
        )


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    shared = set(left) & set(right)
    if not shared:
        return 0.0
    dot = sum(left[token] * right[token] for token in shared)
    norm = math.sqrt(sum(value * value for value in left.values()))
    norm *= math.sqrt(sum(value * value for value in right.values()))
    return round(dot / norm, 6) if norm else 0.0
