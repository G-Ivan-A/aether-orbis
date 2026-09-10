"""Local end-to-end runs: a specification in, qualified knowledge out."""

from tests import paths as paths  # noqa: F401

import subprocess
import sys
import unittest
from pathlib import Path

from aether_orbis.adapters import ConfiguredEvaluator, metadata_score
from aether_orbis.errors import SpecificationError
from aether_orbis.evaluation import apply_decision_policy, match_decision_rule
from aether_orbis.model import Measurement
from aether_orbis.ports import CollectingTelemetrySink
from tools.contract_validation import validate_instance

from tests.acquisition_fixtures import build_pipeline, load_specification, run
from tests.support import ROOT, SCHEMAS

EXAMPLE = ROOT / "examples" / "acquisition" / "local_acquisition_run.py"


class SpecificationFixtureTests(unittest.TestCase):
    def test_both_fixture_specifications_satisfy_the_contract(self):
        for model in ("am-1", "am-2"):
            with self.subTest(model=model):
                self.assertEqual(
                    [],
                    validate_instance(
                        load_specification(model),
                        "research-specification.schema.json",
                        SCHEMAS,
                    ),
                )


class Am1RunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result, cls.telemetry, cls.store = run("am-1")

    def test_the_run_reaches_all_three_decisions(self):
        self.assertEqual(
            {"QUALIFIED", "CONDITIONAL", "REJECTED"},
            {outcome.final_decision for outcome in self.result.outcomes},
        )

    def test_malformed_material_is_reported_without_stopping_the_run(self):
        self.assertEqual(1, len(self.result.failures))
        self.assertEqual(3, len(self.result.outcomes))
        self.assertEqual(
            1, len([event for event in self.telemetry.by_role("parsing") if event["status"] == "error"])
        )

    def test_a_rejected_material_keeps_its_evaluation_and_preserved_record(self):
        rejected = self.result.by_decision("REJECTED")[0]
        self.assertTrue(rejected.stopped_at_triage)
        self.assertEqual(
            [],
            validate_instance(
                rejected.triage_evaluation, "evaluation-result.schema.json", SCHEMAS
            ),
        )
        self.assertEqual(
            [], validate_instance(rejected.record, "preserved-record.schema.json", SCHEMAS)
        )
        self.assertEqual(
            rejected.source.content_hash, rejected.record["identity"]["content_hash"]
        )

    def test_preservation_does_not_depend_on_the_decision(self):
        shapes = {
            tuple(sorted(outcome.record)) for outcome in self.result.outcomes
        }
        self.assertEqual(1, len(shapes), shapes)

    def test_qualified_knowledge_is_evidence_backed(self):
        qualified = self.result.by_decision("QUALIFIED")[0]
        self.assertEqual(
            [],
            validate_instance(
                qualified.extraction, "extraction-result.schema.json", SCHEMAS
            ),
        )
        self.assertTrue(qualified.extraction["claims"])
        for fragment in qualified.record["acquired_artifact"]["evidence_fragments"]:
            self.assertIn(fragment["fragment"], qualified.source.text)

    def test_every_evaluated_material_carries_a_source_group_id(self):
        for outcome in self.result.outcomes:
            self.assertTrue(outcome.source.source_group_id)
            self.assertEqual(
                outcome.source.source_group_id,
                outcome.triage_evaluation["subject"]["source_group_id"],
            )
        self.assertEqual(3, len(set(self.result.source_group_ids)))

    def test_every_emitted_telemetry_event_satisfies_the_contract(self):
        self.assertTrue(self.telemetry.events)
        for event in self.telemetry.events:
            with self.subTest(role=event["operation_role"], status=event["status"]):
                self.assertEqual(
                    [], validate_instance(event, "telemetry-event.schema.json", SCHEMAS)
                )

    def test_the_run_is_reproducible(self):
        again, _, _ = run("am-1")
        self.assertEqual(
            [outcome.record for outcome in self.result.outcomes],
            [outcome.record for outcome in again.outcomes],
        )

    def test_stored_evaluations_can_be_redecided_by_a_stricter_policy(self):
        qualified = self.result.by_decision("QUALIFIED")[0]
        stricter = dict(load_specification("am-1")["evaluation"]["decision_policy"])
        stricter["rules"] = [
            {
                "decision": "QUALIFIED",
                "all": [{"dimension": "evidence_strength", "operator": "gte", "value": 0.99}],
            }
        ]
        stricter["fallback"] = "CONDITIONAL"
        self.assertEqual("QUALIFIED", qualified.decision["decision"])
        self.assertEqual("CONDITIONAL", apply_decision_policy(qualified.evaluation, stricter))


class Am2RunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result, cls.telemetry, cls.store = run("am-2")

    def test_the_run_reaches_all_three_decisions(self):
        self.assertEqual(
            {"QUALIFIED", "CONDITIONAL", "REJECTED"},
            {outcome.final_decision for outcome in self.result.outcomes},
        )

    def test_an_exact_content_duplicate_joins_the_same_source_group(self):
        by_url = {
            outcome.source.canonical_url: outcome for outcome in self.result.outcomes
        }
        original = by_url["https://registry.example.org/entities/example-organization"]
        mirror = by_url["https://mirror.example.net/entities/example-organization"]
        other = by_url["https://blog.unknown.example/rumours/example-organization"]
        self.assertEqual(original.source.content_hash, mirror.source.content_hash)
        self.assertEqual(original.source.source_group_id, mirror.source.source_group_id)
        self.assertNotEqual(original.source.source_group_id, other.source.source_group_id)

    def test_independence_means_only_that_no_exact_duplicate_was_detected(self):
        by_url = {
            outcome.source.canonical_url: outcome for outcome in self.result.outcomes
        }
        original = by_url["https://registry.example.org/entities/example-organization"]
        mirror = by_url["https://mirror.example.net/entities/example-organization"]
        self.assertEqual(
            1.0, original.evaluation["characteristics"]["independence"]["score"]
        )
        self.assertEqual(
            0.0, mirror.triage_evaluation["characteristics"]["independence"]["score"]
        )
        self.assertEqual("CONDITIONAL", mirror.final_decision)

    def test_the_three_characteristics_stay_separated(self):
        qualified = self.result.by_decision("QUALIFIED")[0]
        characteristics = qualified.evaluation["characteristics"]
        self.assertNotIn("confidence", characteristics)
        self.assertIn("source_authority", characteristics)
        self.assertIn("evidence_strength", characteristics)
        element = qualified.extraction["entities"][0]
        self.assertIn("extraction_confidence", element)
        self.assertIn("evidence_strength", element["evidence"])
        self.assertNotEqual(
            characteristics["source_authority"]["score"],
            characteristics["evidence_strength"]["score"],
        )

    def test_the_full_knowledge_product_is_preserved_for_every_decision(self):
        for outcome in self.result.outcomes:
            with self.subTest(decision=outcome.final_decision):
                self.assertEqual(
                    [],
                    validate_instance(
                        outcome.record, "preserved-record.schema.json", SCHEMAS
                    ),
                )
                self.assertIn("knowledge_product", outcome.record["derived_knowledge"])

    def test_every_emitted_telemetry_event_satisfies_the_contract(self):
        for event in self.telemetry.events:
            with self.subTest(role=event["operation_role"], status=event["status"]):
                self.assertEqual(
                    [], validate_instance(event, "telemetry-event.schema.json", SCHEMAS)
                )

    def test_a_dimension_without_a_measurement_function_is_a_configuration_error(self):
        pipeline = build_pipeline("am-2")
        pipeline.evaluator = ConfiguredEvaluator(
            measures={"source_authority": metadata_score({}, default=0.6)},
            triage_dimensions=("source_authority",),
        )
        with self.assertRaises(SpecificationError):
            pipeline.run()

    def test_a_policy_condition_that_was_never_measured_is_reported(self):
        class PartialEvaluator:
            """Measures only ``source_authority``, at both stages."""

            def measure(self, stage, source, extraction, dimensions):
                return {"source_authority": Measurement(0.6, "declared authority")}

        telemetry = CollectingTelemetrySink()
        pipeline = build_pipeline("am-2", telemetry=telemetry)
        pipeline.evaluator = PartialEvaluator()
        pipeline.run()
        qualification = [
            event
            for event in telemetry.by_role("qualification")
            if event["status"] == "partial"
        ]
        self.assertTrue(qualification)
        self.assertEqual(
            {"configuration_incomplete"}, {event["error_code"] for event in qualification}
        )


class DecisionReplayTests(unittest.TestCase):
    def test_replaying_a_policy_needs_no_reevaluation(self):
        result, _, _ = run("am-1")
        policy = load_specification("am-1")["evaluation"]["decision_policy"]
        for outcome in result.outcomes:
            evaluation = outcome.evaluation or outcome.triage_evaluation
            decision, matched_rule = match_decision_rule(evaluation, policy)
            stored = outcome.decision or outcome.triage_decision
            self.assertEqual(stored["decision"], decision)
            self.assertEqual(stored["matched_rule"], matched_rule)


class ExampleScriptTests(unittest.TestCase):
    def test_the_local_example_run_reports_all_three_decisions(self):
        completed = subprocess.run(
            [sys.executable, str(EXAMPLE)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(ROOT),
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        for expected in ("am-1", "am-2", "QUALIFIED", "CONDITIONAL", "REJECTED"):
            self.assertIn(expected, completed.stdout)


if __name__ == "__main__":
    unittest.main()
