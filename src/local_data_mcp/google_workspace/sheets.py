"""Google Sheets data source adapter (read-only).

Exposes ONE spreadsheet: each tab is a resource, each tab's rows are data.

Testability: the adapter does NOT build its own Google connection. It receives
an already-built Sheets ``service`` object, so tests can inject a fake and
exercise the logic (header parsing, normalization, error wrapping) without any
network access. ``build_sheets_service`` builds the real one in production.
"""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead, TableSchema
from local_data_mcp.errors import DataSourceError, ResourceNotFoundError

logger = logging.getLogger(__name__)


def normalize_headers(raw_headers: list[str]) -> list[str]:
    """Make spreadsheet headers safe and unique for use as dict keys.

    - trims surrounding whitespace (``"Notes "`` -> ``"Notes"``)
    - names blank headers by 1-based position (``""`` -> ``"column_3"``)
    - de-duplicates collisions with a numeric suffix (``"Notes"``, ``"Notes_2"``)

    The source sheet is never modified; this runs only on the values we read.
    """
    normalized: list[str] = []
    used: set[str] = set()
    for position, raw in enumerate(raw_headers, start=1):
        name = raw.strip() or f"column_{position}"
        candidate = name
        suffix = 2
        while candidate in used:
            candidate = f"{name}_{suffix}"
            suffix += 1
        used.add(candidate)
        normalized.append(candidate)
    return normalized


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
        metadata = self._execute(
            self._service.spreadsheets().get(spreadsheetId=self._spreadsheet_id)
        )
        return [sheet["properties"]["title"] for sheet in metadata.get("sheets", [])]

    def get_schema(self, resource: str) -> TableSchema:
        """Return the (normalized) column names of tab ``resource``."""
        values = self._fetch_tab(resource)
        columns = normalize_headers(values[0]) if values else []
        return TableSchema(resource=resource, columns=columns)

    def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
        """Return up to ``limit`` rows of tab ``resource`` as header-keyed dicts."""
        values = self._fetch_tab(resource)
        if not values:
            return []

        header = normalize_headers(values[0])
        return [self._row_to_dict(header, row) for row in values[1 : 1 + limit]]

    def _fetch_tab(self, resource: str) -> list[list[str]]:
        """Fetch all values of a tab, after checking the tab exists."""
        self._require_resource(resource)
        # Single-quote the tab name so titles with spaces are valid A1 notation.
        response = self._execute(
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self._spreadsheet_id, range=f"'{resource}'")
        )
        return response.get("values", [])

    def _require_resource(self, resource: str) -> None:
        available = self.list_resources()
        if resource not in available:
            raise ResourceNotFoundError(self._name, resource, available)

    def _execute(self, request: Any) -> Any:
        """Run a Google API request, translating HttpError into a clean error."""
        try:
            return request.execute()
        except HttpError as error:
            raise DataSourceError(self._describe_http_error(error)) from error

    def _describe_http_error(self, error: HttpError) -> str:
        status = getattr(error.resp, "status", None)
        if status == 404:
            return (
                f"Spreadsheet '{self._spreadsheet_id}' was not found. "
                "Check the configured Google Sheets ID."
            )
        if status == 403:
            return (
                f"Access to spreadsheet '{self._spreadsheet_id}' was denied. "
                "Make sure it is shared with your authorized Google account."
            )
        return f"Google Sheets API request failed (HTTP {status})."

    @staticmethod
    def _row_to_dict(header: list[str], row: list[str]) -> dict[str, str]:
        # The Sheets API drops trailing empty cells, so a data row can be shorter
        # than the header. Pad it so every column keeps its place.
        padded = row + [""] * (len(header) - len(row))
        return {column: value for column, value in zip(header, padded)}
