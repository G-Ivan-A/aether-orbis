"""Helpers shared by the acquisition core tests."""

from __future__ import annotations

from tests import paths as paths  # noqa: F401

from pathlib import Path
from typing import Any

from aether_orbis.adapters import PlainTextParser
from aether_orbis.grouping import SourceGrouper
from aether_orbis.ingestion import ingest_material
from aether_orbis.model import NormalizedSource, RawMaterial

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "configs" / "schemas"
FIXTURES = ROOT / "tests" / "fixtures"
ACQUISITION = FIXTURES / "acquisition"

RETRIEVED_AT = "2026-09-10T09:00:00Z"
PUBLISHED_AT = "2026-09-09T18:30:00Z"


def raw(
    url: str = "https://example.com/article",
    text: str = "Example Organization partnered with Example Registry.",
    **overrides: Any,
) -> RawMaterial:
    """Return raw material with contractual defaults."""

    payload = overrides.pop("payload", text.encode("utf-8"))
    return RawMaterial(
        url=url,
        payload=payload,
        media_type=overrides.pop("media_type", "text/plain"),
        retrieved_at=overrides.pop("retrieved_at", RETRIEVED_AT),
        published_at=overrides.pop("published_at", PUBLISHED_AT),
        metadata=overrides.pop("metadata", {}),
    )


def source(
    text: str = "Example Organization partnered with Example Registry.",
    url: str = "https://example.com/article",
    grouper: SourceGrouper | None = None,
    **overrides: Any,
) -> NormalizedSource:
    """Return a normalized source built through real ingestion."""

    return ingest_material(
        raw(url=url, text=text, **overrides),
        PlainTextParser(),
        grouper if grouper is not None else SourceGrouper(),
    )
