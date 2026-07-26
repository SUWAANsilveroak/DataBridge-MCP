"""MCP server for the Universal Local Data project.

This module has one job: build the MCP application, register the tools the
server exposes to clients, and run it over the stdio transport.

Why stdio? Local MCP clients such as Claude Desktop launch the server as a
subprocess and communicate over standard input/output. Nothing opens a network
port, which keeps a "local data" server genuinely local.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from local_data_mcp import __version__
from local_data_mcp.adapters import AdapterRegistry, InMemoryAdapter
from local_data_mcp.adapters.capabilities import SupportsTabularRead
from local_data_mcp.config import Settings
from local_data_mcp.errors import (
    AdapterNotFoundError,
    GoogleAuthError,
    UnsupportedCapabilityError,
)
from local_data_mcp.google_workspace.auth import load_credentials
from local_data_mcp.google_workspace.sheets import (
    GoogleSheetsAdapter,
    build_sheets_service,
)
from local_data_mcp.logging_config import configure_logging

logger = logging.getLogger(__name__)

# The name the client displays for this server. Kept as a constant so the
# server and its tests agree on a single value.
SERVER_NAME = "universal-local-data-mcp"

# Row-read limits. Bounding the count stops an LLM from asking for a huge sheet
# and hanging the server (and blowing up its own context).
DEFAULT_ROW_LIMIT = 100
MAX_ROW_LIMIT = 1000

# The application object. Tools are registered onto it via the @mcp.tool()
# decorator below.
mcp = FastMCP(SERVER_NAME)


@mcp.tool()
def server_info() -> dict[str, str]:
    """Report basic information about this MCP server.

    Acts as a lightweight health check: a client can call this to confirm the
    server is alive and to discover its name and version. Takes no input, so
    there is nothing to validate yet — input validation arrives with the first
    tool that accepts arguments.
    """
    return {
        "name": SERVER_NAME,
        "version": __version__,
        "status": "ok",
    }


def build_default_registry() -> AdapterRegistry:
    """Create the registry pre-populated with the sources this server exposes.

    For now that is a single in-memory demo source, so the discovery tools are
    demonstrable end-to-end. Real adapters (Google Sheets/Docs, databases) will
    register here in later features — the tools below never change.
    """
    registry = AdapterRegistry()
    registry.register(InMemoryAdapter("demo", resources=["users", "orders"]))
    return registry


# The data sources this server exposes. Built once when the module is imported.
registry = build_default_registry()


@mcp.tool()
def list_sources() -> list[str]:
    """List the names of the data sources this server exposes."""
    logger.info("tool=list_sources")
    return registry.names()


@mcp.tool()
def list_resources(source: str) -> list[str]:
    """List the resources (tables, sheets, documents) in a given data source.

    Args:
        source: a data source name, as returned by ``list_sources``.
    """
    logger.info("tool=list_resources source=%s", source)
    try:
        adapter = registry.get(source)
    except AdapterNotFoundError as error:
        logger.warning("list_resources failed: %s", error)
        raise
    return adapter.list_resources()


@mcp.tool()
def read_rows(
    source: str, resource: str, limit: int = DEFAULT_ROW_LIMIT
) -> list[dict[str, str]]:
    """Read rows from a tabular resource (e.g. a spreadsheet tab).

    Args:
        source: a data source name, as returned by ``list_sources``.
        resource: a resource within that source, as returned by ``list_resources``.
        limit: maximum number of rows to return (1..1000, default 100).
    """
    logger.info(
        "tool=read_rows source=%s resource=%s limit=%s", source, resource, limit
    )
    if not 1 <= limit <= MAX_ROW_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_ROW_LIMIT}, got {limit}.")

    adapter = registry.get(source)
    if not isinstance(adapter, SupportsTabularRead):
        raise UnsupportedCapabilityError(source, "tabular reads")

    return adapter.read_rows(resource, limit)


def _register_configured_sources(
    registry: AdapterRegistry, settings: Settings
) -> None:
    """Register optional, externally-configured data sources at runtime.

    Currently just Google Sheets, and only when a spreadsheet ID is configured
    *and* the user has authorized. Any failure is logged and skipped so the
    server still starts with the always-available sources — Google not being set
    up must not take the whole server down.
    """
    if not settings.google_sheets_id:
        logger.info("no google_sheets_id configured; skipping Google Sheets source")
        return
    try:
        credentials = load_credentials(settings)
        service = build_sheets_service(credentials)
        registry.register(
            GoogleSheetsAdapter("gsheets", settings.google_sheets_id, service)
        )
        logger.info("registered Google Sheets source 'gsheets'")
    except GoogleAuthError as error:
        logger.warning("Google Sheets source not registered: %s", error)


def main() -> None:
    """Configure the server from the environment and run it over stdio.

    The ``try/finally`` guarantees we log a shutdown line even when the client
    disconnects or the user interrupts with Ctrl+C.
    """
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    _register_configured_sources(registry, settings)

    logger.info("server starting (name=%s, version=%s)", SERVER_NAME, __version__)
    try:
        mcp.run(transport="stdio")
    finally:
        logger.info("server stopping")


if __name__ == "__main__":
    main()
