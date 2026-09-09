#!/usr/bin/env python3
"""Validate all tracked contract artifacts in the repository."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.contract_validation import iter_repository_artifacts, validate_repository  # noqa: E402


def main() -> int:
    errors = validate_repository(ROOT)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    artifact_count = sum(1 for _ in iter_repository_artifacts(ROOT))
    print(f"Validated {artifact_count} contract artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
