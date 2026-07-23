"""Tests for logging configuration.

The most important assertion here is that logs go to stderr, not stdout:
stdout is reserved for the MCP JSON-RPC protocol.
"""

import logging
import sys

from local_data_mcp.logging_config import (
    HANDLER_NAME,
    LOGGER_NAME,
    configure_logging,
)


def _our_handlers(logger: logging.Logger) -> list[logging.Handler]:
    return [h for h in logger.handlers if h.get_name() == HANDLER_NAME]


def test_applies_the_requested_level() -> None:
    logger = configure_logging("DEBUG")
    assert logger.level == logging.DEBUG


def test_logs_to_stderr_not_stdout() -> None:
    """The handler must write to stderr; writing to stdout corrupts MCP."""
    logger = configure_logging("INFO")
    handlers = _our_handlers(logger)

    assert len(handlers) == 1
    assert handlers[0].stream is sys.stderr
    assert handlers[0].stream is not sys.stdout


def test_is_idempotent() -> None:
    """Configuring twice must not attach a second handler."""
    configure_logging("INFO")
    configure_logging("INFO")

    logger = logging.getLogger(LOGGER_NAME)
    assert len(_our_handlers(logger)) == 1
