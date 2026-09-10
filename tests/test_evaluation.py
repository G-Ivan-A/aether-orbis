"""Evaluation measures; the Decision Policy decides. The two stay separable."""

from tests import paths as paths  # noqa: F401

import unittest

from aether_orbis.errors import SpecificationError
from aether_orbis.evaluation import (
    apply_decision_policy,
    build_evaluation_result,
    build_qualification_decision,
    match_decision_rule,
)
from aether_orbis.model import Measurement
from tools.contract_validation import validate_instance

from tests.support import SCHEMAS, source

EVALUATED_AT = "2026-09-10T12:00:00Z"
DECIDED_AT = "2026-09-10T12:00:01Z"

STRICT = {
    "schema_version": "1.0",
    "policy_id": "strict-selection",
    "policy_version": "1.0",
    "rules": [
        {
            "decision": "QUALIFIED",
            "all": [
                {"dimension": "topic_match", "operator": "gte", "value": 0.9},
                {"dimension": "evidence_strength", "operator": "gte", "value": 0.9},
            ],
        },
        {
            "decision": "CONDITIONAL",
            "all": [{"dimension": "topic_match", "operator": "gte", "value": 0.5}],
        },
    ],
    "fallback": "REJECTED",
}

PERMISSIVE = {
    "schema_version": "1.0",
    "policy_id": "permissive-selection",
    "policy_version": "1.0",
    "rules": [
        {
            "decision": "QUALIFIED",
            "all": [{"dimension": "topic_match", "operator": "gte", "value": 0.6}],
        }
    ],
    "fallback": "CONDITIONAL",
}

SPECIFICATION = {
    "specification_id": "evaluation-tests",
    "evaluation": {
        "dimensions": ["topic_match", "evidence_strength"],
        "decision_policy": STRICT,
    },
}


def evaluation(measurements, stage="full"):
    return build_evaluation_result(
        source(),
        SPECIFICATION,
        measurements,
        stage=stage,
        evaluated_at=EVALUATED_AT,
    )


def measured(topic_match=0.8, evidence_strength=0.7):
    return {
        "topic_match": Measurement(topic_match, "keyword coverage"),
        "evidence_strength": Measurement(evidence_strength, "verified fragments"),
    }


class EvaluationResultTests(unittest.TestCase):
    def test_a_stored_result_satisfies_the_contract(self):
        document = evaluation(measured())
        self.assertEqual(
            [], validate_instance(document, "evaluation-result.schema.json", SCHEMAS)
        )
        self.assertIn("source_group_id", document["subject"])
        self.assertEqual("full", document["evaluation_stage"])

    def test_an_undeclared_characteristic_is_a_configuration_error(self):
        with self.assertRaises(SpecificationError):
            evaluation({"vibes": Measurement(1.0, "unspecified")})

    def test_the_generic_characteristic_confidence_is_forbidden(self):
        specification = {
            "specification_id": "evaluation-tests",
            "evaluation": {"dimensions": ["confidence"], "decision_policy": STRICT},
        }
        with self.assertRaises(SpecificationError):
            build_evaluation_result(
                source(),
                specification,
                {"confidence": Measurement(0.9, "generic")},
                stage="full",
                evaluated_at=EVALUATED_AT,
            )

    def test_an_evaluation_without_characteristics_is_refused(self):
        with self.assertRaises(SpecificationError):
            evaluation({})

    def test_triage_may_measure_a_subset_of_the_declared_dimensions(self):
        document = evaluation({"topic_match": Measurement(0.4, "cheap check")}, stage="triage")
        self.assertEqual(["topic_match"], list(document["characteristics"]))
        self.assertEqual(
            [], validate_instance(document, "evaluation-result.schema.json", SCHEMAS)
        )


class DecisionPolicyReplayTests(unittest.TestCase):
    def test_a_stored_evaluation_can_be_redecided_by_another_policy(self):
        document = evaluation(measured(topic_match=0.8, evidence_strength=0.7))
        self.assertEqual("CONDITIONAL", apply_decision_policy(document, STRICT))
        self.assertEqual("QUALIFIED", apply_decision_policy(document, PERMISSIVE))
        self.assertEqual(
            [], validate_instance(document, "evaluation-result.schema.json", SCHEMAS)
        )

    def test_replaying_a_policy_does_not_change_the_stored_evaluation(self):
        document = evaluation(measured())
        before = dict(document)
        apply_decision_policy(document, PERMISSIVE)
        self.assertEqual(before, document)

    def test_the_matched_rule_index_is_reported_and_the_fallback_is_explicit(self):
        low = evaluation(measured(topic_match=0.1, evidence_strength=0.1))
        self.assertEqual(("REJECTED", None), match_decision_rule(low, STRICT))
        high = evaluation(measured(topic_match=0.95, evidence_strength=0.95))
        self.assertEqual(("QUALIFIED", 0), match_decision_rule(high, STRICT))

    def test_a_rule_naming_an_unmeasured_characteristic_never_matches(self):
        triage = evaluation({"topic_match": Measurement(0.95, "cheap check")}, stage="triage")
        decision, matched_rule = match_decision_rule(triage, STRICT)
        self.assertEqual("CONDITIONAL", decision)
        self.assertEqual(1, matched_rule)


class QualificationDecisionTests(unittest.TestCase):
    def test_a_decision_explains_itself_and_satisfies_the_contract(self):
        document = evaluation(measured(topic_match=0.95, evidence_strength=0.95))
        decision = build_qualification_decision(document, STRICT, decided_at=DECIDED_AT)
        self.assertEqual("QUALIFIED", decision["decision"])
        self.assertEqual(0, decision["matched_rule"])
        self.assertIn("topic_match", decision["rationale"])
        self.assertEqual(document["evaluation_id"], decision["evaluation_id"])
        self.assertEqual(
            [], validate_instance(decision, "qualification-decision.schema.json", SCHEMAS)
        )

    def test_a_fallback_decision_records_that_no_rule_matched(self):
        document = evaluation(measured(topic_match=0.1, evidence_strength=0.1))
        decision = build_qualification_decision(document, STRICT, decided_at=DECIDED_AT)
        self.assertEqual("REJECTED", decision["decision"])
        self.assertIsNone(decision["matched_rule"])
        self.assertIn("fallback", decision["rationale"])
        self.assertEqual(
            [], validate_instance(decision, "qualification-decision.schema.json", SCHEMAS)
        )

    def test_two_policies_over_one_evaluation_yield_two_distinct_decisions(self):
        document = evaluation(measured())
        strict = build_qualification_decision(document, STRICT, decided_at=DECIDED_AT)
        permissive = build_qualification_decision(document, PERMISSIVE, decided_at=DECIDED_AT)
        self.assertNotEqual(strict["decision_id"], permissive["decision_id"])
        self.assertEqual(strict["evaluation_id"], permissive["evaluation_id"])


if __name__ == "__main__":
    unittest.main()
