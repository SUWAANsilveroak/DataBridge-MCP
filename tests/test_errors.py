"""Tests for the domain exception hierarchy.

The important behaviour here is that errors carry *helpful context* — the name
that was missing and the names that are available — so the message an LLM sees
is actionable.
"""

from local_data_mcp.errors import (
    AdapterNotFoundError,
    DuplicateAdapterError,
    LocalDataMCPError,
)


def test_adapter_not_found_lists_available_sources() -> None:
    error = AdapterNotFoundError("missing", available=["alpha", "beta"])

    assert error.name == "missing"
    assert error.available == ["alpha", "beta"]
    assert "alpha, beta" in str(error)
    assert isinstance(error, LocalDataMCPError)


def test_adapter_not_found_handles_empty_registry() -> None:
    error = AdapterNotFoundError("missing", available=[])
    assert "none registered" in str(error)


def test_duplicate_adapter_names_the_conflict() -> None:
    error = DuplicateAdapterError("demo")

    assert error.name == "demo"
    assert "demo" in str(error)
    assert isinstance(error, LocalDataMCPError)
