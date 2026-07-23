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
from local_data_mcp.config import Settings
from local_data_mcp.logging_config import configure_logging

logger = logging.getLogger(__name__)

# The name the client displays for this server. Kept as a constant so the
# server and its tests agree on a single value.
SERVER_NAME = "universal-local-data-mcp"

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


def main() -> None:
    """Configure the server from the environment and run it over stdio.

    The ``try/finally`` guarantees we log a shutdown line even when the client
    disconnects or the user interrupts with Ctrl+C.
    """
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    logger.info("server starting (name=%s, version=%s)", SERVER_NAME, __version__)
    try:
        mcp.run(transport="stdio")
    finally:
        logger.info("server stopping")


if __name__ == "__main__":
    main()
