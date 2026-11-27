import json
import unittest
from unittest.mock import patch

from tests.support import ROOT
from tools.contract_validation import load_document, validate_instance

from aether_orbis.adapters.http_fetcher import (
    FetchError, HttpLimits, HttpResponse, HttpRssFetcher, SourceSelection, https_get,
)
from aether_orbis.adapters.profiles import build_profile_run
from aether_orbis.model import FrontierItem
from aether_orbis.ports import CollectingTelemetrySink

SEED = "https://habr.com/ru/feed/"
ARTICLE = "https://habr.com/ru/articles/12/"
SECOND = "https://habr.com/ru/articles/34/"
THIRD = "https://habr.com/ru/articles/56/"
FEED = "https://habr.com/ru/rss/search/?q=practice"
ROBOTS = "https://habr.com/robots.txt"
PAGE = (
    b'<meta property="article:published_time" content="2026-11-01T12:00:00Z">'
    b'<meta name="author" content="Fixture Author Sensitive">'
    b'<article>Software architecture, research methodology and knowledge engineering '
    b'were used to publish a traceable evaluation of deployment practices.</article>'
)
POLICY = HttpResponse(200, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /\n")


class HttpFetcherTests(unittest.TestCase):
    def setUp(self):
        self.seconds = 0.0
        self.calls = []
        self.responses = {ROBOTS: POLICY}

    def transport(self, url, timeout, max_bytes):
        self.calls.append((url, self.seconds, timeout, max_bytes))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response

    def pause(self, duration):
        self.seconds += duration

    def fetcher(self, selection, **limits):
        return HttpRssFetcher(
            selections={SEED: selection}, approval_reference="synthetic-fixture",
            limits=HttpLimits(**limits), transport=self.transport,
            timer=lambda: self.seconds, pause=self.pause,
        )

    def execute(self, fetcher):
        profile = load_document(
            ROOT / "configs/directions/hub-practice-analysis/research-profile.yaml"
        )
        runtime = load_document(ROOT / "configs/runtime/default.yaml")
        orchestrator = build_profile_run(profile, runtime, fetcher)
        telemetry = CollectingTelemetrySink()
        orchestrator.pipeline.telemetry = telemetry
        orchestrator.telemetry = telemetry
        return orchestrator.execute(), telemetry

    def test_manifest_rss_dedup_and_failure_reach_research_run(self):
        self.responses[ARTICLE] = HttpResponse(200, {"content-type": "text/html"}, PAGE)
        self.responses[FEED] = HttpResponse(200, {"content-type": "application/rss+xml"}, (
            f"<rss><channel><item><link>{ARTICLE}#duplicate</link></item>"
            f"<item><link>{SECOND}</link><pubDate>Tue, 03 Nov 2026 16:00:00 +0300</pubDate></item>"
            f"<item><link>{THIRD}</link></item></channel></rss>"
        ).encode())
        self.responses[SECOND] = HttpResponse(200, {"content-type": "text/html"}, PAGE)
        self.responses[THIRD] = TimeoutError("Fixture Author Sensitive")
        run, telemetry = self.execute(self.fetcher(SourceSelection((ARTICLE,), FEED)))
        self.assertEqual("PARTIAL", run.status)
        self.assertEqual(2, len(run.outcomes))
        self.assertEqual("allowed", run.outcomes[0].source.metadata["access_status"])
        self.assertEqual(ARTICLE.rstrip("/"), run.outcomes[0].source.canonical_url)
        self.assertEqual(SECOND.rstrip("/"), run.outcomes[1].source.canonical_url)
        self.assertEqual("2026-11-03T13:00:00Z", run.outcomes[1].source.published_at)
        self.assertEqual(["source_timeout"], [failure.access_code for failure in run.failures])
        self.assertIn("Source access failed (source_timeout).", run.document["outcome"]["gaps"])
        self.assertEqual([ROBOTS, ARTICLE, FEED, SECOND, THIRD], [call[0] for call in self.calls])
        self.assertEqual([0, 2, 4, 6, 8], [call[1] for call in self.calls])
        self.assertNotIn("Fixture Author Sensitive", json.dumps(telemetry.events))
        self.assertNotIn(THIRD, json.dumps(telemetry.events))
        self.assertEqual([], validate_instance(
            run.document, "research-run.schema.json", ROOT / "configs" / "schemas"
        ))

    def test_wildcard_robots_applies_to_redirect_target(self):
        self.responses[ROBOTS] = HttpResponse(
            200, {"content-type": "text/plain"}, b"User-agent: *\nDisallow: /*/34/$\n"
        )
        self.responses[ARTICLE] = HttpResponse(302, {"location": SECOND})
        run, _ = self.execute(self.fetcher(SourceSelection((ARTICLE, SECOND))))
        self.assertEqual("ZERO", run.status)
        self.assertTrue(all(failure.access_code == "source_robots_denied" for failure in run.failures))
        self.assertEqual([ROBOTS, ARTICLE], [call[0] for call in self.calls])

    def test_different_origin_redirect_and_rate_limit_stop_fetching(self):
        self.responses[ARTICLE] = HttpResponse(302, {"location": "https://outside.example/article"})
        self.responses[SECOND] = HttpResponse(429, {"retry-after": "1"})
        run, _ = self.execute(self.fetcher(SourceSelection((ARTICLE, SECOND, THIRD))))
        self.assertEqual("ZERO", run.status)
        self.assertEqual(
            ["source_scope_denied", "source_http_429", "source_origin_blocked"],
            [failure.access_code for failure in run.failures],
        )
        self.assertEqual([ROBOTS, ARTICLE, SECOND], [call[0] for call in self.calls])

    def test_manifest_stops_at_first_url_over_limit(self):
        self.responses[ARTICLE] = HttpResponse(200, {"content-type": "text/html"}, PAGE)
        results = list(self.fetcher(SourceSelection((ARTICLE, SECOND, THIRD)), max_urls=1).fetch(
            FrontierItem(strategy="enumerate", kind="item", value=SEED)
        ))
        self.assertEqual(2, len(results))
        self.assertEqual("source_url_limit", results[1].code)
        self.assertEqual([ROBOTS, ARTICLE], [call[0] for call in self.calls])

    def test_redirect_to_approved_article_does_not_retry_after_timeout(self):
        self.responses[ARTICLE] = HttpResponse(302, {"location": SECOND})
        self.responses[SECOND] = TimeoutError()
        run, _ = self.execute(self.fetcher(SourceSelection((ARTICLE, SECOND))))
        self.assertEqual(["source_timeout"], [failure.access_code for failure in run.failures])
        self.assertEqual([ROBOTS, ARTICLE, SECOND], [call[0] for call in self.calls])

    def test_delay_respects_remaining_run_time(self):
        run, _ = self.execute(self.fetcher(SourceSelection((ARTICLE,)), run_seconds=1.5))
        self.assertEqual("source_run_time_limit", run.failures[0].access_code)
        self.assertEqual([(ROBOTS, 0, 1.5, 1_000_000)], self.calls)

    def test_oversized_response_never_reaches_ingestion(self):
        self.responses[ARTICLE] = HttpResponse(200, {"content-type": "text/html"}, PAGE)
        run, _ = self.execute(self.fetcher(SourceSelection((ARTICLE,)), max_bytes=40))
        self.assertEqual("source_body_limit", run.failures[0].access_code)
        self.assertFalse(run.outcomes)

    def test_unavailable_robots_stops_article_and_dtd_is_rejected(self):
        self.responses[ROBOTS] = HttpResponse(404, {})
        run, _ = self.execute(self.fetcher(SourceSelection((ARTICLE,))))
        self.assertEqual("source_robots_unavailable", run.failures[0].access_code)
        self.assertEqual([ROBOTS], [call[0] for call in self.calls])

        self.responses[ROBOTS] = POLICY
        self.responses[FEED] = HttpResponse(
            200, {"content-type": "application/rss+xml"},
            b"<!DOCTYPE rss><rss><channel></channel></rss>",
        )
        run, _ = self.execute(self.fetcher(SourceSelection(habr_rss=FEED)))
        self.assertEqual("rss_invalid", run.failures[0].access_code)

    def test_private_resolved_address_refused_before_socket_creation(self):
        answers = [(2, 1, 6, "", ("127.0.0.1", 443))]
        with patch("socket.getaddrinfo", return_value=answers), patch("socket.socket") as sock:
            with self.assertRaisesRegex(FetchError, "source_address_denied"):
                https_get("https://fixture.example/a", 1, 100)
        sock.assert_not_called()
