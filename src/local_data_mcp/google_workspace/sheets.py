"""Google Sheets data source adapter (read-only).

Exposes ONE spreadsheet: each tab is a resource, each tab's rows are data.

Testability: the adapter does NOT build its own Google connection. It receives
an already-built Sheets ``service`` object, so tests can inject a fake and
exercise the logic (header parsing, row padding, missing-tab errors) without any
network access. ``build_sheets_service`` builds the real one in production.
"""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import build

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead
from local_data_mcp.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


def build_sheets_service(credentials: Any) -> Any:
    """Build a Google Sheets API v4 service from OAuth credentials."""
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


class GoogleSheetsAdapter(DataSourceAdapter, SupportsTabularRead):
    """Reads the tabs and rows of a single Google Spreadsheet."""

    def __init__(self, name: str, spreadsheet_id: str, service: Any) -> None:
        self._name = name
        self._spreadsheet_id = spreadsheet_id
        self._service = service

    @property
    def name(self) -> str:
        return self._name

    def list_resources(self) -> list[str]:
        """Return the spreadsheet's tab titles."""
        metadata = (
            self._service.spreadsheets()
            .get(spreadsheetId=self._spreadsheet_id)
            .execute()
        )
        return [sheet["properties"]["title"] for sheet in metadata.get("sheets", [])]

    def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
        """Return up to ``limit`` rows of tab ``resource`` as header-keyed dicts."""
        self._require_resource(resource)

        # Single-quote the tab name so titles with spaces are valid A1 notation.
        response = (
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self._spreadsheet_id, range=f"'{resource}'")
            .execute()
        )
        values = response.get("values", [])
        if not values:
            return []

        header = values[0]
        data_rows = values[1 : 1 + limit]
        return [self._row_to_dict(header, row) for row in data_rows]

    def _require_resource(self, resource: str) -> None:
        available = self.list_resources()
        if resource not in available:
            raise ResourceNotFoundError(self._name, resource, available)

    @staticmethod
    def _row_to_dict(header: list[str], row: list[str]) -> dict[str, str]:
        # The Sheets API drops trailing empty cells, so a data row can be shorter
        # than the header. Pad it so every column keeps its place.
        padded = row + [""] * (len(header) - len(row))
        return {column: value for column, value in zip(header, padded)}
