"""The Sufficiency Gate: five statuses, none of them masking another."""

from tests import paths as paths  # noqa: F401

import copy
import unittest

from aether_orbis.errors import SpecificationError
from aether_orbis.model import Measurement
from aether_orbis.sufficiency import (
    BUDGET_EXHAUSTED,
    CONFLICT,
    EXHAUSTED,
    FRONTIER_EXHAUSTED,
    PARTIAL,
    SUFFICIENT,
    ZERO,
    build_run_outcome,
    completion_dimensions,
    detect_conflicts,
    success_conditions,
    unmet_conditions,
)
from tools.contract_validation import validate_instance

from tests.acquisition_fixtures import build_pipeline, load_specification
from tests.support import SCHEMAS

MET = {
    "neighborhood_completeness": Measurement(1.0, "every seed expanded"),
    "new_entity_saturation": Measurement(0.0, "no new entity"),
}
UNMET = {
    "neighborhood_completeness": Measurement(0.4, "two seeds still pending"),
    "new_entity_saturation": Measurement(0.5, "half the entities are new"),
}


def qualified(**overrides):
    """Return the qualified outcomes of the AM-2 fixture run."""

    result = build_pipeline("am-2", **overrides).run()
    return tuple(
        outcome
        for outcome in result.outcomes
        if outcome.final_decision in ("QUALIFIED", "CONDITIONAL")
    )


def outcome_for(coverage, *, qualified_outcomes, stop_reason=FRONTIER_EXHAUSTED, **kwargs):
    return build_run_outcome(
        load_specification("am-2"),
        coverage,
        qualified=qualified_outcomes,
        stop_reason=stop_reason,
        **kwargs,
    )


class StatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qualified = qualified()

    def test_meeting_every_success_condition_is_sufficient(self):
        outcome = outcome_for(MET, qualified_outcomes=self.qualified)
        self.assertEqual(SUFFICIENT, outcome["status"])
        self.assertEqual([], outcome["gaps"])

    def test_an_unfinished_frontier_with_gaps_is_partial(self):
        outcome = outcome_for(UNMET, qualified_outcomes=self.qualified)
        self.assertEqual(PARTIAL, outcome["status"])
        self.assertEqual(2, len(outcome["gaps"]))

    def test_the_same_gaps_under_an_exhausted_budget_are_exhausted(self):
        outcome = outcome_for(
            UNMET, qualified_outcomes=self.qualified, stop_reason=BUDGET_EXHAUSTED
        )
        self.assertEqual(EXHAUSTED, outcome["status"])

    def test_no_qualified_knowledge_is_zero_and_never_partial(self):
        outcome = outcome_for(UNMET, qualified_outcomes=())
        self.assertEqual(ZERO, outcome["status"])
        self.assertIn("no analytical answer", outcome["gaps"][0])

    def test_zero_carries_no_analytic_answer_of_any_kind(self):
        outcome = outcome_for(MET, qualified_outcomes=())
        self.assertEqual(ZERO, outcome["status"])
        self.assertEqual([], outcome["conflicts"])
        self.assertNotEqual([], outcome["gaps"])

    def test_a_contradiction_is_a_conflict_and_never_a_partial(self):
        from aether_orbis.adapters import CorpusFetcher
        from tests.support import ACQUISITION

        stream = qualified(
            fetcher=CorpusFetcher.from_directory(ACQUISITION / "am-2" / "conflict")
        )
        outcome = outcome_for(UNMET, qualified_outcomes=stream)
        self.assertEqual(CONFLICT, outcome["status"])
        self.assertEqual(2, len(outcome["conflicts"][0]["source_group_ids"]))

    def test_every_status_satisfies_the_outcome_contract(self):
        cases = {
            SUFFICIENT: outcome_for(MET, qualified_outcomes=self.qualified),
            PARTIAL: outcome_for(UNMET, qualified_outcomes=self.qualified),
            EXHAUSTED: outcome_for(
                UNMET, qualified_outcomes=self.qualified, stop_reason=BUDGET_EXHAUSTED
            ),
            ZERO: outcome_for(UNMET, qualified_outcomes=()),
        }
        for status, outcome in cases.items():
            with self.subTest(status=status):
                self.assertEqual(status, outcome["status"])
                self.assertEqual(
                    [],
                    validate_instance(
                        outcome, "research-run-outcome.schema.json", SCHEMAS
                    ),
                )


class ExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qualified = qualified()

    def test_a_gap_names_the_dimension_the_measurement_and_the_condition(self):
        outcome = outcome_for(UNMET, qualified_outcomes=self.qualified)
        self.assertIn("neighborhood_completeness is 0.4", outcome["gaps"][0])
        self.assertIn("gte 0.85", outcome["gaps"][0])

    def test_a_dimension_that_was_never_measured_is_reported_as_a_gap(self):
        gaps = unmet_conditions({}, success_conditions(load_specification("am-2")))
        self.assertEqual(2, len(gaps))
        self.assertIn("never measured", gaps[0])

    def test_the_remaining_frontier_becomes_the_recommended_expansion(self):
        from aether_orbis.model import FrontierItem

        outcome = outcome_for(
            UNMET,
            qualified_outcomes=self.qualified,
            remaining_frontier=(
                FrontierItem(strategy="expand", kind="seed", value="Example Registry"),
            ),
        )
        self.assertEqual(["expand: Example Registry"], outcome["recommended_expansion"])

    def test_an_empty_frontier_recommends_widening_the_scope(self):
        outcome = outcome_for(UNMET, qualified_outcomes=self.qualified)
        self.assertIn("widen the scope", outcome["recommended_expansion"][0])

    def test_a_sufficient_run_recommends_nothing(self):
        outcome = outcome_for(MET, qualified_outcomes=self.qualified)
        self.assertEqual([], outcome["recommended_expansion"])

    def test_the_rationale_names_the_measurements_it_was_based_on(self):
        outcome = outcome_for(MET, qualified_outcomes=self.qualified)
        self.assertIn("neighborhood_completeness=1.0", outcome["rationale"])


class SpecificationOwnershipTests(unittest.TestCase):
    """Coverage names come from the specification and from nowhere else (O-3)."""

    def test_the_declared_completion_dimensions_are_used_verbatim(self):
        self.assertEqual(
            ("neighborhood_completeness", "new_entity_saturation"),
            completion_dimensions(load_specification("am-2")),
        )

    def test_reporting_an_undeclared_coverage_dimension_is_an_error(self):
        with self.assertRaises(SpecificationError):
            outcome_for(
                {"invented_metric": Measurement(1.0, "not declared anywhere")},
                qualified_outcomes=qualified(),
            )

    def test_a_success_condition_on_an_undeclared_dimension_is_an_error(self):
        specification = copy.deepcopy(load_specification("am-2"))
        specification["termination"]["success_conditions"].append(
            {"dimension": "invented_metric", "operator": "gte", "value": 1.0}
        )
        with self.assertRaises(SpecificationError):
            success_conditions(specification)

    def test_a_missing_termination_block_is_an_error(self):
        specification = copy.deepcopy(load_specification("am-2"))
        del specification["termination"]
        with self.assertRaises(SpecificationError):
            completion_dimensions(specification)


class ConflictDetectionTests(unittest.TestCase):
    def test_agreement_between_independent_groups_is_not_a_conflict(self):
        self.assertEqual((), detect_conflicts(qualified()))

    def test_a_conflict_names_the_relation_and_both_groups(self):
        from aether_orbis.adapters import CorpusFetcher
        from tests.support import ACQUISITION

        conflicts = detect_conflicts(
            qualified(
                fetcher=CorpusFetcher.from_directory(ACQUISITION / "am-2" / "conflict")
            )
        )
        self.assertEqual(1, len(conflicts))
        self.assertEqual("partnered_with", conflicts[0]["dimension"])
        self.assertIn("CONTRADICTED", conflicts[0]["description"])
        self.assertEqual(
            sorted(conflicts[0]["source_group_ids"]), conflicts[0]["source_group_ids"]
        )

    def test_one_group_contradicting_itself_is_not_an_independent_conflict(self):
        stream = qualified()
        single = tuple(
            outcome
            for outcome in stream
            if outcome.source.source_group_id == stream[0].source.source_group_id
        )
        self.assertEqual((), detect_conflicts(single))


if __name__ == "__main__":
    unittest.main()
