"""Ingestion normalizes material and always produces a content identity."""

from tests import paths as paths  # noqa: F401

import unittest

from aether_orbis.adapters import HtmlTextParser, PlainTextParser
from aether_orbis.errors import MalformedSourceError
from aether_orbis.grouping import SourceGrouper
from aether_orbis.ingestion import canonicalize_url, ingest_frontier, ingest_material
from aether_orbis.model import FrontierItem

from tests.support import RETRIEVED_AT, raw, source

HTML = """
<html>
  <head>
    <title>Partnership announced</title>
    <meta name="article:published_time" content="2026-09-08T10:00:00Z">
  </head>
  <body>
    <nav>Home About Contacts</nav>
    <p>Example Organization partnered with Example Registry.</p>
    <script>tracker("noise")</script>
  </body>
</html>
"""


class CanonicalUrlTests(unittest.TestCase):
    def test_representation_only_differences_canonicalize_to_the_same_url(self):
        self.assertEqual(
            canonicalize_url("HTTPS://Example.COM:443/a/b/#section"),
            canonicalize_url("https://example.com/a/b"),
        )

    def test_query_parameters_are_preserved_verbatim(self):
        self.assertEqual(
            "https://example.com/a?b=2&a=1",
            canonicalize_url("https://example.com/a?b=2&a=1"),
        )

    def test_a_relative_url_is_malformed(self):
        with self.assertRaises(MalformedSourceError):
            canonicalize_url("/relative/path")


class IngestionTests(unittest.TestCase):
    def test_a_normal_source_carries_every_mandatory_identity_field(self):
        result = ingest_material(raw(), PlainTextParser(), SourceGrouper())
        self.assertTrue(result.source_id.startswith("src-"))
        self.assertTrue(result.content_hash.startswith("sha256:"))
        self.assertEqual("https://example.com/article", result.canonical_url)
        self.assertEqual(RETRIEVED_AT, result.retrieved_at)
        self.assertEqual("2026-09-09T18:30:00Z", result.published_at)
        self.assertEqual("plain-text-parser/1.0", result.parser_version)
        self.assertTrue(result.source_group_id)

    def test_an_empty_document_is_normal_and_still_identified(self):
        result = ingest_material(raw(text=""), PlainTextParser(), SourceGrouper())
        self.assertEqual("", result.text)
        self.assertTrue(result.content_hash.startswith("sha256:"))
        self.assertTrue(result.source_id.startswith("src-"))

    def test_an_undecodable_payload_is_malformed(self):
        with self.assertRaises(MalformedSourceError):
            ingest_material(
                raw(payload=b"\xff\xfe\x00binary"), PlainTextParser(), SourceGrouper()
            )

    def test_material_without_a_publication_timestamp_is_malformed(self):
        with self.assertRaises(MalformedSourceError):
            ingest_material(raw(published_at=None), PlainTextParser(), SourceGrouper())

    def test_an_invalid_retrieval_timestamp_is_malformed(self):
        with self.assertRaises(MalformedSourceError):
            ingest_material(raw(retrieved_at="yesterday"), PlainTextParser(), SourceGrouper())

    def test_html_is_normalized_into_text_without_boilerplate_or_scripts(self):
        result = ingest_material(
            raw(payload=HTML.encode("utf-8"), media_type="text/html", published_at=None),
            HtmlTextParser(),
            SourceGrouper(),
        )
        self.assertIn("Example Organization partnered with Example Registry.", result.text)
        self.assertNotIn("tracker", result.text)
        self.assertNotIn("Home About Contacts", result.text)
        self.assertEqual("2026-09-08T10:00:00Z", result.published_at)
        self.assertEqual("Partnership announced", result.metadata["title"])

    def test_identical_text_produces_an_identical_content_hash(self):
        first = source(text="Same body.", url="https://a.example/one")
        second = source(text="Same body.", url="https://b.example/two")
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertNotEqual(first.source_id, second.source_id)


class FrontierIngestionTests(unittest.TestCase):
    def test_one_malformed_material_does_not_stop_the_remaining_ones(self):
        class Fetcher:
            def fetch(self, item):
                return (raw(url="https://a.example/ok"), raw(payload=b"\xff"), raw(url="https://b.example/ok"))

        attempts = list(
            ingest_frontier(
                (FrontierItem(strategy="enumerate", kind="item", value="x"),),
                Fetcher(),
                PlainTextParser(),
                SourceGrouper(),
            )
        )
        self.assertEqual(3, len(attempts))
        self.assertEqual(
            [True, False, True], [attempt[2] is not None for attempt in attempts]
        )
        self.assertIsInstance(attempts[1][3], MalformedSourceError)


if __name__ == "__main__":
    unittest.main()
