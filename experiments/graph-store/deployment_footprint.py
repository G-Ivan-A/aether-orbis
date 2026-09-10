#!/usr/bin/env python3
"""Measure what each graph-store candidate costs to start locally and in CI.

Performance is only half of the ADR-001 question; the other half is whether a
contributor and a CI job can get the store running with one command, no network
and no credentials. This experiment measures that side:

1. dependency footprint — transitive packages pip would install (its resolver
   report, ``--dry-run``: nothing is installed);
2. installed size — on-disk size of the distribution when it is present;
3. cold start — time from process start to the first answered query, which is
   what a test suite pays on every run;
4. runtime requirement — whether a separate server, JVM or container must be
   running before the first query, which is what CI pays to set up.

Run:

    python3 experiments/graph-store/deployment_footprint.py

Candidates that need a server are reported from their documented requirement and
are deliberately *not* started here: a Phase 1 experiment that needs a container
would already have answered the question it is asking.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

COLD_START = {
    "kuzu": (
        "import kuzu, tempfile, os;"
        "d = tempfile.mkdtemp();"
        "c = kuzu.Connection(kuzu.Database(os.path.join(d, 'db')));"
        "c.execute('CREATE NODE TABLE N(id STRING, PRIMARY KEY (id))');"
        "c.execute(\"CREATE (n:N {id: 'a'})\");"
        "r = c.execute('MATCH (n:N) RETURN n.id');"
        "assert r.has_next()"
    ),
    "sqlite3": (
        "import sqlite3, tempfile, os;"
        "d = tempfile.mkdtemp();"
        "c = sqlite3.connect(os.path.join(d, 'db.sqlite3'));"
        "c.execute('CREATE TABLE n(id TEXT PRIMARY KEY)');"
        "c.execute(\"INSERT INTO n VALUES ('a')\");"
        "assert c.execute('SELECT id FROM n').fetchone()"
    ),
}


@dataclass(frozen=True)
class Candidate:
    """One candidate, its pip requirement and its documented runtime need."""

    name: str
    requirement: str | None
    module: str | None
    runtime: str


CANDIDATES = (
    Candidate("stdlib (dict + sqlite3)", None, "sqlite3", "none — in the interpreter"),
    Candidate("kuzu", "kuzu", "kuzu", "none — embedded in the process"),
    Candidate("neo4j (community)", "neo4j", None, "server: JVM or container, bolt port"),
    Candidate("postgres + apache age", "psycopg[binary]", None, "server: PostgreSQL with the AGE extension"),
)


def resolve(requirement: str) -> tuple[int, tuple[str, ...]]:
    """Return the package count and names pip would install for *requirement*."""

    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.json"
        result = subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--dry-run",
                "--ignore-installed", "--quiet", "--report", str(report), requirement,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip().splitlines()[-1] if result.stderr else "pip failed"
            )
        document = json.loads(report.read_text(encoding="utf-8"))
    names = sorted(item["metadata"]["name"] for item in document["install"])
    return len(names), tuple(names)


def installed_size_mb(module: str) -> float | None:
    """Return the on-disk size of *module* in MiB, or ``None`` if it is absent."""

    probe = subprocess.run(
        [sys.executable, "-c", f"import {module} as m; print(getattr(m, '__file__', '') or '')"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if probe.returncode != 0:
        return None
    path = probe.stdout.strip()
    if not path:
        return 0.0
    package = Path(path).parent
    if package.name in {"lib-dynload"} or not (package / "__init__.py").exists():
        return Path(path).stat().st_size / 1024 / 1024
    total = sum(item.stat().st_size for item in package.rglob("*") if item.is_file())
    return total / 1024 / 1024


def cold_start_ms(module: str, repeats: int) -> float | None:
    """Return the median cold-start-to-first-query time of *module*, in ms."""

    script = COLD_START.get(module)
    if script is None:
        return None
    timings = []
    for _ in range(repeats):
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        timings.append((time.perf_counter() - started) * 1000)
    return sorted(timings)[len(timings) // 2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5, help="cold-start repetitions")
    parser.add_argument("--names", action="store_true", help="print resolved package names")
    args = parser.parse_args()

    print(
        f"{'candidate':<24} {'packages':>9} {'size MiB':>9} {'cold ms':>9}  runtime requirement"
    )
    for candidate in CANDIDATES:
        packages = "0"
        names: tuple[str, ...] = ()
        if candidate.requirement is not None:
            try:
                count, names = resolve(candidate.requirement)
                packages = str(count)
            except RuntimeError as error:
                packages = "n/a"
                names = (str(error)[:60],)
        size = installed_size_mb(candidate.module) if candidate.module else None
        cold = cold_start_ms(candidate.module, args.repeats) if candidate.module else None
        print(
            f"{candidate.name:<24} {packages:>9} "
            f"{('n/a' if size is None else f'{size:.1f}'):>9} "
            f"{('n/a' if cold is None else f'{cold:.0f}'):>9}  {candidate.runtime}"
        )
        if args.names and names:
            print("    " + ", ".join(names))
    print("\nNothing was installed and nothing was written into the repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
