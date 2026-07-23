"""A registry that holds data-source adapters and looks them up by name.

The MCP layer talks to the registry, never to concrete adapters. That single
seam is what makes the server "closed for modification": adding a new source
means registering a new adapter here, not editing the tools.
"""

from __future__ import annotations

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.errors import AdapterNotFoundError, DuplicateAdapterError


class AdapterRegistry:
    """An in-memory collection of adapters keyed by their unique name."""

    def __init__(self) -> None:
        self._adapters: dict[str, DataSourceAdapter] = {}

    def register(self, adapter: DataSourceAdapter) -> None:
        """Add an adapter. Reject a name that is already taken."""
        if adapter.name in self._adapters:
            raise DuplicateAdapterError(adapter.name)
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> DataSourceAdapter:
        """Return the adapter registered under ``name``, or raise a helpful error."""
        try:
            return self._adapters[name]
        except KeyError:
            raise AdapterNotFoundError(name, available=self.names()) from None

    def names(self) -> list[str]:
        """Return the registered source names, sorted for stable output."""
        return sorted(self._adapters)
