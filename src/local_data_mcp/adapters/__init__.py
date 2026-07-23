"""Data-source adapters and the registry that manages them.

Re-exported here so the rest of the app can import the public pieces from one
place: ``from local_data_mcp.adapters import AdapterRegistry, InMemoryAdapter``.
"""

from local_data_mcp.adapters.base import DataSourceAdapter
from local_data_mcp.adapters.memory import InMemoryAdapter
from local_data_mcp.adapters.registry import AdapterRegistry

__all__ = ["DataSourceAdapter", "InMemoryAdapter", "AdapterRegistry"]
