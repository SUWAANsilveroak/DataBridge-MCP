"""Tests for the in-memory reference adapter."""

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.memory import InMemoryAdapter


def test_reports_its_name() -> None:
    adapter = InMemoryAdapter("demo", resources=["users"])
    assert adapter.name == "demo"


def test_lists_its_resources() -> None:
    adapter = InMemoryAdapter("demo", resources=["users", "orders"])
    assert adapter.list_resources() == ["users", "orders"]


def test_is_a_data_source_adapter() -> None:
    assert isinstance(InMemoryAdapter("demo", resources=[]), DataSourceAdapter)


def test_state_is_isolated_from_mutation() -> None:
    """Mutating the input or the returned list must not corrupt internal state."""
    source = ["users"]
    adapter = InMemoryAdapter("demo", resources=source)

    source.append("injected")  # mutate the caller's original list
    returned = adapter.list_resources()
    returned.append("mutated")  # mutate the list the adapter handed back

    assert adapter.list_resources() == ["users"]
