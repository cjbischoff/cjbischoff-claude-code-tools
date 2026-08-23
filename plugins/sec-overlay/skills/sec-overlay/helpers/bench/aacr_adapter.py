"""Map rows of the ``Alibaba-Aone/aacr-bench`` code-review dataset to corpus entries.

The dataset is an external code-review benchmark, not security ground truth. Its rows
enter the corpus tagged ``source="aacr"`` so ``tally`` keeps them out of the
real-confirmed headline (see ``bench/README.md`` for the row schema and its
unverified-distribution caveat). This adapter never touches harness findings.
"""

from __future__ import annotations

import re

from .corpus import CorpusEntry

_SLUG = re.compile(r"[^a-z0-9]+")
# ponytail: substring match — extend if the dataset labels security another way.
_SECURITY_SIGNALS = ("security", "vulnerab")


def _cls(category: str) -> str:
    """Kebab-case a dataset ``category`` for use as an attack-class key."""
    return _SLUG.sub("-", category.strip().lower()).strip("-") or "review-comment"


def _source(category: str) -> str:
    """Tag security-category rows so ``tally`` emits a distinct ``aacr-security`` slice.

    M3d found no distinct security category in the dataset preview; the full
    distribution is unverified, so this matches any category whose text signals
    security (``security`` / ``vulnerab``). Non-security rows stay ``aacr``.
    """
    low = category.lower()
    return "aacr-security" if any(s in low for s in _SECURITY_SIGNALS) else "aacr"


def aacr_entries(rows: list[dict]) -> list[CorpusEntry]:
    """Convert AACR dataset rows into labelled corpus entries.

    Args:
        rows: Dataset rows (see ``bench/README.md`` for the column schema). Each row
            needs ``pr_url``, ``pr_source_commit``, ``path``, ``from_line``, ``note``,
            ``category``, and ``label``.

    Returns:
        One :class:`CorpusEntry` per row, tagged ``source="aacr"`` (or
        ``"aacr-security"`` for a security-category row). ``label`` truthy
        maps to a positive (a valid review comment the reviewer should raise), falsy
        to a negative. ``finding_id`` is ``aacr-<index>`` for stable uniqueness.

    Example:
        >>> aacr_entries([{"pr_url": "https://github.com/o/r/pull/1",
        ...   "pr_source_commit": "a" * 40, "path": "a.py", "from_line": 3,
        ...   "note": "bug", "category": "Code Defect", "label": 1}])[0].source
        'aacr'
    """
    entries: list[CorpusEntry] = []
    for i, row in enumerate(rows):
        entries.append(CorpusEntry(
            finding_id=f"aacr-{i}",
            kind="positive" if row.get("label") else "negative",
            source=_source(str(row.get("category", ""))),
            cls=_cls(str(row.get("category", ""))),
            repo_url=str(row.get("pr_url", "")),
            commit=str(row.get("pr_source_commit", "")),
            file=str(row.get("path", "")),
            line=int(row.get("from_line", 0) or 0),
            description=str(row.get("note", "")),
        ))
    return entries
