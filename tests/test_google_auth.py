"""Tests for Google Workspace authentication.

We never hit Google or open a browser. Instead we mock the Google boundary
(``Credentials``, ``Request``, ``InstalledAppFlow``) and test *our* logic: the
missing-token error, returning a valid token, the refresh path, and the failure
paths. This is exactly why the OAuth logic lives behind our own functions —
it makes the behaviour testable.
"""

import json
from pathlib import Path

import pytest

from local_data_mcp.config import Settings
from local_data_mcp.errors import GoogleAuthError
from local_data_mcp.google_workspace import auth as auth_module


class FakeCredentials:
    """A stand-in for google.oauth2.credentials.Credentials."""

    def __init__(self, valid=True, expired=False, refresh_token="refresh-token"):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refreshed = False

    def refresh(self, request):
        self.refreshed = True
        self.valid = True
        self.expired = False

    def to_json(self):
        return json.dumps({"token": "fake"})


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_credentials_file=str(tmp_path / "credentials.json"),
        google_token_file=str(tmp_path / "token.json"),
    )


def _write(path: str) -> None:
    Path(path).write_text("{}", encoding="utf-8")


# --- load_credentials -------------------------------------------------------


def test_missing_token_raises_not_authorized(tmp_path):
    settings = _settings(tmp_path)  # no token file created
    with pytest.raises(GoogleAuthError, match="Not authorized"):
        auth_module.load_credentials(settings)


def test_valid_token_is_returned_as_is(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _write(settings.google_token_file)
    fake = FakeCredentials(valid=True)
    monkeypatch.setattr(
        auth_module.Credentials, "from_authorized_user_file", lambda *a, **k: fake
    )

    assert auth_module.load_credentials(settings) is fake


def test_expired_token_is_refreshed_and_saved(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _write(settings.google_token_file)
    fake = FakeCredentials(valid=False, expired=True, refresh_token="r")
    monkeypatch.setattr(
        auth_module.Credentials, "from_authorized_user_file", lambda *a, **k: fake
    )
    monkeypatch.setattr(auth_module, "Request", lambda: object())

    result = auth_module.load_credentials(settings)

    assert result is fake
    assert fake.refreshed is True
    # The refreshed token should have been written back to disk.
    assert json.loads(Path(settings.google_token_file).read_text()) == {"token": "fake"}


def test_refresh_failure_raises(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _write(settings.google_token_file)
    fake = FakeCredentials(valid=False, expired=True, refresh_token="r")

    def boom(request):
        raise auth_module.RefreshError("revoked")

    fake.refresh = boom
    monkeypatch.setattr(
        auth_module.Credentials, "from_authorized_user_file", lambda *a, **k: fake
    )
    monkeypatch.setattr(auth_module, "Request", lambda: object())

    with pytest.raises(GoogleAuthError, match="Re-authorize"):
        auth_module.load_credentials(settings)


def test_invalid_without_refresh_token_raises(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _write(settings.google_token_file)
    fake = FakeCredentials(valid=False, expired=False, refresh_token=None)
    monkeypatch.setattr(
        auth_module.Credentials, "from_authorized_user_file", lambda *a, **k: fake
    )

    with pytest.raises(GoogleAuthError):
        auth_module.load_credentials(settings)


# --- authorize --------------------------------------------------------------


def test_authorize_without_credentials_file_raises(tmp_path):
    settings = _settings(tmp_path)  # credentials.json does not exist
    with pytest.raises(GoogleAuthError, match="OAuth client file not found"):
        auth_module.authorize(settings)


def test_authorize_runs_flow_and_saves_token(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    _write(settings.google_credentials_file)
    fake = FakeCredentials()

    class FakeFlow:
        @staticmethod
        def from_client_secrets_file(path, scopes):
            return FakeFlow()

        def run_local_server(self, port=0):
            return fake

    monkeypatch.setattr(auth_module, "InstalledAppFlow", FakeFlow)

    result = auth_module.authorize(settings)

    assert result is fake
    assert Path(settings.google_token_file).exists()
