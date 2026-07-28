"""Tests for the pre-import Python version guard (no dependencies, no network)."""

from local_data_mcp._runtime import (
    MINIMUM_PYTHON,
    find_newer_python,
    python_version_error,
)


def _which_from(available):
    """Build a fake ``shutil.which`` that only knows about ``available`` names."""
    return lambda name: f"/usr/bin/{name}" if name in available else None


def test_supported_version_returns_none() -> None:
    # The exact minimum and anything above it must pass (return None).
    assert python_version_error((3, 10, 0)) is None
    assert python_version_error((3, 12, 4)) is None
    assert python_version_error((4, 0, 0)) is None


def test_too_old_version_returns_message() -> None:
    message = python_version_error((3, 9, 6))
    assert message is not None
    # The message must name both what was found and what is required, so a user
    # can act on it without reading our source.
    assert "3.9" in message
    assert "3.10" in message


def test_message_reports_the_actual_found_version() -> None:
    # A different old version should be reflected verbatim in the message.
    assert "3.7" in python_version_error((3, 7, 0))


def test_minimum_python_is_3_10() -> None:
    # Pin the supported floor so a change is deliberate and visible.
    assert MINIMUM_PYTHON == (3, 10)


# --- find_newer_python ------------------------------------------------------


def test_finds_a_qualified_interpreter_at_or_above_minimum() -> None:
    which = _which_from({"python3.11"})
    assert find_newer_python(which) == "/usr/bin/python3.11"


def test_prefers_the_newest_available_interpreter() -> None:
    # Both present; the newer one must win.
    which = _which_from({"python3.10", "python3.12"})
    assert find_newer_python(which) == "/usr/bin/python3.12"


def test_ignores_interpreters_below_the_minimum() -> None:
    # python3.9 exists but is too old; nothing usable → None.
    which = _which_from({"python3.9", "python2.7"})
    assert find_newer_python(which) is None


def test_returns_none_when_no_python_found() -> None:
    assert find_newer_python(_which_from(set())) is None
