"""Logging setup for the Universal Local Data MCP Server.

Named ``logging_config`` rather than ``logging`` on purpose: a module named
``logging`` would shadow Python's standard-library ``logging`` package and
break ``import logging`` everywhere.

Critical constraint: logs go to **stderr, never stdout**. In a stdio MCP server
the stdout stream carries the JSON-RPC protocol messages between client and
server. Writing anything else to stdout corrupts that stream and breaks the
connection, so every log record must go to stderr.
"""

from __future__ import annotations

import logging
import sys

# One logger namespace for the whole package. Each module gets its own child
# logger via ``logging.getLogger(__name__)``, which inherits this config.
LOGGER_NAME = "local_data_mcp"

# A name on our handler so we can recognise it and avoid attaching it twice.
HANDLER_NAME = "local_data_mcp_stderr"

# Plain-ASCII separator on purpose: fancy Unicode separators render as garbage
# in Windows consoles, and logs must be readable on the platform we run on.
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str) -> logging.Logger:
    """Configure package logging to write to stderr at ``level``.

    Idempotent: calling it more than once will not attach duplicate handlers,
    which would otherwise cause every line to be logged multiple times.

    Returns the package logger so callers can log immediately if they wish.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    already_configured = any(
        handler.get_name() == HANDLER_NAME for handler in logger.handlers
    )
    if not already_configured:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.set_name(HANDLER_NAME)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)

    # Don't bubble records up to the root logger; that would double-print if the
    # root logger has its own handlers (some libraries configure it).
    logger.propagate = False
    return logger
