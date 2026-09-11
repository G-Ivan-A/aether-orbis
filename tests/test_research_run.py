"""End-to-end Research Runs: AM-1 and AM-2 on one codebase."""

from tests import paths as paths  # noqa: F401

import subprocess
import sys
import unittest

import yaml

from aether_orbis.adapters import CorpusFetcher, InMemoryGraphStore, InMemoryVectorIndex
from aether_orbis.context import build_context_package
from aether_orbis.errors import SpecificationError
from aether_orbis.expansion import next_frontier
from aether_orbis.orchestration import ResearchRunOrchestrator
from aether_orbis.representations import entity_node_id
from tools.contract_validation import validate_instance

from tests.acquisition_fixtures import build_pipeline, load_specification
from tests.research_run_fixtures import (
    COMPLETION_MEASURES,
    build_orchestrator,
    load_runtime_configuration,
    run,
)
from tests.support import ACQUISITION, FIXTURES, ROOT, SCHEMAS

EXAMPLE = ROOT / "examples" / "research-runs" / "local_research_run.py"
SINGLE_ITERATION = FIXTURES / "runtime" / "single-iteration.yaml"
CONFLICT_CORPUS = ACQUISITION / "am-2" / "conflict"
ZERO_CORPUS = ACQUISITION / "am-2" / "zero"


def runtime(path):
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


class RunDocumentTests(unittest.TestCase):
    """O-7: the run records what it ran with, processed and decided."""

    @classmethod
    def setUpClass(cls):
        cls.results = {model: run(model) for model in ("am-1", "am-2")}

    def documents(self):
        return {model: result[0].document for model, result in self.results.items()}

    def test_both_run_documents_satisfy_the_contract(self):
        for model, document in self.documents().items():
            with self.subTest(model=model):
                self.assertEqual(
                    [], validate_instance(document, "research-run.schema.json", SCHEMAS)
                )

    def test_the_run_records_the_specification_and_runtime_versions(self):
        document = self.documents()["am-2"]
        specification = load_specification("am-2")
        self.assertEqual(
            {
                "id": specification["specification_id"],
                "version": specification["specification_version"],
            },
            document["specification"],
        )
        configuration = load_runtime_configuration()
        self.assertEqual(
            {
                "id": configuration["runtime_id"],
                "version": configuration["runtime_version"],
            },
            document["runtime_configuration"],
        )

    def test_the_run_records_the_model_adapter_versions_it_executed_with(self):
        versions = self.documents()["am-2"]["model_versions"]
        pipeline = build_pipeline("am-2")
        self.assertEqual(pipeline.extractor.extractor_version, versions["extractor"])
        self.assertEqual(pipeline.parser.parser_version, versions["parser"])
        self.assertIn("extraction_model", versions)

    def test_the_run_records_the_content_hash_of_every_processed_source(self):
        document = self.documents()["am-2"]
        outcomes = self.results["am-2"][0].outcomes
        self.assertEqual(len(outcomes), len(document["processed_sources"]))
        for processed in document["processed_sources"]:
            self.assertRegex(processed["content_hash"], r"^sha256:[a-f0-9]{64}$")

    def test_the_run_records_a_full_decision_for_every_processed_source(self):
        document = self.documents()["am-2"]
        self.assertEqual(
            len(document["processed_sources"]), len(document["decisions"])
        )
        for decision in document["decisions"]:
            self.assertEqual(
                [],
                validate_instance(
                    decision, "qualification-decision.schema.json", SCHEMAS
                ),
            )
            self.assertTrue(decision["rationale"])

    def test_the_run_records_every_iteration_and_the_sources_it_processed(self):
        document = self.documents()["am-2"]
        self.assertEqual(2, len(document["expansion_iterations"]))
        self.assertEqual([0, 1], [i["iteration"] for i in document["expansion_iterations"]])
        self.assertEqual(
            {"expand"}, {i["strategy"] for i in document["expansion_iterations"]}
        )
        processed = [
            source_id
            for iteration in document["expansion_iterations"]
            for source_id in iteration["processed_source_ids"]
        ]
        self.assertEqual(sorted(processed), sorted(set(processed)))

    def test_the_run_records_the_budget_it_actually_consumed(self):
        document = self.documents()["am-2"]
        self.assertEqual(
            {"iterations": 2, "cost_rub": 0.0}, document["consumed_budget"]
        )
        self.assertLessEqual(
            document["consumed_budget"]["iterations"],
            load_runtime_configuration()["budgets"]["max_iterations"],
        )

    def test_the_run_records_a_preservation_decision_for_every_source(self):
        for outcome in self.results["am-2"][0].outcomes:
            self.assertEqual(
                [],
                validate_instance(
                    outcome.record, "preserved-record.schema.json", SCHEMAS
                ),
            )

    def test_every_emitted_event_satisfies_the_telemetry_contract(self):
        for model, (result, _, _, _) in self.results.items():
            with self.subTest(model=model):
                self.assertTrue(result.events)
                for event in result.events:
                    self.assertEqual(
                        [],
                        validate_instance(
                            event, "telemetry-event.schema.json", SCHEMAS
                        ),
                    )


class Am1EndToEndTests(unittest.TestCase):
    """AM-1 Domain Monitoring: an enumerated window with an honest hole in it."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.package, cls.graph, cls.vector = run("am-1")

    def test_the_run_uses_the_enumerate_strategy_it_declared(self):
        self.assertEqual(
            {"enumerate"},
            {i["strategy"] for i in self.result.document["expansion_iterations"]},
        )

    def test_material_that_could_not_be_normalized_lowers_coverage(self):
        self.assertEqual(1, len(self.result.failures))
        self.assertEqual(
            {"window_coverage": 0.75}, self.result.document["outcome"]["coverage"]
        )

    def test_the_incomplete_window_is_reported_and_not_answered(self):
        outcome = self.result.document["outcome"]
        self.assertEqual("PARTIAL", outcome["status"])
        self.assertTrue(outcome["gaps"])
        self.assertIn("could not be normalized", outcome["gaps"][0])

    def test_both_representations_indexed_the_qualified_stream(self):
        self.assertTrue(self.graph.edges)
        self.assertTrue(self.vector.chunks)

    def test_the_context_package_carries_the_gaps_with_the_knowledge(self):
        self.assertEqual("PARTIAL", self.package["status"])
        self.assertTrue(self.package["gaps"])
        self.assertTrue(self.package["claims"])
        for claim in self.package["claims"]:
            self.assertTrue(claim["evidence"]["fragment"])
            self.assertTrue(claim["provenance"]["content_hash"])


class Am2EndToEndTests(unittest.TestCase):
    """AM-2 Entity/Relationship Extraction: the same code, expanding a graph."""

    @classmethod
    def setUpClass(cls):
        cls.result, cls.package, cls.graph, cls.vector = run("am-2")

    def test_the_run_uses_the_expand_strategy_it_declared(self):
        self.assertEqual(
            {"expand"},
            {i["strategy"] for i in self.result.document["expansion_iterations"]},
        )

    def test_expansion_reaches_a_source_no_seed_named_directly(self):
        urls = {outcome.source.canonical_url for outcome in self.result.outcomes}
        self.assertIn("https://registry.example.org/entities/example-registry", urls)

    def test_the_covered_neighborhood_is_sufficient(self):
        outcome = self.result.document["outcome"]
        self.assertEqual("SUFFICIENT", outcome["status"])
        self.assertEqual([], outcome["gaps"])
        self.assertEqual([], outcome["recommended_expansion"])

    def test_the_graph_traverses_from_an_entity_back_to_its_sources(self):
        provenance = self.graph.provenance(entity_node_id("org.example-registry"))
        self.assertTrue(provenance)
        for item in provenance:
            self.assertTrue(item["canonical_url"].startswith("https://"))

    def test_the_vector_index_retrieves_the_same_knowledge_by_text(self):
        found = self.vector.search("partnered with Example Registry", limit=1)
        self.assertEqual(1, len(found))
        self.assertIn("partnered with", found[0].text)

    def test_the_context_package_reports_both_representations(self):
        self.assertEqual(
            {
                "graph": {"nodes": len(self.graph.nodes), "edges": len(self.graph.edges)},
                "vector": {"chunks": len(self.vector.chunks)},
            },
            self.package["representations"],
        )


class SameCodebaseTests(unittest.TestCase):
    """The two models differ in the specification, not in the pipeline."""

    def test_both_models_run_through_the_same_orchestrator_class(self):
        for model in ("am-1", "am-2"):
            with self.subTest(model=model):
                self.assertIsInstance(
                    build_orchestrator(model), ResearchRunOrchestrator
                )

    def test_the_strategy_recorded_by_each_run_comes_from_its_specification(self):
        for model in ("am-1", "am-2"):
            with self.subTest(model=model):
                declared = load_specification(model)["scope"]["strategy"]
                document = build_orchestrator(model).execute().document
                self.assertEqual(
                    {declared},
                    {i["strategy"] for i in document["expansion_iterations"]},
                )

    def test_only_the_expand_strategy_grows_its_own_frontier(self):
        result = build_pipeline("am-1").run()
        self.assertEqual(
            (), next_frontier(load_specification("am-1"), result.outcomes)
        )


class IdempotencyTests(unittest.TestCase):
    def test_repeating_the_run_produces_the_same_document(self):
        first = build_orchestrator("am-2").execute().document
        second = build_orchestrator("am-2").execute().document
        self.assertEqual(first, second)

    def test_a_source_reachable_from_two_seeds_is_decided_once(self):
        result = build_orchestrator("am-2").execute()
        source_ids = [outcome.source.source_id for outcome in result.outcomes]
        self.assertEqual(sorted(source_ids), sorted(set(source_ids)))

    def test_reindexing_a_repeated_run_leaves_both_stores_unchanged(self):
        graph, vector = InMemoryGraphStore(), InMemoryVectorIndex()
        for _ in range(2):
            build_orchestrator(
                "am-2", graph_store=graph, vector_index=vector
            ).execute()
            sizes = (len(graph.nodes), len(graph.edges), len(vector.chunks))
        graph_again, vector_again = InMemoryGraphStore(), InMemoryVectorIndex()
        build_orchestrator(
            "am-2", graph_store=graph_again, vector_index=vector_again
        ).execute()
        self.assertEqual(
            sizes,
            (len(graph_again.nodes), len(graph_again.edges), len(vector_again.chunks)),
        )


class RepresentationIndependenceTests(unittest.TestCase):
    """Disabling one representation must not break the other, or the run."""

    def test_a_run_without_a_graph_store_still_completes_and_retrieves(self):
        vector = InMemoryVectorIndex()
        result = build_orchestrator("am-2", vector_index=vector).execute()
        self.assertEqual("SUFFICIENT", result.status)
        self.assertTrue(vector.search("Example Registry"))

    def test_a_run_without_a_vector_index_still_completes_and_traverses(self):
        graph = InMemoryGraphStore()
        result = build_orchestrator("am-2", graph_store=graph).execute()
        self.assertEqual("SUFFICIENT", result.status)
        self.assertTrue(graph.provenance(entity_node_id("org.example-organization")))

    def test_a_run_with_neither_representation_produces_the_same_document(self):
        with_both = run("am-2")[0].document
        without = build_orchestrator("am-2").execute().document
        self.assertEqual(with_both, without)

    def test_only_the_qualified_stream_reaches_the_representations(self):
        graph = InMemoryGraphStore()
        result = build_orchestrator("am-1", graph_store=graph).execute()
        rejected = {
            outcome.source.source_id
            for outcome in result.outcomes
            if outcome.final_decision == "REJECTED"
        }
        self.assertTrue(rejected)
        indexed = {
            edge.provenance["source_id"] for edge in graph.edges.values()
        }
        self.assertEqual(set(), rejected & indexed)


class TerminationTests(unittest.TestCase):
    def test_an_exhausted_budget_ends_the_run_as_exhausted(self):
        result = build_orchestrator(
            "am-2", runtime_configuration=runtime(SINGLE_ITERATION)
        ).execute()
        self.assertEqual("EXHAUSTED", result.status)
        self.assertEqual(1, result.document["consumed_budget"]["iterations"])
        self.assertTrue(result.document["outcome"]["recommended_expansion"])

    def test_the_budget_comes_from_the_runtime_configuration_alone(self):
        self.assertNotIn("budgets", load_specification("am-2")["termination"])
        self.assertIn("budgets", load_runtime_configuration())

    def test_a_runtime_configuration_without_budgets_is_an_error(self):
        configuration = dict(load_runtime_configuration())
        del configuration["budgets"]
        with self.assertRaises(SpecificationError):
            build_orchestrator("am-2", runtime_configuration=configuration)

    def test_a_run_that_qualifies_nothing_ends_as_zero_without_an_answer(self):
        graph, vector = InMemoryGraphStore(), InMemoryVectorIndex()
        result = build_orchestrator(
            "am-2",
            graph_store=graph,
            vector_index=vector,
            fetcher=CorpusFetcher.from_directory(ZERO_CORPUS),
        ).execute()
        self.assertEqual("ZERO", result.status)
        self.assertTrue(result.document["outcome"]["gaps"])
        self.assertEqual({}, graph.nodes)
        self.assertEqual({}, vector.chunks)

        package = build_context_package(result.document, result.qualified)
        self.assertEqual([], package["claims"])
        self.assertEqual([], package["sources"])
        self.assertTrue(package["rationale"])

    def test_contradicting_source_groups_end_the_run_as_conflict(self):
        result = build_orchestrator(
            "am-2", fetcher=CorpusFetcher.from_directory(CONFLICT_CORPUS)
        ).execute()
        self.assertEqual("CONFLICT", result.status)
        conflict = result.document["outcome"]["conflicts"][0]
        self.assertEqual(2, len(set(conflict["source_group_ids"])))

    def test_all_five_statuses_are_reachable_from_the_fixtures(self):
        statuses = {
            run("am-1")[0].status,
            run("am-2")[0].status,
            build_orchestrator(
                "am-2", runtime_configuration=runtime(SINGLE_ITERATION)
            ).execute().status,
            build_orchestrator(
                "am-2", fetcher=CorpusFetcher.from_directory(ZERO_CORPUS)
            ).execute().status,
            build_orchestrator(
                "am-2", fetcher=CorpusFetcher.from_directory(CONFLICT_CORPUS)
            ).execute().status,
        }
        self.assertEqual(
            {"SUFFICIENT", "PARTIAL", "ZERO", "CONFLICT", "EXHAUSTED"}, statuses
        )


class CompletionConfigurationTests(unittest.TestCase):
    def test_the_evaluator_measures_only_the_declared_dimensions(self):
        for model in ("am-1", "am-2"):
            with self.subTest(model=model):
                declared = set(load_specification(model)["termination"]["completion_dimensions"])
                measured = set(run(model)[0].document["outcome"]["coverage"])
                self.assertEqual(declared, measured)

    def test_an_unmeasured_dimension_becomes_a_gap_rather_than_a_pass(self):
        from aether_orbis.adapters import ConfiguredCompletionEvaluator

        orchestrator = build_orchestrator("am-2")
        orchestrator.completion = ConfiguredCompletionEvaluator(
            measures={"neighborhood_completeness": COMPLETION_MEASURES["neighborhood_completeness"]}
        )
        outcome = orchestrator.execute().document["outcome"]
        self.assertIn(
            "new_entity_saturation was never measured",
            " ".join(outcome["gaps"]),
        )


class ExampleScriptTests(unittest.TestCase):
    def test_one_command_runs_both_models_end_to_end(self):
        completed = subprocess.run(
            [sys.executable, str(EXAMPLE)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(ROOT),
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        for expected in ("am-1: PARTIAL", "am-2: SUFFICIENT", "context package"):
            self.assertIn(expected, completed.stdout)


if __name__ == "__main__":
    unittest.main()
