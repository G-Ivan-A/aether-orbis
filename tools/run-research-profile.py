#!/usr/bin/env python3
"""Run a validated Research Profile against a local corpus."""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import yaml

from aether_orbis.adapters.fetchers import CorpusFetcher
from aether_orbis.adapters.profiles import build_profile_run
from aether_orbis.errors import SpecificationError
from tools.contract_validation import load_document, validate_instance


def load_config(path: Path, schema_name: str) -> dict:
    document = load_document(path)
    errors = validate_instance(document, schema_name, ROOT / "configs" / "schemas")
    if errors:
        raise SpecificationError(f"{path.name}: " + "\n".join(errors))
    return document


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--runtime", type=Path, default=ROOT / "configs" / "runtime" / "default.yaml")
    parser.add_argument("--corpus", required=True, type=Path)
    args = parser.parse_args()
    try:
        profile = load_config(args.profile, "research-profile.schema.json")
        runtime = load_config(args.runtime, "runtime-configuration.schema.json")
        if "offline_adapters" not in profile:
            raise SpecificationError("the profile needs offline_adapters for this entry point")
        fetcher = CorpusFetcher.from_directory(args.corpus)
        result = build_profile_run(profile, runtime, fetcher).execute()
    except (SpecificationError, OSError, yaml.YAMLError, ValueError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps({
        "run": result.document,
        "failures": [failure.reason for failure in result.failures],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
