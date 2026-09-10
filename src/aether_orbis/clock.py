"""Deterministic time source for the acquisition core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable


def to_rfc3339(moment: datetime) -> str:
    """Return *moment* as an RFC 3339 UTC timestamp."""

    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@runtime_checkable
class Clock(Protocol):
    """Provides the current time to the pipeline."""

    def now(self) -> datetime:
        """Return the current instant."""


class SystemClock:
    """Wall-clock time in UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass
class StepClock:
    """Clock that advances by a fixed step on every call.

    Used by tests and local runs so that identifiers and telemetry latencies are
    reproducible without freezing real time.
    """

    start: datetime = field(
        default_factory=lambda: datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    )
    step: timedelta = timedelta(milliseconds=250)
    _ticks: int = 0

    def now(self) -> datetime:
        moment = self.start + self.step * self._ticks
        self._ticks += 1
        return moment
