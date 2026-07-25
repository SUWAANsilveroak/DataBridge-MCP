"""Domain-specific exceptions for the Universal Data MCP Server.

A small hierarchy rooted at ``LocalDataMCPError`` lets the rest of the code
catch *our* errors precisely (without also swallowing unrelated built-ins) and
attach structured context — like the list of sources that *do* exist — that the
MCP layer can turn into helpful, actionable messages for an LLM.
"""

from __future__ import annotations


class LocalDataMCPError(Exception):
    """Base class for every error this project raises deliberately."""


class AdapterNotFoundError(LocalDataMCPError):
    """Raised when a data source is requested by a name that isn't registered."""

    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = available
        available_text = ", ".join(available) if available else "none registered"
        super().__init__(
            f"No data source named {name!r}. Available sources: {available_text}."
        )


class DuplicateAdapterError(LocalDataMCPError):
    """Raised when two adapters try to register under the same name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"A data source named {name!r} is already registered.")


class GoogleAuthError(LocalDataMCPError):
    """Raised when Google credentials are missing, invalid, or cannot be refreshed."""
