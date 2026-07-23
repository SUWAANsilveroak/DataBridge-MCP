"""Tests that the abstract base class actually enforces its contract.

This is the payoff of choosing an ABC over a plain class or a Protocol: an
incomplete adapter fails loudly at construction time, not later in production.
"""

import pytest

from local_data_mcp.adapters.base import DataSourceAdapter


def test_cannot_instantiate_the_abstract_base() -> None:
    with pytest.raises(TypeError):
        DataSourceAdapter()  # type: ignore[abstract]


def test_subclass_missing_a_method_cannot_be_instantiated() -> None:
    class MissingListResources(DataSourceAdapter):
        @property
        def name(self) -> str:
            return "incomplete"

        # Deliberately does NOT implement list_resources().

    with pytest.raises(TypeError):
        MissingListResources()  # type: ignore[abstract]


def test_complete_subclass_can_be_instantiated() -> None:
    class Complete(DataSourceAdapter):
        @property
        def name(self) -> str:
            return "complete"

        def list_resources(self) -> list[str]:
            return []

    adapter = Complete()
    assert adapter.name == "complete"
