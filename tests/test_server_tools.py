"""Tests for the discovery MCP tools, exercised through the default registry.

These prove the end-to-end path: tool -> registry -> adapter -> result, plus
the error path for an unknown source.
"""

import pytest

from local_data_mcp.errors import AdapterNotFoundError
from local_data_mcp.server import list_resources, list_sources


def test_list_sources_includes_the_demo_source() -> None:
    assert "demo" in list_sources()


def test_list_resources_returns_the_demo_resources() -> None:
    assert list_resources("demo") == ["users", "orders"]


def test_list_resources_for_unknown_source_raises() -> None:
    with pytest.raises(AdapterNotFoundError):
        list_resources("does-not-exist")
