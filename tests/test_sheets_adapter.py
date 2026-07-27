"""Tests for the Google Sheets adapter.

A fake Sheets service stands in for the real Google client, injected via a
service *factory* (the adapter builds lazily). So these tests exercise our logic
(tab listing, header normalization, row padding, missing tabs, error wrapping,
lazy build) with no network access.
"""

import pytest

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead, TableSchema
from local_data_mcp.errors import DataSourceError, ResourceNotFoundError
from local_data_mcp.google_workspace.sheets import (
    GoogleSheetsAdapter,
    normalize_headers,
)
from googleapiclient.errors import HttpError


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


class _FakeResp:
    def __init__(self, status: int):
        self.status = status
        self.reason = "error"


def _http_error(status: int) -> HttpError:
    return HttpError(_FakeResp(status), b"{}", uri="http://example")


class _RaisingService:
    """A service whose every call raises an HttpError with a given status."""

    def __init__(self, status: int):
        self._status = status

    def spreadsheets(self):
        return self

    def get(self, spreadsheetId: str):
        return self

    def values(self):
        return self

    def execute(self):
        raise _http_error(self._status)


TABS = ["users", "orders"]
DATA = {
    "users": [["name", "email"], ["Ann", "ann@x.com"], ["Bob", "bob@x.com"]],
    "orders": [["id", "total"], ["1", "10"]],
}


def _adapter(tabs=TABS, data=DATA) -> GoogleSheetsAdapter:
    service = FakeSheetsService(tabs, data)
    return GoogleSheetsAdapter("gsheets", "sheet-id", lambda: service)


def _raising_adapter(status: int) -> GoogleSheetsAdapter:
    return GoogleSheetsAdapter("g", "id", lambda: _RaisingService(status))


# --- normalize_headers (pure logic) -----------------------------------------


def test_normalize_trims_whitespace() -> None:
    assert normalize_headers(["  a  ", "b "]) == ["a", "b"]


def test_normalize_names_blank_headers_by_position() -> None:
    assert normalize_headers(["a", "", "  ", "d"]) == ["a", "column_2", "column_3", "d"]


def test_normalize_dedupes_collisions() -> None:
    assert normalize_headers(["x", "x", "x"]) == ["x", "x_2", "x_3"]


# --- lazy service build -----------------------------------------------------


def test_service_is_built_lazily_and_cached() -> None:
    calls = {"n": 0}
    service = FakeSheetsService(TABS, DATA)

    def factory():
        calls["n"] += 1
        return service

    adapter = GoogleSheetsAdapter("g", "id", factory)
    assert calls["n"] == 0  # not built at construction

    adapter.list_resources()
    adapter.list_resources()
    assert calls["n"] == 1  # built once on first use, then cached


# --- discovery / capability -------------------------------------------------


def test_adapter_implements_base_and_capability() -> None:
    adapter = _adapter()
    assert isinstance(adapter, DataSourceAdapter)
    assert isinstance(adapter, SupportsTabularRead)


def test_list_resources_returns_tab_titles() -> None:
    assert _adapter().list_resources() == ["users", "orders"]


# --- get_schema -------------------------------------------------------------


def test_get_schema_returns_table_schema() -> None:
    schema = _adapter().get_schema("users")
    assert isinstance(schema, TableSchema)
    assert schema.resource == "users"
    assert schema.columns == ["name", "email"]


def test_get_schema_normalizes_messy_headers() -> None:
    data = {"t": [["Automation ", "", "Rules", "Rules"]]}
    adapter = GoogleSheetsAdapter("g", "id", lambda: FakeSheetsService(["t"], data))
    assert adapter.get_schema("t").columns == [
        "Automation",
        "column_2",
        "Rules",
        "Rules_2",
    ]


# --- read_rows --------------------------------------------------------------


def test_read_rows_returns_header_keyed_dicts() -> None:
    assert _adapter().read_rows("users", limit=100) == [
        {"name": "Ann", "email": "ann@x.com"},
        {"name": "Bob", "email": "bob@x.com"},
    ]


def test_read_rows_uses_normalized_headers() -> None:
    data = {"t": [["Name ", ""], ["Ann", "x"]]}
    adapter = GoogleSheetsAdapter("g", "id", lambda: FakeSheetsService(["t"], data))
    assert adapter.read_rows("t", limit=10) == [{"Name": "Ann", "column_2": "x"}]


def test_read_rows_respects_limit() -> None:
    assert _adapter().read_rows("users", limit=1) == [
        {"name": "Ann", "email": "ann@x.com"}
    ]


def test_read_rows_pads_ragged_rows() -> None:
    data = {"t": [["a", "b", "c"], ["1"]]}  # data row shorter than header
    adapter = GoogleSheetsAdapter("g", "id", lambda: FakeSheetsService(["t"], data))
    assert adapter.read_rows("t", limit=10) == [{"a": "1", "b": "", "c": ""}]


def test_read_rows_empty_tab_returns_empty_list() -> None:
    adapter = GoogleSheetsAdapter(
        "g", "id", lambda: FakeSheetsService(["empty"], {"empty": []})
    )
    assert adapter.read_rows("empty", limit=10) == []


def test_read_rows_unknown_resource_raises() -> None:
    with pytest.raises(ResourceNotFoundError):
        _adapter().read_rows("does-not-exist", limit=10)


# --- error wrapping ---------------------------------------------------------


def test_http_404_becomes_data_source_error() -> None:
    with pytest.raises(DataSourceError, match="not found"):
        _raising_adapter(404).list_resources()


def test_http_403_becomes_data_source_error() -> None:
    with pytest.raises(DataSourceError, match="denied"):
        _raising_adapter(403).list_resources()
