#!/usr/bin/env python3
"""Compare content-extraction candidates on a small labelled HTML corpus.

Selection criteria for Phase 1, in order:

1. content recall — every labelled main-content fragment survives extraction,
   because evidence fragments must be verifiable verbatim in the stored text;
2. boilerplate rejection — navigation, forms, scripts and footers must not enter
   the text an evidence fragment is verified against;
3. offline determinism — the same input yields the same text without network,
   credentials or a browser runtime.

Run (no network, no credentials):

    python3 experiments/oss-candidates/content_extraction.py

Candidates that are not installed are reported as ``n/a`` instead of failing, so
the experiment stays reproducible on a stdlib-only checkout.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = Path(__file__).resolve().parent / "corpus"
sys.path.insert(0, str(ROOT / "src"))

from aether_orbis.adapters import HtmlTextParser  # noqa: E402
from aether_orbis.model import RawMaterial  # noqa: E402


def stdlib_parser(html: str) -> str:
    material = RawMaterial(
        url="https://example.org/experiment",
        payload=html.encode("utf-8"),
        media_type="text/html",
        retrieved_at="2026-09-10T09:00:00Z",
        published_at="2026-09-09T18:30:00Z",
    )
    text, _ = HtmlTextParser().parse(material)
    return text


def naive_strip_tags(html: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", html)


def trafilatura_extract(html: str) -> str:
    import trafilatura

    return trafilatura.extract(html, include_tables=True, include_comments=False) or ""


def readability_extract(html: str) -> str:
    import re

    from readability import Document

    return re.sub(r"<[^>]+>", " ", Document(html).summary())


CANDIDATES = {
    "stdlib html.parser": stdlib_parser,
    "naive strip-tags": naive_strip_tags,
    "trafilatura": trafilatura_extract,
    "readability-lxml": readability_extract,
}


def load_corpus() -> list[tuple[str, str, dict[str, list[str]]]]:
    labels = json.loads((CORPUS / "labels.json").read_text(encoding="utf-8"))
    return [
        (name, (CORPUS / name).read_text(encoding="utf-8"), label)
        for name, label in sorted(labels.items())
    ]


def measure(extract) -> tuple[float, float, float]:
    found = expected = leaked = boilerplate = 0
    extract("<html><body><p>warm up</p></body></html>")  # keep import cost out of the timing
    started = time.perf_counter()
    for _, html, label in load_corpus():
        text = extract(html)
        for fragment in label["content"]:
            expected += 1
            found += fragment in text
        for fragment in label["boilerplate"]:
            boilerplate += 1
            leaked += fragment in text
    elapsed = (time.perf_counter() - started) * 1000
    recall = found / expected if expected else 1.0
    rejection = 1 - leaked / boilerplate if boilerplate else 1.0
    return recall, rejection, elapsed


def main() -> int:
    print(f"{'candidate':<20} {'recall':>7} {'boilerplate rejected':>21} {'ms':>7}")
    for name, extract in CANDIDATES.items():
        try:
            recall, rejection, elapsed = measure(extract)
        except ImportError as error:
            print(f"{name:<20} {'n/a':>7} {'n/a':>21} {'n/a':>7}  ({error.name} not installed)")
            continue
        print(f"{name:<20} {recall:>7.2f} {rejection:>21.2f} {elapsed:>7.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
