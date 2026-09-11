"""Ports that isolate the acquisition core from external systems.

Every dependency that would otherwise require the network, a browser, a paid API
or a production store is expressed here as a protocol. Adapters live in
:mod:`aether_orbis.adapters`; tests supply offline doubles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol, runtime_checkable

from aether_orbis.model import (
    ExtractionCandidates,
    FrontierItem,
    Measurement,
    NormalizedSource,
    RawMaterial,
)
from aether_orbis.representations import GraphProjection, VectorChunk
from aether_orbis.sufficiency import CompletionState


@runtime_checkable
class SourceFetcher(Protocol):
    """Retrieves raw material for one frontier item."""

    def fetch(self, item: FrontierItem) -> Iterable[RawMaterial]:
        """Yield every raw material discovered for *item*."""


@runtime_checkable
class ContentParser(Protocol):
    """Normalizes raw material into plain text plus metadata."""

    parser_version: str

    def parse(self, material: RawMaterial) -> tuple[str, dict[str, Any]]:
        """Return normalized text and metadata for *material*."""


@runtime_checkable
class KnowledgeExtractor(Protocol):
    """Proposes entities, relations and claims for a normalized source."""

    extractor_version: str
    model: str

    def extract(self, source: NormalizedSource) -> ExtractionCandidates:
        """Return extraction candidates; verification stays in the core."""


@runtime_checkable
class CharacteristicEvaluator(Protocol):
    """Measures the named characteristics declared by a Research Specification."""

    def measure(
        self,
        stage: str,
        source: NormalizedSource,
        extraction: dict[str, Any] | None,
        dimensions: tuple[str, ...],
    ) -> dict[str, Measurement]:
        """Return a measurement per characteristic name."""


@runtime_checkable
class GraphStore(Protocol):
    """Indexes the graph representation of the qualified knowledge stream.

    ADR-001 (4) keeps graph and vector parallel, so this port knows nothing about
    :class:`VectorIndex`: a run with only one of the two configured still
    completes.
    """

    def index_graph(self, projection: GraphProjection) -> None:
        """Index *projection*; repeating the same projection MUST be idempotent."""

    def provenance(self, node_id: str) -> tuple[dict[str, Any], ...]:
        """Return the provenance of every edge that touches *node_id*."""


@runtime_checkable
class VectorIndex(Protocol):
    """Indexes the vector representation of the same knowledge stream."""

    def index_chunks(self, chunks: Iterable[VectorChunk]) -> None:
        """Index *chunks*; repeating the same chunks MUST be idempotent."""

    def search(self, query: str, limit: int = 5) -> tuple[VectorChunk, ...]:
        """Return the chunks most similar to *query*, best match first."""


@runtime_checkable
class CompletionEvaluator(Protocol):
    """Measures the completion dimensions declared by a Research Specification.

    The names are supplied by the caller and originate from
    ``termination.completion_dimensions``; the port never invents its own
    (sufficiency-gate-contract O-3).
    """

    def measure_completion(
        self, state: CompletionState, dimensions: tuple[str, ...]
    ) -> dict[str, Measurement]:
        """Return a measurement per completion dimension name."""


@runtime_checkable
class TelemetrySink(Protocol):
    """Receives telemetry events emitted at every transition."""

    def emit(self, event: dict[str, Any]) -> None:
        """Record one telemetry event document."""


@dataclass
class CollectingTelemetrySink:
    """In-memory telemetry sink used by tests and local runs."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    def by_role(self, operation_role: str) -> list[dict[str, Any]]:
        """Return every recorded event with the given ``operation_role``."""

        return [event for event in self.events if event["operation_role"] == operation_role]
