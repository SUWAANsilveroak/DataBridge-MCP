"""Local SQLite data source adapter (read-only).

Exposes one SQLite database file: each table (and view) is a resource, and its
rows are the data. Because a database is exactly where "don't give the model raw
access" matters most, reads are strictly read-only and structured — the LLM
never runs arbitrary SQL, and destructive statements are impossible:

- the connection is opened in **read-only** mode (``mode=ro`` URI), so even a
  write attempt fails at the driver level;
- table names cannot be SQL-parameterized, so each requested name is validated
  against the database's real table list *before* use (an allowlist), then
  quoted as an identifier — closing the injection door;
- row counts are bounded by a parameterized ``LIMIT``.

A fresh read-only connection is opened per operation (local SQLite opens are
cheap), which also sidesteps SQLite's cross-thread connection restrictions.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from pathlib import Path

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead, TableSchema
from local_data_mcp.errors import DataSourceError, ResourceNotFoundError

logger = logging.getLogger(__name__)

# Tables/views the user cares about — never SQLite's internal bookkeeping ones.
_LIST_TABLES_SQL = (
    "SELECT name FROM sqlite_master "
    "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' "
    "ORDER BY name"
)


class SQLiteAdapter(DataSourceAdapter, SupportsTabularRead):
    """Reads the tables/views and rows of a single local SQLite database."""

    def __init__(self, name: str, database_path: str) -> None:
        self._name = name
        self._database_path = database_path

    @property
    def name(self) -> str:
        return self._name

    def list_resources(self) -> list[str]:
        """Return the database's table and view names (excluding internal ones)."""
        with closing(self._connect()) as connection:
            return self._table_names(connection)

    def get_schema(self, resource: str) -> TableSchema:
        """Return the column names of table/view ``resource``."""
        with closing(self._connect()) as connection:
            self._require_resource(connection, resource)
            columns = self._columns(connection, resource)
        return TableSchema(resource=resource, columns=columns)

    def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
        """Return up to ``limit`` rows of ``resource`` as column-keyed dicts."""
        with closing(self._connect()) as connection:
            self._require_resource(connection, resource)
            columns = self._columns(connection, resource)
            # `resource` is validated against the real table list above, so it is
            # safe to quote and inline here (identifiers cannot be parameterized).
            # The LIMIT value IS parameterized.
            quoted = self._quote_identifier(resource)
            rows = connection.execute(
                f"SELECT * FROM {quoted} LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(columns, row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        """Open a fresh READ-ONLY connection to the database file.

        The ``mode=ro`` URI makes the driver reject any write and refuse to
        create a missing file, so we check existence first for a clear message.
        """
        path = Path(self._database_path)
        if not path.exists():
            raise DataSourceError(
                f"SQLite database not found at '{self._database_path}'. "
                "Check the configured database path."
            )
        uri = f"{path.resolve().as_uri()}?mode=ro"
        try:
            return sqlite3.connect(uri, uri=True)
        except sqlite3.Error as error:
            raise DataSourceError(
                f"Could not open SQLite database '{self._database_path}': {error}"
            ) from error

    def _require_resource(self, connection: sqlite3.Connection, resource: str) -> None:
        available = self._table_names(connection)
        if resource not in available:
            raise ResourceNotFoundError(self._name, resource, available)

    @staticmethod
    def _table_names(connection: sqlite3.Connection) -> list[str]:
        return [row[0] for row in connection.execute(_LIST_TABLES_SQL).fetchall()]

    @classmethod
    def _columns(cls, connection: sqlite3.Connection, resource: str) -> list[str]:
        quoted = cls._quote_identifier(resource)
        # PRAGMA table_info returns one row per column; index 1 is the name.
        info = connection.execute(f"PRAGMA table_info({quoted})").fetchall()
        return [row[1] for row in info]

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """Quote a validated SQL identifier (double quotes, doubling internal ones)."""
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    @staticmethod
    def _row_to_dict(columns: list[str], row: tuple) -> dict[str, str]:
        # Honour the dict[str, str] contract: stringify every value, mapping SQL
        # NULL to an empty string (same "everything is text" shape as Sheets).
        return {
            column: ("" if value is None else str(value))
            for column, value in zip(columns, row)
        }
