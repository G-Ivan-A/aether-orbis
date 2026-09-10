"""Acquisition core of Aether Orbis (Phase 1, P1-B).

The package executes the contracts accepted in P1-A: it builds a frontier from a
Research Specification, ingests and normalizes material, extracts evidence-backed
knowledge, evaluates and qualifies it and preserves the result.

External systems (network, browsers, model providers, stores) are reached only
through the ports declared in :mod:`aether_orbis.ports`, so the whole core runs
offline in tests.
"""

from aether_orbis.errors import (
    AcquisitionError,
    MalformedSourceError,
    SpecificationError,
    UnsupportedPreservationError,
)

__all__ = [
    "AcquisitionError",
    "MalformedSourceError",
    "SpecificationError",
    "UnsupportedPreservationError",
]
