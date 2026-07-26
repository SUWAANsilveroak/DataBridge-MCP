"""Tests that the capability interface enforces its contract like the base ABC."""

import pytest

from local_data_mcp.adapters.capabilities import SupportsTabularRead


def test_cannot_instantiate_capability_directly() -> None:
    with pytest.raises(TypeError):
        SupportsTabularRead()  # type: ignore[abstract]


def test_subclass_missing_read_rows_cannot_be_instantiated() -> None:
    class Incomplete(SupportsTabularRead):
        pass  # does not implement read_rows

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]
