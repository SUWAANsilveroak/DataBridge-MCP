"""Tests for the adapter registry."""

import pytest

from local_data_mcp.adapters.memory import InMemoryAdapter
from local_data_mcp.adapters.registry import AdapterRegistry
from local_data_mcp.errors import AdapterNotFoundError, DuplicateAdapterError


def _adapter(name: str) -> InMemoryAdapter:
    return InMemoryAdapter(name, resources=[])


def test_register_then_get_returns_the_same_adapter() -> None:
    registry = AdapterRegistry()
    adapter = _adapter("demo")

    registry.register(adapter)

    assert registry.get("demo") is adapter


def test_get_unknown_source_raises_with_available_names() -> None:
    registry = AdapterRegistry()
    registry.register(_adapter("demo"))

    with pytest.raises(AdapterNotFoundError) as exc_info:
        registry.get("nope")

    assert "demo" in str(exc_info.value)


def test_duplicate_registration_is_rejected() -> None:
    registry = AdapterRegistry()
    registry.register(_adapter("demo"))

    with pytest.raises(DuplicateAdapterError):
        registry.register(_adapter("demo"))


def test_names_are_returned_sorted() -> None:
    registry = AdapterRegistry()
    registry.register(_adapter("zeta"))
    registry.register(_adapter("alpha"))

    assert registry.names() == ["alpha", "zeta"]
