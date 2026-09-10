"""Content parsers.

``HtmlTextParser`` uses only the standard library so that the contract suite
runs without optional dependencies. ``TrafilaturaParser`` is the selected
production adapter; it imports its dependency lazily and therefore never breaks
an offline test run.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from aether_orbis.model import RawMaterial

IGNORED_TAGS = {"script", "style", "noscript", "template"}
BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer", "li", "tr", "br",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre",
}
BOILERPLATE_TAGS = {"nav", "footer", "aside", "form"}


class _TextCollector(HTMLParser):
    """Collects visible text and drops obvious boilerplate containers."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self.title: str | None = None
        self.metadata: dict[str, str] = {}
        self._ignored_depth = 0
        self._boilerplate_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in IGNORED_TAGS:
            self._ignored_depth += 1
        elif tag in BOILERPLATE_TAGS:
            self._boilerplate_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self._read_meta(dict(attrs))
        if tag in BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in IGNORED_TAGS:
            self._ignored_depth = max(self._ignored_depth - 1, 0)
        elif tag in BOILERPLATE_TAGS:
            self._boilerplate_depth = max(self._boilerplate_depth - 1, 0)
        elif tag == "title":
            self._in_title = False
        if tag in BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title and data.strip():
            self.title = data.strip()
            return
        if self._ignored_depth or self._boilerplate_depth:
            return
        if data.strip():
            self.chunks.append(" ".join(data.split()))

    def _read_meta(self, attrs: dict[str, str | None]) -> None:
        name = attrs.get("name") or attrs.get("property")
        content = attrs.get("content")
        if name and content:
            self.metadata[name.lower()] = content


@dataclass
class HtmlTextParser:
    """Normalizes HTML into plain text with the standard library only."""

    parser_version: str = "html-text-parser/1.0"

    def parse(self, material: RawMaterial) -> tuple[str, dict[str, Any]]:
        payload = material.payload
        text = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
        collector = _TextCollector()
        collector.feed(text)
        collector.close()

        metadata: dict[str, Any] = dict(material.metadata)
        if collector.title:
            metadata.setdefault("title", collector.title)
        for key in ("article:published_time", "date", "published_time"):
            if key in collector.metadata:
                metadata.setdefault("published_at", collector.metadata[key])
                break
        for key, value in collector.metadata.items():
            metadata.setdefault(f"meta_{key.replace(':', '_')}", value)

        return "".join(collector.chunks), metadata


@dataclass
class PlainTextParser:
    """Passes already normalized text through unchanged."""

    parser_version: str = "plain-text-parser/1.0"

    def parse(self, material: RawMaterial) -> tuple[str, dict[str, Any]]:
        payload = material.payload
        text = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
        return text, dict(material.metadata)


@dataclass
class TrafilaturaParser:
    """Production content adapter built on Trafilatura (ADR-001, start choice).

    The dependency is imported lazily: an installation without Trafilatura still
    runs the whole contract suite through :class:`HtmlTextParser`.
    """

    parser_version: str = "trafilatura/2.x"
    fallback: HtmlTextParser = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.fallback is None:
            self.fallback = HtmlTextParser()

    def parse(self, material: RawMaterial) -> tuple[str, dict[str, Any]]:
        try:
            import trafilatura  # noqa: PLC0415  (optional dependency, imported lazily)
        except ImportError:
            return self.fallback.parse(material)

        payload = material.payload
        text = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else payload
        extracted = trafilatura.extract(text, include_comments=False, include_tables=True)
        if not extracted:
            return self.fallback.parse(material)
        _, metadata = self.fallback.parse(material)
        return extracted, metadata
