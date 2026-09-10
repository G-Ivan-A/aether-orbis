#!/usr/bin/env python3
"""Compare graph-store candidates on the AM-2 knowledge graph of the fixtures.

ADR-001 deferred the choice of a graph store to the moment there was a real
graph to measure. The AM-2 Research Run now produces one, so this experiment
runs the *same* projection through every candidate that implements the
``GraphStore`` port and measures what the port actually asks for:

1. contract fitness — index a projection, walk a neighbourhood, and walk back
   from a node to the provenance of every source that supports it;
2. idempotency — re-indexing the same run must not change the stored graph,
   because a repeated Research Run is a normal operation, not an error;
3. cost — indexing and traversal time on the fixture graph and on a synthetic
   graph large enough for the difference between candidates to be visible.

Run (no network, no credentials, nothing written into the repository):

    python3 experiments/graph-store/traversal_benchmark.py
    python3 experiments/graph-store/traversal_benchmark.py --scale 20000 --only stdlib

The Kuzu write path measured here is a ``MERGE`` per element rather than a bulk
``COPY``, because the port requires re-indexing a repeated run to be idempotent
and ``COPY`` is not; its indexing numbers are therefore the cost of that
guarantee, not the engine's peak load throughput.

Candidates whose optional dependency is absent are reported as ``n/a`` rather
than failing, so the experiment stays reproducible on a stdlib-only checkout.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples" / "research-runs"))

from aether_orbis.adapters import InMemoryGraphStore, KuzuGraphStore  # noqa: E402
from aether_orbis.representations import (  # noqa: E402
    GraphEdge,
    GraphNode,
    GraphProjection,
    entity_node_id,
    project_graph,
)
from local_research_run import run  # noqa: E402

PROBE = entity_node_id("org.example-organization")


class SqliteGraphStore:
    """stdlib baseline: edges in SQLite, traversal by recursive CTE.

    The point of the baseline is to show what the project already has for free.
    Any candidate that needs a dependency has to be better than this on the
    operations the port declares, or it is not worth the dependency.
    """

    def __init__(self, database_path: str) -> None:
        self.connection = sqlite3.connect(database_path)
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS node(
                id TEXT PRIMARY KEY, type TEXT, properties TEXT);
            CREATE TABLE IF NOT EXISTS edge(
                subject TEXT, predicate TEXT, object TEXT, state TEXT,
                source_id TEXT, provenance TEXT, evidence TEXT,
                PRIMARY KEY (subject, predicate, object, source_id));
            CREATE INDEX IF NOT EXISTS edge_subject ON edge(subject);
            CREATE INDEX IF NOT EXISTS edge_object ON edge(object);
            """
        )

    def index_graph(self, projection: GraphProjection) -> None:
        with self.connection:
            self.connection.executemany(
                "INSERT OR REPLACE INTO node VALUES (?, ?, ?)",
                [
                    (n.id, n.type, json.dumps(dict(n.properties), sort_keys=True))
                    for n in projection.nodes
                ],
            )
            self.connection.executemany(
                "INSERT OR REPLACE INTO edge VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        e.subject,
                        e.predicate,
                        e.object,
                        e.state,
                        e.provenance["source_id"],
                        json.dumps(dict(e.provenance), sort_keys=True),
                        json.dumps(dict(e.evidence) if e.evidence else {}, sort_keys=True),
                    )
                    for e in projection.edges
                ],
            )

    def neighbours(self, node_id: str, *, depth: int = 1) -> tuple[str, ...]:
        rows = self.connection.execute(
            """
            WITH RECURSIVE reachable(id, hops) AS (
                SELECT ?, 0
                UNION
                SELECT CASE WHEN e.subject = r.id THEN e.object ELSE e.subject END,
                       r.hops + 1
                FROM edge e JOIN reachable r
                  ON e.subject = r.id OR e.object = r.id
                WHERE r.hops < ?
            )
            SELECT DISTINCT id FROM reachable WHERE id <> ? ORDER BY id
            """,
            (node_id, depth, node_id),
        ).fetchall()
        return tuple(row[0] for row in rows)

    def provenance(self, node_id: str) -> tuple[dict[str, Any], ...]:
        rows = self.connection.execute(
            "SELECT DISTINCT provenance FROM edge WHERE subject = ? OR object = ?"
            " ORDER BY source_id",
            (node_id, node_id),
        ).fetchall()
        found: dict[str, dict[str, Any]] = {}
        for (blob,) in rows:
            provenance = json.loads(blob)
            found.setdefault(provenance["source_id"], provenance)
        return tuple(found[key] for key in sorted(found))

    def size(self) -> tuple[int, int]:
        nodes = self.connection.execute("SELECT count(*) FROM node").fetchone()[0]
        edges = self.connection.execute("SELECT count(*) FROM edge").fetchone()[0]
        return nodes, edges


def kuzu_size(store: KuzuGraphStore) -> tuple[int, int]:
    def scalar(query: str) -> int:
        result = store.connect().execute(query)
        return int(result.get_next()[0]) if result.has_next() else 0

    return (
        scalar("MATCH (n:Node) RETURN count(n)"),
        scalar("MATCH ()-[e:Edge]->() RETURN count(e)"),
    )


def kuzu_neighbours(store: KuzuGraphStore, node_id: str, *, depth: int = 1):
    result = store.connect().execute(
        f"MATCH (a:Node)-[e:Edge*1..{depth}]-(b:Node) WHERE a.id = $id "
        "RETURN DISTINCT b.id",
        {"id": node_id},
    )
    found = set()
    while result.has_next():
        found.add(result.get_next()[0])
    return tuple(sorted(found - {node_id}))


@dataclass
class Candidate:
    """One graph-store candidate and the three operations the port declares."""

    name: str
    build: Callable[[Path], Any]
    neighbours: Callable[[Any, str, int], tuple[str, ...]]
    size: Callable[[Any], tuple[int, int]]
    note: str = ""


CANDIDATES = (
    Candidate(
        name="stdlib in-memory",
        build=lambda _: InMemoryGraphStore(),
        neighbours=lambda store, node, depth: store.neighbours(node, depth=depth),
        size=lambda store: (len(store.nodes), len(store.edges)),
        note="CI default, no dependency, no persistence",
    ),
    Candidate(
        name="stdlib SQLite CTE",
        build=lambda tmp: SqliteGraphStore(str(tmp / "graph.sqlite3")),
        neighbours=lambda store, node, depth: store.neighbours(node, depth=depth),
        size=lambda store: store.size(),
        note="persistent, no dependency, traversal in SQL",
    ),
    Candidate(
        name="kuzu (embedded)",
        build=lambda tmp: KuzuGraphStore(str(tmp / "kuzu-db")),
        neighbours=lambda store, node, depth: kuzu_neighbours(store, node, depth=depth),
        size=kuzu_size,
        note="embedded property graph, Cypher, idempotent MERGE per statement",
    ),
)


def synthetic(projection: GraphProjection, scale: int) -> GraphProjection:
    """Return *projection* grown to roughly *scale* edges by cloning its shape.

    The fixture graph is deliberately small; the shape of the AM-2 graph — a hub
    entity, its sources and their claims — is what gets repeated, so the larger
    graph exercises the same traversal, not an artificial topology.
    """

    if not projection.edges:
        return projection
    nodes = list(projection.nodes)
    edges = list(projection.edges)
    copies = max(scale // max(len(projection.edges), 1), 1)
    for index in range(1, copies):
        suffix = f"#{index}"
        nodes.extend(
            GraphNode(id=node.id + suffix, type=node.type, properties=node.properties)
            for node in projection.nodes
        )
        edges.extend(
            GraphEdge(
                subject=edge.subject + suffix,
                predicate=edge.predicate,
                object=edge.object + suffix,
                state=edge.state,
                provenance={**edge.provenance, "source_id": edge.provenance["source_id"] + suffix},
                evidence=edge.evidence,
            )
            for edge in projection.edges
        )
        # One bridge per copy keeps the whole graph connected through the hub.
        edges.append(
            GraphEdge(
                subject=PROBE,
                predicate="same_as",
                object=PROBE + suffix,
                state="OBSERVED",
                provenance={**projection.edges[0].provenance, "source_id": f"synthetic{suffix}"},
                evidence=None,
            )
        )
    return GraphProjection(nodes=tuple(nodes), edges=tuple(edges))


def elapsed(operation: Callable[[], Any]) -> tuple[float, Any]:
    started = time.perf_counter()
    value = operation()
    return (time.perf_counter() - started) * 1000, value


@dataclass
class Report:
    name: str
    note: str
    index_ms: float = 0.0
    reindex_ms: float = 0.0
    neighbours_ms: float = 0.0
    provenance_ms: float = 0.0
    idempotent: str = "-"
    provenance_ok: str = "-"
    neighbours: int = 0
    failure: str = ""
    sizes: tuple[int, int] = field(default=(0, 0))


def measure(candidate: Candidate, projection: GraphProjection, depth: int) -> Report:
    report = Report(name=candidate.name, note=candidate.note)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            store = candidate.build(Path(tmp))
            report.index_ms, _ = elapsed(lambda: store.index_graph(projection))
            first = candidate.size(store)
            report.reindex_ms, _ = elapsed(lambda: store.index_graph(projection))
            report.sizes = candidate.size(store)
            report.idempotent = "yes" if report.sizes == first else "no"
            report.neighbours_ms, found = elapsed(
                lambda: candidate.neighbours(store, PROBE, depth)
            )
            report.neighbours = len(found)
            report.provenance_ms, provenance = elapsed(lambda: store.provenance(PROBE))
            report.provenance_ok = (
                "yes"
                if provenance
                and all({"source_id", "content_hash", "canonical_url"} <= set(item) for item in provenance)
                else "no"
            )
        except Exception as error:  # noqa: BLE001 - a missing candidate is a result
            report.failure = str(error).splitlines()[0][:70]
    return report


def print_table(title: str, reports: list[Report]) -> None:
    print(f"\n{title}")
    print(
        f"{'candidate':<20} {'index ms':>9} {'reindex':>9} {'neigh ms':>9} "
        f"{'prov ms':>9} {'idem':>5} {'prov':>5} {'nodes':>7} {'edges':>7}"
    )
    for report in reports:
        if report.failure:
            print(f"{report.name:<20} {'n/a':>9}  ({report.failure})")
            continue
        print(
            f"{report.name:<20} {report.index_ms:>9.1f} {report.reindex_ms:>9.1f} "
            f"{report.neighbours_ms:>9.1f} {report.provenance_ms:>9.1f} "
            f"{report.idempotent:>5} {report.provenance_ok:>5} "
            f"{report.sizes[0]:>7} {report.sizes[1]:>7}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=int, default=500, help="target edge count")
    parser.add_argument("--depth", type=int, default=2, help="traversal depth")
    parser.add_argument(
        "--only",
        default="",
        help="measure only the candidates whose name contains this substring",
    )
    args = parser.parse_args()

    candidates = [c for c in CANDIDATES if args.only in c.name]
    result, _, _, _ = run("am-2")
    projection = project_graph(result.qualified)
    print(
        f"AM-2 run: status={result.status}, qualified sources={len(result.qualified)}, "
        f"graph={len(projection.nodes)} nodes / {len(projection.edges)} edges"
    )

    print_table(
        "fixture graph (the graph a Phase 1 Research Run actually produces)",
        [measure(candidate, projection, args.depth) for candidate in candidates],
    )
    grown = synthetic(projection, args.scale)
    print_table(
        f"synthetic graph ({len(grown.nodes)} nodes / {len(grown.edges)} edges)",
        [measure(candidate, grown, args.depth) for candidate in candidates],
    )
    print("\nNothing was written outside the temporary directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
