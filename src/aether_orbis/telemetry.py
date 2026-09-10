"""Telemetry event construction (``telemetry-contract.md``)."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any

from aether_orbis.clock import to_rfc3339


def build_event(
    *,
    run_id: str,
    profile_id: str,
    component: str,
    operation_role: str,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    error_code: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one telemetry event document."""

    started = to_rfc3339(started_at)
    finished = to_rfc3339(finished_at)
    latency_ms = max(int((finished_at - started_at).total_seconds() * 1000), 0)
    digest = sha256(
        f"{run_id}\n{component}\n{operation_role}\n{started}\n{finished}".encode("utf-8")
    ).hexdigest()
    event: dict[str, Any] = {
        "schema_version": "1.0",
        "event_id": f"evt-{digest[:16]}",
        "run_id": run_id,
        "profile_id": profile_id,
        "component": component,
        "operation_role": operation_role,
        "started_at": started,
        "finished_at": finished,
        "latency_ms": latency_ms,
        "status": status,
    }
    if error_code is not None:
        event["error_code"] = error_code
    if payload:
        event.update(payload)
    return event
