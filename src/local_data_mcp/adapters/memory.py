"""An in-memory reference adapter.

Its job is not to be useful in production but to *prove the contract*: it is
the simplest possible thing that satisfies ``DataSourceAdapter``, which lets us
wire up and test the registry and the MCP tools without any real data source.
It also doubles as a copy-me template for future real adapters.
"""

from __future__ import annotations

from collections.abc import Iterable

from local_data_mcp.adapters.base import DataSourceAdapter


class InMemoryAdapter(DataSourceAdapter):
    """A data source whose resources are just names held in memory."""

    def __init__(self, name: str, resources: Iterable[str]) -> None:
        self._name = name
        # Copy into a list so later mutation of the caller's iterable cannot
        # change our internal state after construction.
        self._resources = list(resources)

    @property
    def name(self) -> str:
        return self._name

    def list_resources(self) -> list[str]:
        # Return a copy so callers cannot mutate our internal list.
        return list(self._resources)
