"""Preservation follows the policy only — not the source type, not the decision."""

from tests import paths as paths  # noqa: F401

import itertools
import unittest

from aether_orbis.errors import UnsupportedPreservationError
from aether_orbis.extraction import build_extraction_result
from aether_orbis.model import (
    ClaimCandidate,
    EntityCandidate,
    EvidenceCandidate,
    ExtractionCandidates,
    RelationCandidate,
)
from aether_orbis.preservation import (
    ARTIFACT_LEVELS,
    KNOWLEDGE_LEVELS,
    PHASE_1_HISTORY_LEVELS,
    RISK_LEVELS,
    build_preserved_record,
)
from tools.contract_validation import validate_instance

from tests.support import SCHEMAS, source

TEXT = (
    "Example Organization partnered with Example Registry.\n\n"
    "Example Registry confirmed the agreement on 9 September 2026."
)
FIRST_SENTENCE = TEXT.split("\n\n")[0]
EXTRACTOR_VERSION = "dictionary-extractor/1.0"


def policy(artifact, knowledge, history):
    document = {
        "schema_version": "1.0",
        "acquired_artifact": artifact,
        "derived_knowledge": knowledge,
        "observation_history": history,
    }
    if artifact in RISK_LEVELS:
        document["reproducibility_risk_accepted"] = True
    if artifact == "full_content":
        document["profile"] = "archival"
    return document


def extraction(subject):
    evidence = EvidenceCandidate(fragment=FIRST_SENTENCE, evidence_strength=0.7)
    candidates = ExtractionCandidates(
        entities=(
            EntityCandidate(
                id="org.example",
                type="organization",
                name="Example Organization",
                extraction_confidence=0.9,
                evidence=evidence,
            ),
        ),
        relations=(
            RelationCandidate(
                subject="org.example",
                predicate="partnered_with",
                object="org.example",
                state="OBSERVED",
                extraction_confidence=0.8,
                evidence=evidence,
            ),
        ),
        claims=(
            ClaimCandidate(
                claim="Example Organization partnered with Example Registry.",
                entity_ids=("org.example",),
                extraction_confidence=0.8,
                evidence=evidence,
            ),
        ),
    )
    return build_extraction_result(
        subject,
        candidates,
        model="rule-based/dictionary",
        extractor_version=EXTRACTOR_VERSION,
        extracted_at="2026-09-10T12:00:00Z",
    ).document


class Phase1CombinationTests(unittest.TestCase):
    def test_every_permitted_phase_1_combination_produces_a_valid_record(self):
        subject = source(text=TEXT)
        document = extraction(subject)
        combinations = list(
            itertools.product(ARTIFACT_LEVELS, KNOWLEDGE_LEVELS, PHASE_1_HISTORY_LEVELS)
        )
        self.assertEqual(40, len(combinations))
        for artifact, knowledge, history in combinations:
            with self.subTest(artifact=artifact, knowledge=knowledge, history=history):
                record = build_preserved_record(
                    policy(artifact, knowledge, history),
                    subject,
                    extractor_version=EXTRACTOR_VERSION,
                    extraction=document,
                )
                self.assertEqual(
                    [], validate_instance(record, "preserved-record.schema.json", SCHEMAS)
                )
                self.assertEqual(subject.content_hash, record["identity"]["content_hash"])

    def test_identity_survives_the_minimal_combination(self):
        subject = source(text=TEXT)
        record = build_preserved_record(
            policy("none", "none", "none"), subject, extractor_version=EXTRACTOR_VERSION
        )
        self.assertNotIn("acquired_artifact", record)
        self.assertNotIn("derived_knowledge", record)
        self.assertEqual(
            {
                "source_id": subject.source_id,
                "canonical_url": subject.canonical_url,
                "content_hash": subject.content_hash,
                "retrieved_at": subject.retrieved_at,
                "published_at": subject.published_at,
                "parser_version": subject.parser_version,
                "extractor_version": EXTRACTOR_VERSION,
            },
            record["identity"],
        )

    def test_evidence_fragments_are_preserved_verbatim(self):
        subject = source(text=TEXT)
        record = build_preserved_record(
            policy("evidence_fragments", "claims", "latest_only"),
            subject,
            extractor_version=EXTRACTOR_VERSION,
            extraction=extraction(subject),
        )
        fragments = record["acquired_artifact"]["evidence_fragments"]
        self.assertEqual(1, len(fragments), "identical fragments are stored once")
        self.assertIn(fragments[0]["fragment"], subject.text)


class PolicyRuleTests(unittest.TestCase):
    def test_dropping_below_evidence_fragments_requires_accepted_risk(self):
        for artifact in RISK_LEVELS:
            with self.subTest(artifact=artifact):
                unaccepted = policy(artifact, "claims", "latest_only")
                unaccepted.pop("reproducibility_risk_accepted")
                with self.assertRaises(UnsupportedPreservationError):
                    build_preserved_record(
                        unaccepted, source(text=TEXT), extractor_version=EXTRACTOR_VERSION
                    )

    def test_accepted_risk_is_recorded_in_the_preserved_record(self):
        record = build_preserved_record(
            policy("metadata", "claims", "latest_only"),
            source(text=TEXT),
            extractor_version=EXTRACTOR_VERSION,
        )
        self.assertIs(True, record["policy"]["reproducibility_risk_accepted"])

    def test_full_content_requires_the_archival_profile(self):
        without_profile = policy("full_content", "none", "latest_only")
        without_profile.pop("profile")
        with self.assertRaises(UnsupportedPreservationError):
            build_preserved_record(
                without_profile, source(text=TEXT), extractor_version=EXTRACTOR_VERSION
            )

    def test_full_history_is_not_executable_in_phase_1(self):
        with self.assertRaises(UnsupportedPreservationError):
            build_preserved_record(
                policy("evidence_fragments", "claims", "full_history"),
                source(text=TEXT),
                extractor_version=EXTRACTOR_VERSION,
            )

    def test_preservation_ignores_the_source_type(self):
        chosen = policy("summary", "claims", "latest_only")
        html = build_preserved_record(
            chosen,
            source(text=TEXT, media_type="text/html"),
            extractor_version=EXTRACTOR_VERSION,
        )
        plain = build_preserved_record(
            chosen,
            source(text=TEXT, media_type="text/plain"),
            extractor_version=EXTRACTOR_VERSION,
        )
        self.assertEqual(
            html["acquired_artifact"]["summary"], plain["acquired_artifact"]["summary"]
        )

    def test_a_source_without_extraction_still_preserves_its_declared_shape(self):
        record = build_preserved_record(
            policy("evidence_fragments", "claims_and_relations", "latest_only"),
            source(text=TEXT),
            extractor_version=EXTRACTOR_VERSION,
        )
        self.assertEqual([], record["acquired_artifact"]["evidence_fragments"])
        self.assertEqual({"claims": [], "relations": []}, record["derived_knowledge"])
        self.assertEqual(
            [], validate_instance(record, "preserved-record.schema.json", SCHEMAS)
        )

    def test_an_empty_source_still_produces_a_non_empty_summary(self):
        record = build_preserved_record(
            policy("summary", "none", "latest_only"),
            source(text=""),
            extractor_version=EXTRACTOR_VERSION,
        )
        self.assertTrue(record["acquired_artifact"]["summary"])
        self.assertEqual(
            [], validate_instance(record, "preserved-record.schema.json", SCHEMAS)
        )


if __name__ == "__main__":
    unittest.main()
