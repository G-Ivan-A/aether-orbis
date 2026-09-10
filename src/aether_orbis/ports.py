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
