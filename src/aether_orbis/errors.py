"""Errors raised by the acquisition core."""

from __future__ import annotations


class AcquisitionError(Exception):
    """Base class for every acquisition core failure."""


class SpecificationError(AcquisitionError):
    """The Research Specification does not authorize the requested behaviour.

    Raised instead of silently substituting a default value, as required by
    ``research-specification-contract.md`` O-1 and ``relevance-gate-contract.md``
    escalation rule 1.
    """


class MalformedSourceError(AcquisitionError):
    """Acquired material cannot be normalized into a contractual identity."""


class UnsupportedPreservationError(AcquisitionError):
    """The Preservation Policy is valid in general but not executable in Phase 1."""
