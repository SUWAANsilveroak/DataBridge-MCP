"""Tests for the pure search-matching helpers (no registry, no network)."""

from local_data_mcp.search import (
    filter_names,
    filter_rows,
    name_matches,
    row_matches,
)


# --- names ------------------------------------------------------------------


def test_name_match_is_case_insensitive() -> None:
    assert name_matches("Overtime Rules", "overtime")
    assert name_matches("overtime rules", "OVERTIME")


def test_name_match_is_substring() -> None:
    assert name_matches("Prevailing wage OT 12477", "wage")
    assert not name_matches("Holiday", "overtime")


def test_filter_names_filters_preserving_order() -> None:
    names = ["Sequential OT", "Total cases", "Holiday"]
    assert filter_names(names, "ot") == ["Sequential OT", "Total cases"]


def test_empty_query_matches_all_names() -> None:
    assert filter_names(["a", "b"], "") == ["a", "b"]


def test_no_match_returns_empty_names() -> None:
    assert filter_names(["Holiday", "PTO"], "zzz") == []


# --- rows -------------------------------------------------------------------

ROWS = [
    {"Module": "Payroll", "Case": "OT calc"},
    {"Module": "Unions", "Case": "Fringe"},
    {"Module": "Payroll", "Case": "Holiday"},
]


def test_row_match_scans_all_cells_case_insensitively() -> None:
    assert row_matches({"a": "Hello", "b": "World"}, "world")
    assert not row_matches({"a": "Hello"}, "bye")


def test_filter_rows_returns_matching_rows() -> None:
    assert filter_rows(ROWS, "payroll") == [
        {"Module": "Payroll", "Case": "OT calc"},
        {"Module": "Payroll", "Case": "Holiday"},
    ]


def test_empty_query_matches_all_rows() -> None:
    assert filter_rows(ROWS, "") == ROWS
