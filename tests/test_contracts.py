from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from tools.contract_validation import (
    apply_decision_policy,
    load_document,
    validate_document,
    validate_repository,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "configs" / "schemas"
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"


class ContractFixtureTests(unittest.TestCase):
    def test_tracked_profiles_examples_and_runtime_config_are_valid(self):
        self.assertEqual([], validate_repository(ROOT))

    def test_valid_fixtures_satisfy_their_contracts(self):
        for path in sorted((FIXTURES / "valid").glob("*.yaml")):
            with self.subTest(path=path.name):
                schema_name, separator, _ = path.name.partition("--")
                self.assertEqual("--", separator)
                self.assertEqual([], validate_document(path, schema_name, SCHEMAS))

    def test_invalid_fixtures_are_rejected(self):
        expected_cases = {
            "evaluation-result.schema.json--confidence.yaml",
            "evaluation-result.schema.json--missing-source-group.yaml",
            "extraction-result.schema.json--confidence.yaml",
            "preservation-policy.schema.json--archival-not-explicit.yaml",
            "preservation-policy.schema.json--risk-not-accepted.yaml",
            "preserved-record.schema.json--missing-identity.yaml",
            "preserved-record.schema.json--payloads-despite-none.yaml",
            "research-profile.schema.json--am3-executable.yaml",
            "research-profile.schema.json--full-history.yaml",
            "research-profile.schema.json--mixed-runtime.yaml",
            "research-profile.schema.json--relabelled-am3.yaml",
            "research-run-outcome.schema.json--missing-explanation.yaml",
            "research-specification.schema.json--missing-termination.yaml",
            "research-specification.schema.json--undeclared-dimension.yaml",
            "research-specification.schema.json--unknown-strategy.yaml",
            "runtime-configuration.schema.json--mixed-research.yaml",
            "telemetry-event.schema.json--confidence.yaml",
            "telemetry-event.schema.json--triage-without-evaluation.yaml",
        }
        paths = sorted((FIXTURES / "invalid").glob("*.yaml"))
        self.assertEqual(expected_cases, {path.name for path in paths})
        for path in paths:
            with self.subTest(path=path.name):
                schema_name, separator, _ = path.name.partition("--")
                self.assertEqual("--", separator)
                self.assertNotEqual([], validate_document(path, schema_name, SCHEMAS))

    def test_general_specifications_express_all_models_and_strategies(self):
        paths = sorted(
            (FIXTURES / "valid").glob("research-specification.schema.json--am*.yaml")
        )
        documents = [load_document(path) for path in paths]
        self.assertEqual(
            {"AM-1", "AM-2", "AM-3", "AM-4", "AM-5"},
            {document["acquisition_model"] for document in documents},
        )
        self.assertEqual(
            {"enumerate", "expand", "query"},
            {document["scope"]["strategy"] for document in documents},
        )
        for document in documents:
            self.assertEqual(
                {"objective", "target", "scope", "evaluation", "preservation", "termination"},
                {
                    key
                    for key in document
                    if key
                    in {"objective", "target", "scope", "evaluation", "preservation", "termination"}
                },
            )

    def test_run_outcome_fixtures_cover_all_five_statuses(self):
        paths = sorted(
            (FIXTURES / "valid").glob("research-run-outcome.schema.json--*.yaml")
        )
        self.assertEqual(
            {"SUFFICIENT", "PARTIAL", "ZERO", "CONFLICT", "EXHAUSTED"},
            {load_document(path)["status"] for path in paths},
        )

    def test_saved_evaluation_can_be_redecided_without_reevaluation(self):
        evaluation = FIXTURES / "valid" / "evaluation-result.schema.json--custom.yaml"
        strict = FIXTURES / "valid" / "decision-policy.schema.json--strict.yaml"
        permissive = FIXTURES / "valid" / "decision-policy.schema.json--permissive.yaml"
        self.assertEqual("CONDITIONAL", apply_decision_policy(evaluation, strict))
        self.assertEqual("QUALIFIED", apply_decision_policy(evaluation, permissive))

    def test_content_identity_requires_a_full_sha256_digest(self):
        cases = (
            (
                "evaluation-result.schema.json--custom.yaml",
                "evaluation-result.schema.json",
                ("subject", "content_hash"),
            ),
            (
                "extraction-result.schema.json--contradicted.yaml",
                "extraction-result.schema.json",
                ("source", "content_hash"),
            ),
            (
                "preserved-record.schema.json--identity-with-none.yaml",
                "preserved-record.schema.json",
                ("identity", "content_hash"),
            ),
            (
                "research-run.schema.json--complete.yaml",
                "research-run.schema.json",
                ("processed_sources", 0, "content_hash"),
            ),
        )
        with TemporaryDirectory() as directory:
            for fixture_name, schema_name, hash_path in cases:
                with self.subTest(schema=schema_name):
                    document = load_document(FIXTURES / "valid" / fixture_name)
                    target = document
                    for part in hash_path[:-1]:
                        target = target[part]
                    target[hash_path[-1]] = f"sha256:{'a' * 32}"
                    path = Path(directory) / fixture_name
                    path.write_text(yaml.safe_dump(document), encoding="utf-8")
                    self.assertNotEqual(
                        [], validate_document(path, schema_name, SCHEMAS)
                    )


if __name__ == "__main__":
    unittest.main()
