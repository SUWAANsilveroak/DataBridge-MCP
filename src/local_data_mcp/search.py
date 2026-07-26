"""Pure matching helpers for the search tools.

Kept free of any registry, adapter, or Google dependency so the matching logic
is trivially unit-testable — and so ranking / fuzzy matching can be added here
later without touching the tools.

Matching is deliberately simple: case-insensitive substring. The tools are
predictable primitives; the *intelligence* (synonyms, re-querying) lives in the
LLM that calls them.
"""

from __future__ import annotations


def _needle(query: str) -> str:
    return query.strip().lower()


def name_matches(name: str, query: str) -> bool:
    """True if ``query`` appears in ``name`` (case-insensitive)."""
    return _needle(query) in name.lower()


def filter_names(names: list[str], query: str) -> list[str]:
    """Return the names matching ``query``, preserving order."""
    return [name for name in names if name_matches(name, query)]


def row_matches(row: dict[str, str], query: str) -> bool:
    """True if any cell value in ``row`` contains ``query`` (case-insensitive)."""
    needle = _needle(query)
    return any(needle in str(value).lower() for value in row.values())


def filter_rows(rows: list[dict[str, str]], query: str) -> list[dict[str, str]]:
    """Return the rows with any cell matching ``query``, preserving order."""
    return [row for row in rows if row_matches(row, query)]
