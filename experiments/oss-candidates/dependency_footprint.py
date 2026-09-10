#!/usr/bin/env python3
"""Measure the installation footprint of the OSS candidates of ADR-001.

The acquisition core must stay runnable offline and without paid APIs, so the
number of transitive packages a candidate drags in is a selection criterion, not
a detail. The measurement uses pip's own resolver report instead of installing
anything:

    python3 experiments/oss-candidates/dependency_footprint.py

The only step that needs network access is pip's resolution; nothing is
installed and no artifact is written into the repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = (
    "trafilatura==2.2.0",
    "crawl4ai",
    "playwright",
    "scrapegraphai",
    "readability-lxml",
)


def resolve(requirement: str) -> tuple[int, tuple[str, ...]]:
    """Return the package count and names pip would install for *requirement*."""

    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.json"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--dry-run",
                "--ignore-installed",
                "--quiet",
                "--report",
                str(report),
                requirement,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr else "pip failed")
        document = json.loads(report.read_text(encoding="utf-8"))

    names = sorted(item["metadata"]["name"] for item in document["install"])
    return len(names), tuple(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", nargs="*", default=list(CANDIDATES))
    parser.add_argument("--names", action="store_true", help="print resolved package names")
    args = parser.parse_args()

    print(f"{'requirement':<22} {'packages':>8}")
    for requirement in args.requirements or CANDIDATES:
        try:
            count, names = resolve(requirement)
        except RuntimeError as error:
            print(f"{requirement:<22} {'n/a':>8}  ({error})")
            continue
        print(f"{requirement:<22} {count:>8}")
        if args.names:
            print("    " + ", ".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
