"""Phase 1 grouping: exact canonical URL or exact content hash, nothing else."""

from tests import paths as paths  # noqa: F401

import unittest

from aether_orbis.grouping import SourceGrouper

from tests.support import source

ORIGINAL = "Example Organization partnered with Example Registry in September 2026."
SEMANTICALLY_SIMILAR = (
    "In September 2026 Example Registry entered into a partnership with Example Organization."
)


class GroupingTests(unittest.TestCase):
    def test_the_same_canonical_url_yields_the_same_group(self):
        grouper = SourceGrouper()
        first = source(text=ORIGINAL, url="https://example.com/news/a", grouper=grouper)
        second = source(
            text=ORIGINAL + " Updated.",
            url="https://EXAMPLE.com/news/a/",
            grouper=grouper,
        )
        self.assertEqual(first.canonical_url, second.canonical_url)
        self.assertEqual(first.source_group_id, second.source_group_id)

    def test_the_same_content_hash_yields_the_same_group(self):
        grouper = SourceGrouper()
        first = source(text=ORIGINAL, url="https://a.example/news", grouper=grouper)
        second = source(text=ORIGINAL, url="https://b.example/mirror", grouper=grouper)
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.source_group_id, second.source_group_id)

    def test_semantically_similar_material_is_not_deduplicated(self):
        grouper = SourceGrouper()
        first = source(text=ORIGINAL, url="https://a.example/news", grouper=grouper)
        second = source(
            text=SEMANTICALLY_SIMILAR, url="https://b.example/news", grouper=grouper
        )
        self.assertNotEqual(first.content_hash, second.content_hash)
        self.assertNotEqual(first.source_group_id, second.source_group_id)
        self.assertEqual(2, len(grouper.groups))

    def test_grouping_is_stable_when_the_same_material_is_seen_again(self):
        grouper = SourceGrouper()
        first = source(text=ORIGINAL, url="https://a.example/news", grouper=grouper)
        again = source(text=ORIGINAL, url="https://a.example/news", grouper=grouper)
        self.assertEqual(first.source_group_id, again.source_group_id)
        self.assertEqual(1, len(grouper.groups))


if __name__ == "__main__":
    unittest.main()
