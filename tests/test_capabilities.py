"""Tests that the capability interface enforces its contract like the base ABC."""

import pytest

from local_data_mcp.adapters.capabilities import SupportsTabularRead, TableSchema


def test_cannot_instantiate_capability_directly() -> None:
    with pytest.raises(TypeError):
        SupportsTabularRead()  # type: ignore[abstract]


def test_subclass_missing_any_method_cannot_be_instantiated() -> None:
    class Incomplete(SupportsTabularRead):
        pass  # implements neither get_schema nor read_rows

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]


def test_subclass_missing_get_schema_cannot_be_instantiated() -> None:
    class OnlyReadRows(SupportsTabularRead):
        def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
            return []

        # deliberately does NOT implement get_schema

    with pytest.raises(TypeError):
        OnlyReadRows()  # type: ignore[abstract]


def test_complete_subclass_can_be_instantiated() -> None:
    class Complete(SupportsTabularRead):
        def get_schema(self, resource: str) -> TableSchema:
            return TableSchema(resource=resource, columns=[])

        def read_rows(self, resource: str, limit: int) -> list[dict[str, str]]:
            return []

    assert isinstance(Complete(), SupportsTabularRead)
