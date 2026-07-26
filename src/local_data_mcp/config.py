"""Application configuration for the Universal Local Data MCP Server.

Settings are plain data, validated by Pydantic and loaded from environment
variables. Keeping every configurable knob in one typed model gives us a
single, discoverable place to see how the server can be tuned.

Environment variables are namespaced with the ``LOCAL_DATA_MCP_`` prefix so
they cannot collide with unrelated variables on the user's machine.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ENV_PREFIX = "LOCAL_DATA_MCP_"

# The severities Python's logging module understands. Using a Literal lets
# Pydantic reject anything else for free, with a clear error message.
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseModel):
    """Typed, validated configuration for the server."""

    log_level: LogLevel = Field(
        default="INFO",
        description="Minimum severity of log records that will be emitted.",
    )

    # Google Workspace auth. Both are paths, so switching from a personal to an
    # organization account later means pointing these at different files (or
    # replacing the files) — no code change required.
    google_credentials_file: str = Field(
        default="credentials.json",
        description="Path to the OAuth client secrets JSON from Google Cloud Console.",
    )
    google_token_file: str = Field(
        default="token.json",
        description="Path where the user's OAuth token is saved after authorizing.",
    )
    google_sheets_id: str | None = Field(
        default=None,
        description=(
            "ID of the Google Spreadsheet to expose (the string in its URL "
            "between /d/ and /edit). If unset, no Google Sheets source is "
            "registered."
        ),
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        """Accept a log level in any case, e.g. ``info`` becomes ``INFO``."""
        if isinstance(value, str):
            return value.upper()
        return value

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        """Build ``Settings`` from environment variables.

        Reads variables prefixed with ``LOCAL_DATA_MCP_``; anything missing
        falls back to the field default. ``environ`` can be passed explicitly
        so tests can supply a fake environment instead of mutating the real
        process environment.
        """
        env = os.environ if environ is None else environ

        values: dict[str, str] = {}
        log_level = env.get(f"{ENV_PREFIX}LOG_LEVEL")
        if log_level is not None:
            values["log_level"] = log_level

        credentials_file = env.get(f"{ENV_PREFIX}GOOGLE_CREDENTIALS_FILE")
        if credentials_file is not None:
            values["google_credentials_file"] = credentials_file

        token_file = env.get(f"{ENV_PREFIX}GOOGLE_TOKEN_FILE")
        if token_file is not None:
            values["google_token_file"] = token_file

        sheets_id = env.get(f"{ENV_PREFIX}GOOGLE_SHEETS_ID")
        if sheets_id is not None:
            values["google_sheets_id"] = sheets_id

        return cls(**values)
