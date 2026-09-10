"""Ingestion: acquisition, normalization and content identity.

Ingestion carries no selection, preservation or termination criteria. It only
turns raw material into a :class:`~aether_orbis.model.NormalizedSource` with the
mandatory ``source_id``, ``canonical_url``, ``content_hash``, ``retrieved_at``,
``published_at`` and the parser version (``extraction-contract.md`` O-2).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable, Iterator
from urllib.parse import urlsplit, urlunsplit

from aether_orbis.errors import MalformedSourceError
from aether_orbis.grouping import SourceGrouper
from aether_orbis.model import FrontierItem, NormalizedSource, RawMaterial
from aether_orbis.ports import ContentParser, SourceFetcher

DEFAULT_PORTS = {"http": "80", "https": "443"}
_BLANK_LINES = re.compile(r"\n{3,}")


def canonicalize_url(url: str) -> str:
    """Return the canonical form of *url*.

    Only representation-preserving normalization is applied: the scheme and host
    are lowercased, a default port and the fragment are dropped and a trailing
    slash is removed from a non-empty path. Query parameters are never reordered
    or removed, because in Phase 1 two materials are grouped by exact canonical
    URL equality.
    """

    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        raise MalformedSourceError(f"source URL is not absolute: {url!r}")

    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    netloc = host.lower()
    if parts.port is not None and str(parts.port) != DEFAULT_PORTS.get(scheme):
        netloc = f"{netloc}:{parts.port}"
    if parts.username:
        credentials = parts.username
        if parts.password:
            credentials = f"{credentials}:{parts.password}"
        netloc = f"{credentials}@{netloc}"

    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    return urlunsplit((scheme, netloc, path, parts.query, ""))


def normalize_text(text: str) -> str:
    """Return the normalized text that evidence fragments are verified against."""

    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def content_hash(text: str) -> str:
    """Return the ``sha256:`` digest of normalized *text*."""

    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def source_id_for(canonical_url: str, digest: str) -> str:
    """Return a deterministic ``source_id`` for a canonical URL and content hash."""

    fingerprint = sha256(f"{canonical_url}\n{digest}".encode("utf-8")).hexdigest()
    return f"src-{fingerprint[:16]}"


def normalize_timestamp(value: Any, field_name: str) -> str:
    """Return *value* as an RFC 3339 UTC timestamp."""

    if not isinstance(value, str) or not value.strip():
        raise MalformedSourceError(f"{field_name} is required")
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as error:
        raise MalformedSourceError(f"{field_name} is not a valid timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def decode_payload(material: RawMaterial) -> str:
    """Decode the raw payload, refusing material that is not text."""

    payload = material.payload
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, (bytes, bytearray)):
        raise MalformedSourceError("source payload must be bytes or str")
    try:
        return bytes(payload).decode("utf-8")
    except UnicodeDecodeError as error:
        raise MalformedSourceError(
            f"source payload is not valid UTF-8: {material.url!r}"
        ) from error


def ingest_material(
    material: RawMaterial,
    parser: ContentParser,
    grouper: SourceGrouper,
) -> NormalizedSource:
    """Normalize one raw material into a contractual source.

    An empty but well-formed document is normal: it yields a source with empty
    text. Material without an absolute URL, without a publication timestamp or
    with an undecodable payload is malformed and raises
    :class:`~aether_orbis.errors.MalformedSourceError`.
    """

    canonical_url = canonicalize_url(material.url)
    decode_payload(material)

    text, metadata = parser.parse(material)
    if not isinstance(text, str):
        raise MalformedSourceError(f"parser returned no text for {canonical_url!r}")
    text = normalize_text(text)

    published_at = material.published_at or metadata.get("published_at")
    retrieved_at = normalize_timestamp(material.retrieved_at, "retrieved_at")
    published_at = normalize_timestamp(published_at, "published_at")

    digest = content_hash(text)
    return NormalizedSource(
        source_id=source_id_for(canonical_url, digest),
        source_group_id=grouper.group_for(canonical_url, digest),
        canonical_url=canonical_url,
        content_hash=digest,
        retrieved_at=retrieved_at,
        published_at=published_at,
        parser_version=parser.parser_version,
        media_type=material.media_type,
        text=text,
        metadata={key: value for key, value in metadata.items() if key != "published_at"},
    )


def ingest_frontier(
    items: Iterable[FrontierItem],
    fetcher: SourceFetcher,
    parser: ContentParser,
    grouper: SourceGrouper,
) -> Iterator[tuple[FrontierItem, RawMaterial, NormalizedSource | None, Exception | None]]:
    """Yield an ingestion attempt per material discovered on the frontier.

    Malformed material is reported instead of raising, so that one bad document
    cannot terminate a research run.
    """

    for item in items:
        for material in fetcher.fetch(item):
            try:
                yield item, material, ingest_material(material, parser, grouper), None
            except MalformedSourceError as error:
                yield item, material, None, error
