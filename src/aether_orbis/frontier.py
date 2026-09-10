"""Frontier construction from a Research Specification.

The frontier is derived exclusively from ``specification.scope``. This module
holds no selection criteria of its own: an unknown strategy is a specification
error, never a silent default (``research-specification-contract.md`` O-2).
"""

from __future__ import annotations

from typing import Any

from aether_orbis.errors import SpecificationError
from aether_orbis.model import FrontierItem

STRATEGIES = ("enumerate", "expand", "query")


def build_frontier(specification: dict[str, Any]) -> tuple[FrontierItem, ...]:
    """Return the ordered frontier declared by *specification*."""

    scope = specification.get("scope")
    if not isinstance(scope, dict):
        raise SpecificationError("specification.scope is required")

    strategy = scope.get("strategy")
    if strategy not in STRATEGIES:
        raise SpecificationError(
            f"scope.strategy must be one of {STRATEGIES}, got {strategy!r}"
        )

    frontier = scope.get("frontier")
    if not isinstance(frontier, dict):
        raise SpecificationError("scope.frontier is required")

    if strategy == "enumerate":
        return _enumerate_items(frontier)
    if strategy == "expand":
        return _expand_items(frontier)
    return _query_items(frontier)


def _require_list(frontier: dict[str, Any], key: str, strategy: str) -> list[str]:
    values = frontier.get(key)
    if not isinstance(values, list) or not values:
        raise SpecificationError(
            f"scope.frontier.{key} is required and must be non-empty for strategy "
            f"{strategy!r}"
        )
    return values


def _enumerate_items(frontier: dict[str, Any]) -> tuple[FrontierItem, ...]:
    return tuple(
        FrontierItem(strategy="enumerate", kind="item", value=value)
        for value in _require_list(frontier, "items", "enumerate")
    )


def _expand_items(frontier: dict[str, Any]) -> tuple[FrontierItem, ...]:
    hints = tuple(frontier.get("relation_hints") or ())
    return tuple(
        FrontierItem(strategy="expand", kind="seed", value=value, hints=hints)
        for value in _require_list(frontier, "seeds", "expand")
    )


def _query_items(frontier: dict[str, Any]) -> tuple[FrontierItem, ...]:
    source_types = _require_list(frontier, "source_types", "query")
    templates = _require_list(frontier, "query_templates", "query")
    return tuple(
        FrontierItem(
            strategy="query", kind="query", value=template, source_type=source_type
        )
        for source_type in source_types
        for template in templates
    )
