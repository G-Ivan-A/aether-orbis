"""Single call boundary for a configured, explicitly approved model route."""

from dataclasses import dataclass, field
from math import isfinite
from os import environ
import re
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit
from uuid import uuid4

from aether_orbis.clock import Clock, SystemClock
from aether_orbis.ports import TelemetrySink
from aether_orbis.telemetry import build_event

ROLES = frozenset({
    "extraction", "triage", "full_evaluation", "knowledge_building", "sufficiency", "analysis",
})
MAX_PROMPT_CHARS = 32_000
MAX_REPLY_CHARS = 64_000
ROUTE_ERRORS = frozenset({
    "model_route_unavailable", "model_route_invalid", "model_payload_out_of_bounds",
    "model_payload_denied", "model_route_mismatch", "model_response_invalid",
    "model_credential_missing",
})


class ModelRouteError(Exception):
    """A stable error code suitable for operator diagnostics."""


@dataclass(frozen=True)
class ModelRoute:
    route_id: str
    model: str
    api_base: str
    api_key_env: str
    timeout_seconds: int
    max_tokens: int
    usd_to_rub: float | None = None

    def __post_init__(self) -> None:
        url = urlsplit(self.api_base)
        if (
            url.scheme != "https" or not url.hostname or url.username is not None
            or url.query or url.fragment or re.search(r"[\s\\]", self.api_base)
            or not re.fullmatch(r"AETHER_ORBIS_[A-Z0-9_]+", self.api_key_env)
            or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]*", self.model)
            or not 1 <= self.timeout_seconds <= 120 or not 1 <= self.max_tokens <= 8192
            or (self.usd_to_rub is not None and
                (not isfinite(self.usd_to_rub) or self.usd_to_rub <= 0))
        ):
            raise ValueError("invalid direct model route")
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("invalid direct model port")


@dataclass(frozen=True)
class ModelReply:
    text: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    cached_tokens: int | None
    cost_usd: float | None


CompletionBackend = Callable[[ModelRoute, str], ModelReply]
ApproveModelCall = Callable[[str, ModelRoute, str], bool]


def _token_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _litellm_complete(route: ModelRoute, prompt: str) -> ModelReply:
    key = environ.get(route.api_key_env)
    if not key:
        raise ModelRouteError("model_credential_missing")

    # This adapter owns the SDK in a dedicated process. Keep its metadata local.
    environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    import httpx
    import litellm
    from openai import OpenAI

    litellm.telemetry = False
    litellm.suppress_debug_info = True
    litellm.turn_off_message_logging = True
    litellm.set_verbose = False
    litellm.model_fallbacks = None
    with httpx.Client(follow_redirects=False, trust_env=False, timeout=route.timeout_seconds) as http:
        with OpenAI(
            api_key=key, base_url=route.api_base, http_client=http,
            timeout=route.timeout_seconds, max_retries=0,
        ) as client:
            response = litellm.completion(
                model=f"openai/{route.model}",
                api_base=route.api_base,
                api_key=key,
                client=client,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=route.max_tokens,
                timeout=route.timeout_seconds,
                num_retries=0,
                max_retries=0,
                fallbacks=[],
                caching=False,
                **{"no-log": True},
            )

    usage = getattr(response, "usage", None)
    details = getattr(usage, "prompt_tokens_details", None)
    return ModelReply(
        text=response.choices[0].message.content,
        model=response.model,
        tokens_in=getattr(usage, "prompt_tokens", None),
        tokens_out=getattr(usage, "completion_tokens", None),
        cached_tokens=getattr(details, "cached_tokens", None),
        cost_usd=response._hidden_params.get("response_cost"),
    )


@dataclass
class ModelRouter:
    """Resolve a role to one reviewed route, without implicit retries or fallback."""

    runtime: Mapping[str, Any]
    run_id: str
    profile_id: str
    telemetry: TelemetrySink
    approve: ApproveModelCall | None = None
    backend: CompletionBackend = _litellm_complete
    clock: Clock = field(default_factory=SystemClock)

    def route_for(self, role: str) -> ModelRoute:
        alias = self.runtime["models"].get(role)
        settings = self.runtime.get("model_routes", {}).get(alias)
        if role not in ROLES or settings is None:
            raise ModelRouteError("model_route_unavailable")
        try:
            return ModelRoute(route_id=alias, **settings)
        except (TypeError, ValueError):
            raise ModelRouteError("model_route_invalid") from None

    def complete(self, role: str, prompt: str) -> str:
        started = self.clock.now()
        route = None
        reply = None
        error_code = "model_request_failed"
        try:
            route = self.route_for(role)
            if not prompt or len(prompt) > MAX_PROMPT_CHARS:
                raise ModelRouteError("model_payload_out_of_bounds")
            if self.approve is None or self.approve(role, route, prompt) is not True:
                raise ModelRouteError("model_payload_denied")
            reply = self.backend(route, prompt)
            if reply.model not in (route.model, f"openai/{route.model}"):
                raise ModelRouteError("model_route_mismatch")
            if not isinstance(reply.text, str) or not reply.text.strip() or len(reply.text) > MAX_REPLY_CHARS:
                raise ModelRouteError("model_response_invalid")
            error_code = None
            return reply.text
        except ModelRouteError as error:
            code = str(error)
            error_code = code if code in ROUTE_ERRORS else "model_request_failed"
            raise ModelRouteError(error_code) from None
        except Exception:
            raise ModelRouteError(error_code) from None
        finally:
            self._emit(role, route, reply, started, error_code)

    def _emit(self, role, route, reply, started, error_code) -> None:
        call = {"role": role if role in ROLES else "unknown"}
        if route is not None:
            cost = None
            reported_cost = reply.cost_usd if reply else None
            if (
                type(reported_cost) in (float, int) and 0 <= reported_cost < float("inf")
                and route.usd_to_rub is not None
            ):
                candidate = reported_cost * route.usd_to_rub
                if isfinite(candidate) and candidate >= 0:
                    cost = candidate
            call.update(
                route=route.route_id, provider="openai-compatible", model=route.model,
                tokens_in=_token_count(reply.tokens_in) if reply else None,
                tokens_out=_token_count(reply.tokens_out) if reply else None,
                cached_tokens=_token_count(reply.cached_tokens) if reply else None,
                cost_rub=cost, batch=False,
            )
        event = build_event(
            run_id=self.run_id, profile_id=self.profile_id,
            component="model-router", operation_role="model_routing",
            started_at=started, finished_at=self.clock.now(),
            status="error" if error_code else "ok", error_code=error_code,
            payload={"model_call": call} if route else {"model_role": call["role"]},
        )
        event["event_id"] = f"evt-{uuid4().hex[:16]}"
        self.telemetry.emit(event)
