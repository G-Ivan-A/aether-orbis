from dataclasses import replace
import importlib.util
import json
from os import environ
import unittest
from unittest.mock import Mock, patch

import yaml

from tests.support import ROOT
from tools.contract_validation import load_document, validate_instance

from aether_orbis.adapters.fetchers import StaticFetcher
from aether_orbis.adapters.model_extraction import RoutedPracticeExtractor, build_routed_profile_run
from aether_orbis.adapters.model_router import ModelReply, ModelRouteError, ModelRouter
from aether_orbis.extraction import build_extraction_result
from aether_orbis.model import NormalizedSource, RawMaterial
from aether_orbis.ports import CollectingTelemetrySink

BASE_ROUTE = {
    "model": "fixture-model",
    "api_base": "https://model.example/v1",
    "api_key_env": "AETHER_ORBIS_FIXTURE_KEY",
    "timeout_seconds": 3,
    "max_tokens": 100,
    "usd_to_rub": 90,
}
PROMPT = "SYNTHETIC_PAYLOAD_MARKER"
REPLY = ModelReply("response", "fixture-model", 20, 10, 4, 0.005)


class ModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.runtime = {
            "models": {"extraction": "first"},
            "model_routes": {"first": BASE_ROUTE, "second": BASE_ROUTE | {"model": "second-model"}},
        }
        self.backend = Mock(return_value=REPLY)
        self.telemetry = CollectingTelemetrySink()
        self.router = ModelRouter(
            self.runtime, "run-test", "profile-test", self.telemetry,
            approve=lambda role, route, prompt: True, backend=self.backend,
        )

    def test_yaml_mapping_selects_route_and_emits_only_metrics(self):
        self.assertEqual("response", self.router.complete("extraction", PROMPT))
        self.assertEqual("first", self.backend.call_args.args[0].route_id)
        self.runtime["models"]["extraction"] = "second"
        self.backend.return_value = replace(REPLY, model="second-model")
        self.assertEqual("response", self.router.complete("extraction", PROMPT))
        call = self.telemetry.events[-1]["model_call"]
        self.assertEqual(("second", "second-model", 0.45), (call["route"], call["model"], call["cost_rub"]))
        self.assertNotIn(PROMPT, json.dumps(self.telemetry.events))
        self.assert_events_valid()

    def test_approved_model_extraction_runs_through_the_profile(self):
        profile = load_document(ROOT / "configs/directions/hub-practice-analysis/research-profile.yaml")
        runtime = load_document(ROOT / "configs/runtime/default.yaml")
        runtime["model_routes"] = self.runtime["model_routes"]
        runtime["models"]["extraction"] = "second"
        runtime = yaml.safe_load(yaml.safe_dump(runtime))
        self.assertEqual([], validate_instance(
            runtime, "runtime-configuration.schema.json", ROOT / "configs" / "schemas",
        ))
        quote = "Software architecture and research methodology were used to validate this practice."
        material = RawMaterial(
            url="https://fixture.example/sample", payload=f"<article>{quote}</article>", media_type="text/html",
            retrieved_at="2026-11-02T12:00:00Z", published_at="2026-11-01T12:00:00Z",
        )
        self.backend.return_value = replace(REPLY, model="second-model", text=json.dumps([
            {"technology": "Software architecture", "claim": "A team used software architecture",
             "evidence": quote, "extraction_confidence": 0.8, "evidence_strength": 0.9},
        ]))
        approve = Mock(return_value=True)
        orchestrator = build_routed_profile_run(
            profile, runtime, StaticFetcher((material,)), project_text=lambda source: source.text,
            approve=approve, telemetry=self.telemetry, backend=self.backend,
        )
        run = orchestrator.execute()
        extraction = run.outcomes[0].extraction
        self.assertEqual("A team used software architecture", extraction["claims"][0]["claim"])
        route, prompt = self.backend.call_args.args
        self.assertEqual("second", route.route_id)
        approve.assert_called_once_with("extraction", route, prompt)
        event, = (event for event in self.telemetry.events if event["operation_role"] == "model_routing")
        self.assertEqual(run.document["run_id"], event["run_id"])
        self.assertNotIn(quote, json.dumps(self.telemetry.events))
        self.assert_events_valid()

    def test_unknown_and_denied_calls_never_reach_the_backend(self):
        self.router.approve = None
        with self.assertRaisesRegex(ModelRouteError, "model_route_unavailable"):
            self.router.complete("analysis", PROMPT)
        with self.assertRaisesRegex(ModelRouteError, "model_payload_denied"):
            self.router.complete("extraction", PROMPT)
        self.backend.assert_not_called()
        self.assert_events_valid()

    def test_failure_and_response_model_mismatch_are_visible_without_retry(self):
        self.backend.side_effect = RuntimeError(PROMPT)
        with self.assertRaisesRegex(ModelRouteError, "model_request_failed") as caught:
            self.router.complete("extraction", PROMPT)
        self.assertNotIn(PROMPT, str(caught.exception))
        self.assertEqual(1, self.backend.call_count)
        self.backend.side_effect = None
        self.backend.return_value = replace(REPLY, model="unknown")
        with self.assertRaisesRegex(ModelRouteError, "model_route_mismatch"):
            self.router.complete("extraction", PROMPT)
        self.assertEqual(2, self.backend.call_count)
        self.assertNotIn(PROMPT, json.dumps(self.telemetry.events))
        self.assert_events_valid()

    def test_model_extractor_verifies_evidence_against_local_provenance(self):
        quote = "A synthetic team deploys PracticeTool."
        source = NormalizedSource(
            "src-token", "group-token", "https://source.example/author", "sha256:" + "0" * 64,
            "2026-11-22T00:00:00Z", "2026-11-21T00:00:00Z", "test/1.0", "text/plain",
            quote, {"author": "Sensitive Author"},
        )
        self.backend.return_value = replace(REPLY, text=json.dumps([
            {"technology": "PracticeTool", "claim": "PracticeTool was deployed", "evidence": quote,
             "extraction_confidence": 0.8, "evidence_strength": 0.9},
            {"technology": "HallucinatedTool", "claim": "Generated claim", "evidence": "HallucinatedTool",
             "extraction_confidence": 0.8, "evidence_strength": 0.9},
        ]))
        extractor = RoutedPracticeExtractor(self.router, lambda source: source.text)
        candidates = extractor.extract(source)
        result = build_extraction_result(
            source, candidates, model=extractor.model, extractor_version=extractor.extractor_version,
            extracted_at="2026-11-22T12:00:00Z",
        )
        self.assertEqual("partial", result.status)
        self.assertEqual("PracticeTool was deployed", result.document["claims"][0]["claim"])
        self.assertEqual(1, len(result.document["claims"]))
        prompt = self.backend.call_args.args[1]
        self.assertIn(quote, prompt)
        self.assertNotIn("Sensitive Author", prompt)
        self.assertNotIn(source.canonical_url, prompt)

    @unittest.skipUnless(importlib.util.find_spec("litellm"), "optional LiteLLM SDK is not installed")
    def test_litellm_sdk_uses_the_approved_endpoint_and_does_not_redirect(self):
        import httpx

        requests = []

        def server(request):
            requests.append((str(request.url), json.loads(request.content)))
            if len(requests) == 2:
                return httpx.Response(307, headers={"location": "https://unexpected.example/v1"})
            return httpx.Response(200, json={
                "id": "completion-fixture", "object": "chat.completion", "created": 1795370000,
                "model": "fixture-model",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": "synthetic reply"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            })

        class OfflineClient(httpx.Client):
            def __init__(self, **kwargs):
                kwargs["transport"] = httpx.MockTransport(server)
                super().__init__(**kwargs)

        router = ModelRouter(
            self.runtime, "run-test", "profile-test", self.telemetry,
            approve=lambda role, route, prompt: True,
        )
        with patch.dict(environ, {"AETHER_ORBIS_FIXTURE_KEY": "test-only"}), patch("httpx.Client", OfflineClient):
            self.assertEqual("synthetic reply", router.complete("extraction", PROMPT))
            with self.assertRaisesRegex(ModelRouteError, "model_request_failed"):
                router.complete("extraction", PROMPT)
        self.assertEqual(2, len(requests))
        self.assertEqual({"https://model.example/v1/chat/completions"}, {url for url, _ in requests})
        self.assertEqual("fixture-model", requests[0][1]["model"])
        self.assertEqual([{"role": "user", "content": PROMPT}], requests[0][1]["messages"])
        self.assert_events_valid()

    def assert_events_valid(self):
        for event in self.telemetry.events:
            self.assertEqual([], validate_instance(
                event, "telemetry-event.schema.json", ROOT / "configs" / "schemas"
            ))
