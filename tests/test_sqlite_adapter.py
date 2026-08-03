"""Tests for the read-only SQLite adapter (uses a real temp database, no mocks).

We build an actual SQLite file per test so we exercise the real driver — the
point of this adapter is its interaction with SQLite (read-only mode, table
discovery, NULL handling), which a fake connection wouldn't prove.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead
from local_data_mcp.adapters.sqlite import SQLiteAdapter
from local_data_mcp.errors import DataSourceError, ResourceNotFoundError


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE employees (id INTEGER, name TEXT, note TEXT);
        INSERT INTO employees VALUES (1, 'Ann', 'lead');
        INSERT INTO employees VALUES (2, 'Ben', NULL);
        CREATE TABLE empty_table (a TEXT, b TEXT);
        CREATE VIEW recent AS SELECT id, name FROM employees;
        """
    )
    connection.commit()
    connection.close()
    return path


@pytest.fixture
def adapter(db_path: Path) -> SQLiteAdapter:
    return SQLiteAdapter("sqlite", str(db_path))


def test_is_a_tabular_adapter(adapter: SQLiteAdapter) -> None:
    # It must satisfy both the base contract and the tabular capability, so the
    # existing read/schema/search tools work on it with no changes.
    assert isinstance(adapter, DataSourceAdapter)
    assert isinstance(adapter, SupportsTabularRead)


def test_lists_tables_and_views_excluding_internal(adapter: SQLiteAdapter) -> None:
    # Alphabetical ('employees' < 'empty_table'); the view is included and
    # SQLite's internal sqlite_* tables are not.
    assert adapter.list_resources() == ["employees", "empty_table", "recent"]


def test_get_schema_returns_columns(adapter: SQLiteAdapter) -> None:
    schema = adapter.get_schema("employees")
    assert schema.resource == "employees"
    assert schema.columns == ["id", "name", "note"]


def test_read_rows_returns_column_keyed_dicts_and_maps_null(adapter: SQLiteAdapter) -> None:
    rows = adapter.read_rows("employees", limit=10)
    assert rows == [
        {"id": "1", "name": "Ann", "note": "lead"},
        {"id": "2", "name": "Ben", "note": ""},  # NULL -> ""
    ]


def test_read_rows_respects_limit(adapter: SQLiteAdapter) -> None:
    assert len(adapter.read_rows("employees", limit=1)) == 1


def test_empty_table_has_schema_but_no_rows(adapter: SQLiteAdapter) -> None:
    assert adapter.read_rows("empty_table", limit=10) == []
    assert adapter.get_schema("empty_table").columns == ["a", "b"]


def test_can_read_a_view(adapter: SQLiteAdapter) -> None:
    assert adapter.read_rows("recent", limit=10) == [
        {"id": "1", "name": "Ann"},
        {"id": "2", "name": "Ben"},
    ]


def test_unknown_table_raises_resource_not_found(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ResourceNotFoundError):
        adapter.read_rows("does_not_exist", limit=10)
    with pytest.raises(ResourceNotFoundError):
        adapter.get_schema("does_not_exist")


def test_missing_database_file_raises_data_source_error(tmp_path: Path) -> None:
    adapter = SQLiteAdapter("sqlite", str(tmp_path / "nope.db"))
    with pytest.raises(DataSourceError):
        adapter.list_resources()


def test_connection_is_read_only(adapter: SQLiteAdapter) -> None:
    # The security guarantee: a write is rejected at the driver level, so no tool
    # (or bug) could ever mutate the source database.
    connection = adapter._connect()
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM employees")
    finally:
        connection.close()
