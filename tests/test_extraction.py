"""Extraction keeps only evidence that occurs verbatim in the source."""

import unittest

from aether_orbis.adapters import DictionaryExtractor, EntityDefinition
from aether_orbis.adapters.extractors import FailingExtractor
from aether_orbis.extraction import (
    EVIDENCE_MISMATCH,
    UNKNOWN_ENTITY,
    build_extraction_result,
    verify_fragment,
)
from aether_orbis.model import (
    ClaimCandidate,
    EntityCandidate,
    EvidenceCandidate,
    ExtractionCandidates,
    RelationCandidate,
)
from tools.contract_validation import validate_instance

from tests.support import SCHEMAS, source

TEXT = (
    "Example Organization partnered with Example Registry.\n\n"
    "Example Registry confirmed the agreement on 9 September 2026."
)
EXTRACTED_AT = "2026-09-10T12:00:00Z"

ENTITIES = (
    EntityDefinition(id="org.example", type="organization", name="Example Organization"),
    EntityDefinition(id="org.registry", type="organization", name="Example Registry"),
)


def result(candidates, text=TEXT):
    return build_extraction_result(
        source(text=text),
        candidates,
        model="rule-based/dictionary",
        extractor_version="dictionary-extractor/1.0",
        extracted_at=EXTRACTED_AT,
    )


def evidence(fragment, strength=0.7):
    return EvidenceCandidate(fragment=fragment, evidence_strength=strength)


def entity(entity_id="org.example", fragment=None):
    return EntityCandidate(
        id=entity_id,
        type="organization",
        name="Example Organization",
        extraction_confidence=0.9,
        evidence=evidence(fragment or TEXT.split("\n\n")[0]),
    )


class EvidenceVerificationTests(unittest.TestCase):
    def test_a_verbatim_fragment_is_accepted(self):
        self.assertTrue(verify_fragment(source(text=TEXT), "partnered with Example Registry"))

    def test_a_paraphrased_fragment_is_rejected(self):
        self.assertFalse(
            verify_fragment(source(text=TEXT), "Example Registry became a partner")
        )

    def test_an_element_with_an_unverifiable_fragment_is_dropped(self):
        outcome = result(ExtractionCandidates(entities=(entity(fragment="invented quote"),)))
        self.assertEqual([], outcome.document["entities"])
        self.assertEqual("partial", outcome.status)
        self.assertEqual(EVIDENCE_MISMATCH, outcome.dropped[0].reason)

    def test_a_verified_element_keeps_its_fragment_and_source_identity(self):
        subject = source(text=TEXT)
        outcome = build_extraction_result(
            subject,
            ExtractionCandidates(entities=(entity(),)),
            model="rule-based/dictionary",
            extractor_version="dictionary-extractor/1.0",
            extracted_at=EXTRACTED_AT,
        )
        stored = outcome.document["entities"][0]["evidence"]
        self.assertIn(stored["fragment"], subject.text)
        self.assertEqual(subject.source_id, stored["source_id"])
        self.assertEqual(subject.retrieved_at, stored["retrieved_at"])


class SeparateCharacteristicsTests(unittest.TestCase):
    def test_extraction_confidence_and_evidence_strength_are_stored_separately(self):
        outcome = result(
            ExtractionCandidates(
                entities=(
                    EntityCandidate(
                        id="org.example",
                        type="organization",
                        name="Example Organization",
                        extraction_confidence=0.95,
                        evidence=evidence(TEXT.split("\n\n")[0], strength=0.4),
                    ),
                )
            )
        )
        stored = outcome.document["entities"][0]
        self.assertEqual(0.95, stored["extraction_confidence"])
        self.assertEqual(0.4, stored["evidence"]["evidence_strength"])

    def test_no_generic_confidence_is_ever_written(self):
        outcome = result(ExtractionCandidates(entities=(entity(),)))
        self.assertNotIn("confidence", outcome.document["entities"][0])
        self.assertEqual(
            [], validate_instance(outcome.document, "extraction-result.schema.json", SCHEMAS)
        )


class StatusTests(unittest.TestCase):
    def test_a_source_without_extractable_elements_is_ok_and_empty(self):
        outcome = result(ExtractionCandidates())
        self.assertEqual("ok", outcome.status)
        self.assertEqual([], outcome.document["claims"])
        self.assertEqual(
            [], validate_instance(outcome.document, "extraction-result.schema.json", SCHEMAS)
        )

    def test_a_failed_extractor_yields_an_error_result_without_invented_elements(self):
        outcome = result(ExtractionCandidates(failed=True, error_code="extraction_failed"))
        self.assertEqual("error", outcome.status)
        self.assertEqual(([], [], []), (
            outcome.document["entities"],
            outcome.document["relations"],
            outcome.document["claims"],
        ))
        self.assertEqual("extraction_failed", outcome.error_code)

    def test_a_relation_pointing_at_an_unknown_entity_is_dropped(self):
        outcome = result(
            ExtractionCandidates(
                entities=(entity(),),
                relations=(
                    RelationCandidate(
                        subject="org.example",
                        predicate="partnered_with",
                        object="org.unknown",
                        state="OBSERVED",
                        extraction_confidence=0.8,
                        evidence=evidence(TEXT.split("\n\n")[0]),
                    ),
                ),
            )
        )
        self.assertEqual([], outcome.document["relations"])
        self.assertEqual(UNKNOWN_ENTITY, outcome.dropped[0].reason)
        self.assertEqual("partial", outcome.status)

    def test_a_claim_without_known_entities_is_dropped(self):
        outcome = result(
            ExtractionCandidates(
                claims=(
                    ClaimCandidate(
                        claim="Unattached claim.",
                        entity_ids=(),
                        extraction_confidence=0.8,
                        evidence=evidence(TEXT.split("\n\n")[0]),
                    ),
                )
            )
        )
        self.assertEqual([], outcome.document["claims"])
        self.assertEqual("partial", outcome.status)


class DictionaryExtractorTests(unittest.TestCase):
    def test_the_offline_extractor_quotes_the_sentence_it_used(self):
        subject = source(text=TEXT)
        extractor = DictionaryExtractor(
            entities=ENTITIES,
            predicates={"partnered_with": ("partnered with",)},
            claim_markers=("confirmed",),
        )
        outcome = build_extraction_result(
            subject,
            extractor.extract(subject),
            model=extractor.model,
            extractor_version=extractor.extractor_version,
            extracted_at=EXTRACTED_AT,
        )
        self.assertEqual("ok", outcome.status)
        self.assertEqual(
            {"org.example", "org.registry"},
            {item["id"] for item in outcome.document["entities"]},
        )
        self.assertEqual("partnered_with", outcome.document["relations"][0]["predicate"])
        self.assertEqual(1, len(outcome.document["claims"]))
        for element in (
            *outcome.document["entities"],
            *outcome.document["relations"],
            *outcome.document["claims"],
        ):
            self.assertIn(element["evidence"]["fragment"], subject.text)

    def test_a_failing_extractor_is_reported_rather_than_hidden(self):
        subject = source(text=TEXT)
        extractor = FailingExtractor()
        outcome = build_extraction_result(
            subject,
            extractor.extract(subject),
            model=extractor.model,
            extractor_version=extractor.extractor_version,
            extracted_at=EXTRACTED_AT,
        )
        self.assertEqual("error", outcome.status)


if __name__ == "__main__":
    unittest.main()
