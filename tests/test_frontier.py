"""The frontier comes from the specification and from nothing else."""

from tests import paths as paths  # noqa: F401

import unittest

from aether_orbis.errors import SpecificationError
from aether_orbis.frontier import build_frontier


def specification(strategy, frontier):
    return {"scope": {"strategy": strategy, "frontier": frontier}}


class FrontierTests(unittest.TestCase):
    def test_enumerate_yields_one_item_per_declared_item(self):
        items = build_frontier(
            specification("enumerate", {"items": ["https://a.example/feed", "https://b.example"]})
        )
        self.assertEqual(("item", "item"), tuple(item.kind for item in items))
        self.assertEqual(
            ("https://a.example/feed", "https://b.example"),
            tuple(item.value for item in items),
        )

    def test_expand_yields_seeds_carrying_the_declared_relation_hints(self):
        items = build_frontier(
            specification(
                "expand", {"seeds": ["Example Organization"], "relation_hints": ["partner"]}
            )
        )
        self.assertEqual(1, len(items))
        self.assertEqual("seed", items[0].kind)
        self.assertEqual(("partner",), items[0].hints)

    def test_query_yields_every_source_type_and_template_combination(self):
        items = build_frontier(
            specification(
                "query",
                {
                    "source_types": ["registry", "news"],
                    "query_templates": ["{entity} partnership", "{entity} merger"],
                },
            )
        )
        self.assertEqual(4, len(items))
        self.assertEqual(
            {("registry", "{entity} partnership"), ("registry", "{entity} merger"),
             ("news", "{entity} partnership"), ("news", "{entity} merger")},
            {(item.source_type, item.value) for item in items},
        )

    def test_an_unknown_strategy_is_a_specification_error(self):
        with self.assertRaises(SpecificationError):
            build_frontier(specification("crawl_everything", {"items": ["https://a.example"]}))

    def test_a_missing_frontier_is_a_specification_error(self):
        with self.assertRaises(SpecificationError):
            build_frontier({"scope": {"strategy": "enumerate"}})

    def test_an_empty_declared_frontier_is_a_specification_error(self):
        with self.assertRaises(SpecificationError):
            build_frontier(specification("enumerate", {"items": []}))


if __name__ == "__main__":
    unittest.main()
