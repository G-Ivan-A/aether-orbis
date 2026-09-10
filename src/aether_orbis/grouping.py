"""Phase 1 source grouping.

``relevance-gate-contract.md`` O-6 restricts Phase 1 grouping to an exact
canonical URL or an exact content hash. Near-duplicate and semantic merging is
deliberately absent: ``independence`` therefore means only "no exact duplicate
was detected".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256


def _group_id(canonical_url: str, content_hash: str) -> str:
    digest = sha256(f"{canonical_url}\n{content_hash}".encode("utf-8")).hexdigest()
    return f"group-{digest[:16]}"


@dataclass
class SourceGrouper:
    """Assigns a stable ``source_group_id`` to every evaluated material."""

    _by_url: dict[str, str] = field(default_factory=dict)
    _by_hash: dict[str, str] = field(default_factory=dict)

    def group_for(self, canonical_url: str, content_hash: str) -> str:
        """Return the group of a material, creating it on first sight.

        A material joins an existing group only when its canonical URL or its
        content hash is exactly equal to one already seen.
        """

        group = self._by_url.get(canonical_url) or self._by_hash.get(content_hash)
        if group is None:
            group = _group_id(canonical_url, content_hash)
        self._by_url.setdefault(canonical_url, group)
        self._by_hash.setdefault(content_hash, group)
        return group

    @property
    def groups(self) -> set[str]:
        """Return every group identifier assigned so far."""

        return set(self._by_url.values()) | set(self._by_hash.values())
