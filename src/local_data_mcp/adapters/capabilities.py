"""Capability interfaces: what a data source can *do*, beyond mere discovery.

The base ``DataSourceAdapter`` only promises discovery (``name`` +
``list_resources``). Reading is offered through *capability* interfaces that a
source opts into, so no source is ever forced to implement an operation it
cannot support — a Google Doc is not tabular, a spreadsheet is. This is the
Interface Segregation Principle.

A tool checks for a capability with ``isinstance(adapter, SupportsTabularRead)``
before using it, and returns a clear error if the source doesn't support it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class TableSchema(BaseModel):
    """The column structure of a tabular resource.

    A typed model (rather than a bare list) so MCP clients receive a precise,
    self-describing output schema.
    """

    resource: str
    columns: list[str]


class SupportsTabularRead(ABC):
    """A source whose resources are tables of rows (spreadsheets, DB tables)."""

    @abstractmethod
    def get_schema(self, resource: str) -> TableSchema:
        """Return the column schema of ``resource`` (its normalized headers)."""

    @abstractmethod
    def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
        """Return up to ``limit`` rows of ``resource`` as a list of dicts.

        Each row is keyed by column name, taken from the resource's header row,
        so the result is self-describing for an LLM.
        """
