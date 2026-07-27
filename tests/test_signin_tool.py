"""Tests for the google_sign_in MCP tool.

The real tool opens a browser; here we mock ``authorize`` so we test only that
the tool invokes it and reports success, with no browser or network.
"""

from local_data_mcp import server
from local_data_mcp.server import google_sign_in


def test_google_sign_in_runs_authorize_and_reports(monkeypatch):
    calls = {"n": 0}

    def fake_authorize(settings):
        calls["n"] += 1

    monkeypatch.setattr(server, "authorize", fake_authorize)

    result = google_sign_in()

    assert calls["n"] == 1
    assert "Signed in" in result
