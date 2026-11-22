import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import runpy
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import yaml

from tests.support import ROOT
from tools.contract_validation import load_document, validate_instance

from aether_orbis.adapters.http_fetcher import HttpResponse, HttpRssFetcher


class ProfileRunTests(unittest.TestCase):
    def test_one_command_runs_two_directions_from_yaml(self):
        directions = {
            "hub-practice-analysis": (
                "https://habr.com/ru/feed/",
                "Software architecture, research methodology and knowledge engineering "
                "were used to publish a traceable evaluation of deployment practices.",
                "CONDITIONAL",
            ),
            "reputation-technologies": (
                "Global Reputation Alliance",
                "This synthetic Global Reputation Alliance entry documents technology adoption and partner "
                "work through signed records, independently verified records and other "
                "evidence that can be checked in the registered archive.",
                "QUALIFIED",
            ),
        }
        for direction, (frontier, body, decision) in directions.items():
            with self.subTest(direction=direction), TemporaryDirectory() as directory:
                corpus = Path(directory)
                tracked = ROOT / "configs" / "directions" / direction / "research-profile.yaml"
                profile = load_document(tracked)
                profile["offline_adapters"]["source_authority"] = {"fixture.example": 0.9}
                profile_file = corpus / "profile.yaml"
                profile_file.write_text(yaml.safe_dump(profile), encoding="utf-8")
                (corpus / "manifest.json").write_text(json.dumps({
                    frontier: [{
                        "url": "https://fixture.example/synthetic",
                        "published_at": "2026-11-01T08:00:00Z",
                        "retrieved_at": "2026-11-02T08:00:00Z",
                        "payload": f"<article><p>{body}</p></article>",
                    }],
                }), encoding="utf-8")
                execution = self._run(profile_file, corpus)
                self.assertEqual(0, execution.returncode, execution.stderr)
                output = json.loads(execution.stdout)
                self.assertEqual(
                    {"id": direction, "version": profile["profile_version"]}, output["run"]["profile"],
                )
                self.assertEqual(direction, output["run"]["specification"]["id"])
                self.assertEqual(decision, output["run"]["decisions"][0]["decision"], output)
                self.assertEqual([], validate_instance(
                    output["run"], "research-run.schema.json", ROOT / "configs" / "schemas"
                ))

    def test_schema_failure_precedes_reading_the_corpus(self):
        tracked = ROOT / "configs" / "directions" / "hub-practice-analysis" / "research-profile.yaml"
        profile = copy.deepcopy(load_document(tracked))
        profile["offline_adapters"]["triage"] = ["evidence_strength"]
        with TemporaryDirectory() as directory:
            profile_file = Path(directory) / "invalid.yaml"
            profile_file.write_text(yaml.safe_dump(profile), encoding="utf-8")
            execution = self._run(profile_file, Path(directory) / "missing")
        self.assertEqual(2, execution.returncode)
        self.assertIn("has no triage measurement", execution.stderr)
        self.assertNotIn("manifest.json", execution.stderr)

    def test_approved_manifest_is_loaded_through_the_operator_entry_point(self):
        def transport(url, timeout, max_bytes):
            self.assertEqual("https://fixture.example/robots.txt", url)
            return HttpResponse(403, {})

        tracked = ROOT / "configs/directions/hub-practice-analysis/research-profile.yaml"
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "http.yaml"
            manifest.write_text(yaml.safe_dump({
                "approval_reference": "synthetic-fixture",
                "frontier": {"https://habr.com/ru/feed/": {"urls": ["https://fixture.example/finding/"]}},
            }), encoding="utf-8")
            arguments = ["run-research-profile.py", "--profile", str(tracked), "--http-sources", str(manifest)]
            output = StringIO()
            with patch.object(sys, "argv", arguments), redirect_stdout(output), patch(
                "aether_orbis.adapters.http_fetcher.HttpRssFetcher",
                side_effect=lambda **kwargs: HttpRssFetcher(transport=transport, **kwargs),
            ):
                self.assertEqual(0, runpy.run_path(str(ROOT / "tools/run-research-profile.py"))["main"]())
        result = json.loads(output.getvalue())
        self.assertEqual("ZERO", result["run"]["outcome"]["status"])
        self.assertEqual(["source_http_403"], result["failures"])
        self.assertIn("Source access failed (source_http_403).", result["run"]["outcome"]["gaps"])

    def _run(self, profile: Path, corpus: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / "run-research-profile.py"),
             "--profile", str(profile), "--corpus", str(corpus)],
            capture_output=True, text=True, timeout=15, check=False,
        )
