"""Source fetchers.

Phase 1 fetches from a local corpus: a manifest lists the materials that a
frontier item resolves to, and the payloads live next to it as files. This keeps
integration runs reproducible and free of network access, credentials and rate
limits. A Crawl4AI adapter implements the same port behind the same manifest
shape.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from aether_orbis.model import FrontierItem, RawMaterial

MANIFEST_NAME = "manifest.json"


def load_corpus(directory: Path | str) -> dict[str, tuple[RawMaterial, ...]]:
    """Load a fixture corpus keyed by frontier item value.

    The manifest maps a frontier item value to a list of material descriptors::

        {"Sber": [{"url": "...", "media_type": "text/html",
                   "retrieved_at": "...", "published_at": "...",
                   "payload_file": "sber.html"}]}

    ``payload_file`` is read as bytes so that decoding stays the responsibility
    of ingestion, which is where malformed material must be reported.
    """

    root = Path(directory)
    manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    corpus: dict[str, tuple[RawMaterial, ...]] = {}
    for key, descriptors in manifest.items():
        materials = []
        for descriptor in descriptors:
            payload_file = descriptor.get("payload_file")
            if payload_file is not None:
                payload = (root / payload_file).read_bytes()
            else:
                payload = descriptor.get("payload", "").encode("utf-8")
            materials.append(
                RawMaterial(
                    url=descriptor["url"],
                    payload=payload,
                    media_type=descriptor.get("media_type", "text/html"),
                    retrieved_at=descriptor["retrieved_at"],
                    published_at=descriptor.get("published_at"),
                    metadata=dict(descriptor.get("metadata", {})),
                )
            )
        corpus[key] = tuple(materials)
    return corpus


@dataclass
class CorpusFetcher:
    """Resolves frontier items against a preloaded corpus."""

    corpus: dict[str, tuple[RawMaterial, ...]] = field(default_factory=dict)

    @classmethod
    def from_directory(cls, directory: Path | str) -> "CorpusFetcher":
        return cls(load_corpus(directory))

    def fetch(self, item: FrontierItem) -> Iterable[RawMaterial]:
        """Return the materials registered for *item*; an unknown item is empty.

        An unresolved frontier item is not an error: discovery legitimately
        produces queries and seeds that yield nothing.
        """

        return self.corpus.get(item.value, ())


@dataclass
class StaticFetcher:
    """Returns the same materials for every frontier item."""

    materials: tuple[RawMaterial, ...] = ()

    def fetch(self, item: FrontierItem) -> Iterable[RawMaterial]:
        return self.materials


def descriptor_of(material: RawMaterial, payload_file: str) -> dict[str, Any]:
    """Return a manifest descriptor for *material* (used by fixture tooling)."""

    descriptor: dict[str, Any] = {
        "url": material.url,
        "media_type": material.media_type,
        "retrieved_at": material.retrieved_at,
        "payload_file": payload_file,
    }
    if material.published_at is not None:
        descriptor["published_at"] = material.published_at
    if material.metadata:
        descriptor["metadata"] = dict(material.metadata)
    return descriptor
