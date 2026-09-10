"""Offline adapters for the acquisition ports.

Phase 1 ships adapters that need neither the network, nor a browser, nor a paid
API: material is read from a local corpus, content is normalized with the
standard library and extraction is deterministic and rule based. Production
adapters (Crawl4AI, Trafilatura, an LLM extractor) implement the same ports and
are selected in ``docs/analysis/2026-09-10-acquisition-core-oss-selection.md``.
"""

from aether_orbis.adapters.completion import (
    ConfiguredCompletionEvaluator,
    neighborhood_completeness,
    new_entity_saturation,
    window_coverage,
)
from aether_orbis.adapters.evaluators import (
    ConfiguredEvaluator,
    constant,
    duplicate_independence,
    keyword_coverage,
    mean_evidence_strength,
    mean_extraction_confidence,
    metadata_score,
)
from aether_orbis.adapters.extractors import (
    DictionaryExtractor,
    EntityDefinition,
    FailingExtractor,
)
from aether_orbis.adapters.fetchers import CorpusFetcher, StaticFetcher, load_corpus
from aether_orbis.adapters.parsers import HtmlTextParser, PlainTextParser, TrafilaturaParser
from aether_orbis.adapters.representations import (
    InMemoryGraphStore,
    InMemoryVectorIndex,
    KuzuGraphStore,
)

__all__ = [
    "ConfiguredCompletionEvaluator",
    "ConfiguredEvaluator",
    "CorpusFetcher",
    "DictionaryExtractor",
    "FailingExtractor",
    "EntityDefinition",
    "HtmlTextParser",
    "InMemoryGraphStore",
    "InMemoryVectorIndex",
    "KuzuGraphStore",
    "PlainTextParser",
    "StaticFetcher",
    "TrafilaturaParser",
    "constant",
    "duplicate_independence",
    "keyword_coverage",
    "load_corpus",
    "mean_evidence_strength",
    "mean_extraction_confidence",
    "metadata_score",
    "neighborhood_completeness",
    "new_entity_saturation",
    "window_coverage",
]
