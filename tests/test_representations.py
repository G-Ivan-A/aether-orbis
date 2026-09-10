"""Two parallel representations of one qualified knowledge stream."""

from tests import paths as paths  # noqa: F401

import tempfile
import unittest
from pathlib import Path

from aether_orbis.adapters import (
    CorpusFetcher,
    InMemoryGraphStore,
    InMemoryVectorIndex,
    KuzuGraphStore,
)
from aether_orbis.ports import GraphStore
from aether_orbis.representations import (
    GraphEdge,
    entity_node_id,
    project_graph,
    project_vector,
    provenance_of,
    source_node_id,
)

from tests.acquisition_fixtures import build_pipeline
from tests.support import ACQUISITION

ORGANIZATION = entity_node_id("org.example-organization")
REGISTRY = entity_node_id("org.example-registry")


def qualified_stream(model="am-2", **overrides):
    """Return the qualified and conditional outcomes of one fixture run."""

    result = build_pipeline(model, **overrides).run()
    return tuple(
        outcome
        for outcome in result.outcomes
        if outcome.final_decision in ("QUALIFIED", "CONDITIONAL")
    )


class GraphProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stream = qualified_stream()
        cls.projection = project_graph(cls.stream)

    def test_every_edge_carries_the_identity_of_the_source_it_came_from(self):
        for edge in self.projection.edges:
            self.assertEqual(
                {
                    "source_id",
                    "source_group_id",
                    "canonical_url",
                    "content_hash",
                    "retrieved_at",
                    "decision",
                    "decision_id",
                    "evaluation_id",
                },
                set(edge.provenance),
            )

    def test_relation_edges_keep_the_state_the_extractor_observed(self):
        states = {
            edge.state
            for edge in self.projection.edges
            if edge.predicate == "partnered_with"
        }
        self.assertEqual({"OBSERVED"}, states)

    def test_the_relation_between_the_two_entities_is_present(self):
        related = [
            edge
            for edge in self.projection.edges
            if (edge.subject, edge.object) == (ORGANIZATION, REGISTRY)
        ]
        self.assertTrue(related)

    def test_projecting_the_same_stream_twice_produces_the_same_graph(self):
        again = project_graph(self.stream)
        self.assertEqual(
            [edge.key for edge in self.projection.edges], [edge.key for edge in again.edges]
        )
        self.assertEqual(
            [node.id for node in self.projection.nodes], [node.id for node in again.nodes]
        )

    def test_material_that_never_reached_extraction_is_not_projected(self):
        rejected = build_pipeline("am-2").run().by_decision("REJECTED")
        self.assertTrue(rejected)
        self.assertEqual((), project_graph(rejected).edges)


class GraphStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryGraphStore()
        self.stream = qualified_stream()
        self.store.index_graph(project_graph(self.stream))

    def test_indexing_the_same_projection_twice_changes_nothing(self):
        nodes, edges = len(self.store.nodes), len(self.store.edges)
        self.store.index_graph(project_graph(self.stream))
        self.assertEqual((nodes, edges), (len(self.store.nodes), len(self.store.edges)))

    def test_an_entity_traces_back_to_every_source_that_mentioned_it(self):
        provenance = self.store.provenance(ORGANIZATION)
        self.assertTrue(provenance)
        expected = {outcome.source.canonical_url for outcome in self.stream}
        self.assertEqual(expected, {item["canonical_url"] for item in provenance})

    def test_traversal_reaches_the_neighbour_and_its_source(self):
        neighbours = self.store.neighbours(ORGANIZATION)
        self.assertIn(REGISTRY, neighbours)
        self.assertTrue(
            any(neighbour.startswith("source:") for neighbour in neighbours),
            neighbours,
        )

    def test_evidence_stays_reachable_from_the_graph(self):
        fragments = [item["fragment"] for item in self.store.evidence(ORGANIZATION)]
        self.assertTrue(fragments)
        texts = [outcome.source.text for outcome in self.stream]
        for fragment in fragments:
            self.assertTrue(any(fragment in text for text in texts), fragment)


class VectorProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stream = qualified_stream()
        cls.chunks = project_vector(cls.stream)

    def test_every_chunk_quotes_its_source_verbatim(self):
        by_source = {outcome.source.source_id: outcome.source for outcome in self.stream}
        for chunk in self.chunks:
            source = by_source[chunk.provenance["source_id"]]
            self.assertIn(chunk.text, source.text)

    def test_a_chunk_traces_back_to_the_decision_that_qualified_it(self):
        for chunk in self.chunks:
            self.assertIn(chunk.provenance["decision"], ("QUALIFIED", "CONDITIONAL"))
            self.assertTrue(chunk.provenance["decision_id"])

    def test_projecting_the_same_stream_twice_produces_the_same_chunks(self):
        self.assertEqual(
            [chunk.chunk_id for chunk in self.chunks],
            [chunk.chunk_id for chunk in project_vector(self.stream)],
        )


class VectorIndexTests(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryVectorIndex()
        self.stream = qualified_stream()
        self.index.index_chunks(project_vector(self.stream))

    def test_indexing_the_same_chunks_twice_changes_nothing(self):
        count = len(self.index.chunks)
        self.index.index_chunks(project_vector(self.stream))
        self.assertEqual(count, len(self.index.chunks))

    def test_retrieval_returns_evidence_with_provenance(self):
        found = self.index.search("partnered with Example Registry", limit=1)
        self.assertEqual(1, len(found))
        self.assertIn("partnered with", found[0].text)
        self.assertTrue(found[0].provenance["content_hash"].startswith("sha256:"))

    def test_a_query_that_shares_no_word_returns_nothing(self):
        self.assertEqual((), self.index.search("завод турбин Нижний Тагил"))


class IndependenceTests(unittest.TestCase):
    """Neither representation is a stage of the other (ADR-001, decision 4)."""

    def setUp(self):
        self.stream = qualified_stream()

    def test_the_vector_index_works_without_any_graph_store(self):
        index = InMemoryVectorIndex()
        index.index_chunks(project_vector(self.stream))
        self.assertTrue(index.search("Example Registry"))

    def test_the_graph_store_works_without_any_vector_index(self):
        store = InMemoryGraphStore()
        store.index_graph(project_graph(self.stream))
        self.assertTrue(store.provenance(ORGANIZATION))

    def test_both_representations_cover_the_same_source_identities(self):
        store = InMemoryGraphStore()
        store.index_graph(project_graph(self.stream))
        index = InMemoryVectorIndex()
        index.index_chunks(project_vector(self.stream))

        graph_sources = {
            node.id for node in store.nodes.values() if node.type == "source"
        }
        vector_sources = {
            source_node_id(chunk.provenance["source_id"])
            for chunk in index.chunks.values()
        }
        self.assertEqual(graph_sources, vector_sources)

    def test_each_representation_can_be_rebuilt_from_the_stream_alone(self):
        """Neither projection reads the other's output."""

        self.assertEqual(
            [chunk.chunk_id for chunk in project_vector(self.stream)],
            [chunk.chunk_id for chunk in project_vector(self.stream)],
        )
        self.assertTrue(project_graph(self.stream).edges)


class ProvenanceTests(unittest.TestCase):
    def test_a_triage_rejection_still_carries_its_decision(self):
        rejected = build_pipeline("am-2").run().by_decision("REJECTED")[0]
        provenance = provenance_of(rejected)
        self.assertEqual("REJECTED", provenance["decision"])
        self.assertTrue(provenance["decision_id"])


class GraphEdgeTests(unittest.TestCase):
    def test_the_same_relation_from_two_sources_stays_two_edges(self):
        """Agreement between independent sources is evidence, not duplication."""

        edges = {}
        for source_id in ("source-a", "source-b"):
            edge = GraphEdge(
                subject=ORGANIZATION,
                predicate="partnered_with",
                object=REGISTRY,
                state="OBSERVED",
                provenance={"source_id": source_id},
            )
            edges[edge.key] = edge
        self.assertEqual(2, len(edges))


class ConflictingCorpusTests(unittest.TestCase):
    def test_contradicting_sources_produce_two_states_for_one_relation(self):
        stream = qualified_stream(
            fetcher=CorpusFetcher.from_directory(ACQUISITION / "am-2" / "conflict")
        )
        states = {
            edge.state
            for edge in project_graph(stream).edges
            if edge.predicate == "partnered_with"
        }
        self.assertEqual({"OBSERVED", "CONTRADICTED"}, states)


if __name__ == "__main__":
    unittest.main()


class KuzuGraphStoreTests(unittest.TestCase):
    """The embedded engine of ADR-001 implements the same port as the default."""

    def setUp(self):
        try:
            import kuzu  # noqa: F401
        except ImportError:
            self.skipTest("optional dependency 'kuzu' is not installed")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = KuzuGraphStore(str(Path(self.directory.name) / "db"))
        self.projection = project_graph(qualified_stream())

    def test_it_satisfies_the_graph_store_port(self):
        self.assertIsInstance(self.store, GraphStore)

    def test_it_walks_back_from_an_entity_to_its_sources(self):
        self.store.index_graph(self.projection)
        provenance = self.store.provenance(entity_node_id("org.example-organization"))
        self.assertTrue(provenance)
        for item in provenance:
            self.assertTrue(item["content_hash"].startswith("sha256:"))

    def test_reindexing_the_same_run_changes_nothing(self):
        self.store.index_graph(self.projection)
        first = self.store.provenance(entity_node_id("org.example-organization"))
        self.store.index_graph(self.projection)
        self.assertEqual(first, self.store.provenance(entity_node_id("org.example-organization")))

    def test_it_returns_the_same_provenance_as_the_default_store(self):
        self.store.index_graph(self.projection)
        default = InMemoryGraphStore()
        default.index_graph(self.projection)
        node = entity_node_id("org.example-organization")
        self.assertEqual(
            [item["source_id"] for item in default.provenance(node)],
            [item["source_id"] for item in self.store.provenance(node)],
        )
