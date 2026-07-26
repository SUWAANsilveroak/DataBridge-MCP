"""Tests for the find_resources and search_rows MCP tools."""

import pytest

from local_data_mcp import server
from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead, TableSchema
from local_data_mcp.adapters.memory import InMemoryAdapter
from local_data_mcp.adapters.registry import AdapterRegistry
from local_data_mcp.errors import AdapterNotFoundError, UnsupportedCapabilityError
from local_data_mcp.server import find_resources, search_rows


class _TabularStub(DataSourceAdapter, SupportsTabularRead):
    def __init__(self, name, resources, rows):
        self._name = name
        self._resources = resources
        self._rows = rows

    @property
    def name(self) -> str:
        return self._name

    def list_resources(self) -> list[str]:
        return self._resources

    def get_schema(self, resource: str) -> TableSchema:
        return TableSchema(resource=resource, columns=[])

    def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
        return self._rows[:limit]


@pytest.fixture
def temp_registry(monkeypatch):
    registry = AdapterRegistry()
    monkeypatch.setattr(server, "registry", registry)
    return registry


ROWS = [
    {"Module": "Payroll", "Case": "OT calc"},
    {"Module": "Unions", "Case": "Fringe"},
    {"Module": "Payroll", "Case": "Holiday"},
]


# --- find_resources ---------------------------------------------------------


def test_find_resources_filters_by_name(temp_registry) -> None:
    temp_registry.register(
        _TabularStub("t", ["Overtime rules", "Holiday", "Sequential OT"], [])
    )
    assert find_resources("t", "overtime") == ["Overtime rules"]


def test_find_resources_unknown_source_raises(temp_registry) -> None:
    with pytest.raises(AdapterNotFoundError):
        find_resources("missing", "x")


# --- search_rows ------------------------------------------------------------


def test_search_rows_returns_matching_rows(temp_registry) -> None:
    temp_registry.register(_TabularStub("t", ["cases"], ROWS))
    assert search_rows("t", "cases", "payroll") == [
        {"Module": "Payroll", "Case": "OT calc"},
        {"Module": "Payroll", "Case": "Holiday"},
    ]


def test_search_rows_respects_match_limit(temp_registry) -> None:
    temp_registry.register(_TabularStub("t", ["cases"], ROWS))
    assert search_rows("t", "cases", "payroll", limit=1) == [
        {"Module": "Payroll", "Case": "OT calc"},
    ]


def test_search_rows_rejects_out_of_range_limit(temp_registry) -> None:
    temp_registry.register(_TabularStub("t", ["cases"], ROWS))
    with pytest.raises(ValueError):
        search_rows("t", "cases", "x", limit=0)


def test_search_rows_unknown_source_raises(temp_registry) -> None:
    with pytest.raises(AdapterNotFoundError):
        search_rows("missing", "cases", "x")


def test_search_rows_non_tabular_source_raises(temp_registry) -> None:
    temp_registry.register(InMemoryAdapter("demo", resources=["users"]))
    with pytest.raises(UnsupportedCapabilityError):
        search_rows("demo", "users", "x")
