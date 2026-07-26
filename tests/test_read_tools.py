"""Tests for the read_rows and get_schema MCP tools.

We swap the server's global registry for a controlled one (dependency injection
via monkeypatch) so we can register exactly the sources each case needs.
"""

import pytest

from local_data_mcp import server
from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead, TableSchema
from local_data_mcp.adapters.memory import InMemoryAdapter
from local_data_mcp.adapters.registry import AdapterRegistry
from local_data_mcp.errors import AdapterNotFoundError, UnsupportedCapabilityError
from local_data_mcp.server import get_schema, read_rows


class _TabularStub(DataSourceAdapter, SupportsTabularRead):
    """A minimal tabular source, so tool tests don't depend on Google Sheets."""

    def __init__(self, name: str, rows: list[dict[str, str]]):
        self._name = name
        self._rows = rows

    @property
    def name(self) -> str:
        return self._name

    def list_resources(self) -> list[str]:
        return ["t"]

    def get_schema(self, resource: str) -> TableSchema:
        return TableSchema(resource=resource, columns=["a"])

    def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
        return self._rows[:limit]


@pytest.fixture
def temp_registry(monkeypatch):
    registry = AdapterRegistry()
    monkeypatch.setattr(server, "registry", registry)
    return registry


# --- read_rows --------------------------------------------------------------


def test_read_rows_happy_path(temp_registry) -> None:
    temp_registry.register(_TabularStub("t", [{"a": "1"}, {"a": "2"}]))
    assert read_rows("t", "t", limit=100) == [{"a": "1"}, {"a": "2"}]


def test_read_rows_respects_limit(temp_registry) -> None:
    temp_registry.register(_TabularStub("t", [{"a": "1"}, {"a": "2"}]))
    assert read_rows("t", "t", limit=1) == [{"a": "1"}]


def test_read_rows_rejects_out_of_range_limit(temp_registry) -> None:
    temp_registry.register(_TabularStub("t", []))
    with pytest.raises(ValueError):
        read_rows("t", "t", limit=0)
    with pytest.raises(ValueError):
        read_rows("t", "t", limit=99999)


def test_read_rows_unknown_source_raises(temp_registry) -> None:
    with pytest.raises(AdapterNotFoundError):
        read_rows("missing", "t", limit=10)


def test_read_rows_non_tabular_source_raises(temp_registry) -> None:
    temp_registry.register(InMemoryAdapter("demo", resources=["users"]))
    with pytest.raises(UnsupportedCapabilityError):
        read_rows("demo", "users", limit=10)


# --- get_schema -------------------------------------------------------------


def test_get_schema_happy_path(temp_registry) -> None:
    temp_registry.register(_TabularStub("t", []))
    schema = get_schema("t", "t")
    assert schema.resource == "t"
    assert schema.columns == ["a"]


def test_get_schema_non_tabular_source_raises(temp_registry) -> None:
    temp_registry.register(InMemoryAdapter("demo", resources=["users"]))
    with pytest.raises(UnsupportedCapabilityError):
        get_schema("demo", "users")
