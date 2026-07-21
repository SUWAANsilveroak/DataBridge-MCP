"""Tests for the walking-skeleton MCP server.

We test the *logic* of our tool (the value it returns), not the stdio
transport. Testing the transport would really be testing the MCP SDK, which is
not our code.
"""

from local_data_mcp import __version__
from local_data_mcp.server import SERVER_NAME, server_info


def test_server_info_returns_expected_shape() -> None:
    """server_info reports the server name, version, and an ok status."""
    info = server_info()

    assert info == {
        "name": SERVER_NAME,
        "version": __version__,
        "status": "ok",
    }


def test_server_info_version_matches_package() -> None:
    """The reported version stays tied to the single source of truth."""
    assert server_info()["version"] == __version__
