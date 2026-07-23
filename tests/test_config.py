"""Tests for the Settings configuration model.

We pass a fake ``environ`` dict into ``Settings.from_env`` so the tests never
touch the real process environment and stay independent of each other.
"""

import pytest
from pydantic import ValidationError

from local_data_mcp.config import ENV_PREFIX, Settings

LOG_LEVEL_ENV = f"{ENV_PREFIX}LOG_LEVEL"


def test_defaults_when_env_is_empty() -> None:
    """With nothing set, the log level falls back to INFO."""
    settings = Settings.from_env(environ={})
    assert settings.log_level == "INFO"


def test_reads_log_level_from_env() -> None:
    """An explicit env var overrides the default."""
    settings = Settings.from_env(environ={LOG_LEVEL_ENV: "DEBUG"})
    assert settings.log_level == "DEBUG"


def test_log_level_is_case_insensitive() -> None:
    """Lower-case levels are normalised so users don't have to shout."""
    settings = Settings.from_env(environ={LOG_LEVEL_ENV: "debug"})
    assert settings.log_level == "DEBUG"


def test_invalid_log_level_is_rejected() -> None:
    """An unknown level fails loudly instead of silently defaulting."""
    with pytest.raises(ValidationError):
        Settings.from_env(environ={LOG_LEVEL_ENV: "LOUD"})
