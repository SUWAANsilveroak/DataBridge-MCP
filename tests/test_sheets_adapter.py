"""Tests for the Google Sheets adapter.

A fake Sheets service stands in for the real Google client, so these tests
exercise our logic (tab listing, header-keyed rows, padding, missing tabs)
with no network access.
"""

import pytest

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead
from local_data_mcp.errors import ResourceNotFoundError
from local_data_mcp.google_workspace.sheets import GoogleSheetsAdapter


class _FakeValues:
    def __init__(self, data: dict[str, list[list[str]]]):
        self._data = data
        self._range = ""

    def get(self, spreadsheetId: str, range: str):  # noqa: A002 - matches API
        self._range = range
        return self

    def execute(self):
        tab = self._range.strip("'")
        return {"values": self._data.get(tab, [])}


class _FakeSpreadsheets:
    def __init__(self, tabs: list[str], data: dict[str, list[list[str]]]):
        self._tabs = tabs
        self._data = data

    def get(self, spreadsheetId: str):
        return self

    def execute(self):
        return {"sheets": [{"properties": {"title": t}} for t in self._tabs]}

    def values(self):
        return _FakeValues(self._data)


class FakeSheetsService:
    def __init__(self, tabs: list[str], data: dict[str, list[list[str]]]):
        self._tabs = tabs
        self._data = data

    def spreadsheets(self):
        return _FakeSpreadsheets(self._tabs, self._data)


TABS = ["users", "orders"]
DATA = {
    "users": [["name", "email"], ["Ann", "ann@x.com"], ["Bob", "bob@x.com"]],
    "orders": [["id", "total"], ["1", "10"]],
}


def _adapter(tabs=TABS, data=DATA) -> GoogleSheetsAdapter:
    return GoogleSheetsAdapter("gsheets", "sheet-id", FakeSheetsService(tabs, data))


def test_adapter_implements_base_and_capability() -> None:
    adapter = _adapter()
    assert isinstance(adapter, DataSourceAdapter)
    assert isinstance(adapter, SupportsTabularRead)


def test_list_resources_returns_tab_titles() -> None:
    assert _adapter().list_resources() == ["users", "orders"]


def test_read_rows_returns_header_keyed_dicts() -> None:
    assert _adapter().read_rows("users", limit=100) == [
        {"name": "Ann", "email": "ann@x.com"},
        {"name": "Bob", "email": "bob@x.com"},
    ]


def test_read_rows_respects_limit() -> None:
    assert _adapter().read_rows("users", limit=1) == [
        {"name": "Ann", "email": "ann@x.com"}
    ]


def test_read_rows_pads_ragged_rows() -> None:
    data = {"t": [["a", "b", "c"], ["1"]]}  # data row shorter than header
    adapter = GoogleSheetsAdapter("g", "id", FakeSheetsService(["t"], data))
    assert adapter.read_rows("t", limit=10) == [{"a": "1", "b": "", "c": ""}]


def test_read_rows_empty_tab_returns_empty_list() -> None:
    adapter = GoogleSheetsAdapter("g", "id", FakeSheetsService(["empty"], {"empty": []}))
    assert adapter.read_rows("empty", limit=10) == []


def test_read_rows_unknown_resource_raises() -> None:
    with pytest.raises(ResourceNotFoundError):
        _adapter().read_rows("does-not-exist", limit=10)
