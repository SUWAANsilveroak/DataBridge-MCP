"""Google Workspace OAuth: obtain and refresh user credentials.

Auth has two phases:

1. ``authorize()`` — INTERACTIVE. Opens a browser, the user consents, and a
   long-lived token (with a refresh token) is written to disk. It is exposed to
   users both as the ``google_sign_in`` MCP tool and as a terminal command.
2. ``load_credentials()`` — SILENT, used at runtime by adapters. Reads the saved
   token and refreshes it automatically. Never opens a browser.

Because this process's stdout is the MCP protocol channel, ``authorize`` runs the
browser flow with its console output redirected to stderr, so a sign-in
triggered from inside the server can never corrupt the protocol.

Nothing here is tied to a specific Google account: the credentials file and the
token file are configurable paths, and the scopes are the same for a personal or
an organization account. Switching from personal to org later is just "swap
credentials.json and sign in again" — no code changes.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from local_data_mcp.config import Settings
from local_data_mcp.errors import GoogleAuthError

logger = logging.getLogger(__name__)

# Least-privilege, read-only scopes. We deliberately do NOT request a Drive
# scope: adapters target explicit spreadsheet/document IDs instead of listing an
# entire account. These scopes are identical for a personal or an org account.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

_SIGN_IN_HINT = (
    "Sign in to Google first: use the `google_sign_in` tool, or run "
    "`python -m local_data_mcp.google_workspace.auth`."
)


def load_credentials(settings: Settings) -> Credentials:
    """Return valid Google credentials for runtime use, refreshing if needed.

    Raises ``GoogleAuthError`` if the user has not signed in yet, or if the saved
    token is invalid and cannot be refreshed (e.g. it was revoked).
    """
    token_path = Path(settings.google_token_file)
    if not token_path.exists():
        raise GoogleAuthError(
            f"Not signed in to Google (no token at '{token_path}'). {_SIGN_IN_HINT}"
        )

    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if credentials.valid:
        return credentials

    if credentials.expired and credentials.refresh_token:
        logger.info("refreshing expired Google credentials")
        try:
            credentials.refresh(Request())
        except RefreshError as error:
            raise GoogleAuthError(
                f"Could not refresh Google credentials. {_SIGN_IN_HINT}"
            ) from error
        _save_token(credentials, token_path)
        return credentials

    raise GoogleAuthError(
        f"Google credentials are invalid and cannot be refreshed. {_SIGN_IN_HINT}"
    )


def authorize(settings: Settings | None = None) -> Credentials:
    """Run the interactive browser consent flow and save the token.

    Safe to call from inside the MCP server: the flow's console output is
    redirected to stderr so it cannot corrupt the stdout protocol channel.
    """
    settings = settings or Settings.from_env()

    credentials_path = Path(settings.google_credentials_file)
    if not credentials_path.exists():
        raise GoogleAuthError(
            f"OAuth client file not found at '{credentials_path}'. Download it "
            "from the Google Cloud Console (Credentials -> OAuth client ID -> "
            "Desktop app) and save it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    # This process's stdout carries the MCP protocol; keep the flow's prints off
    # it by redirecting them to stderr for the duration of the browser flow.
    with contextlib.redirect_stdout(sys.stderr):
        credentials = flow.run_local_server(port=0)

    _save_token(credentials, Path(settings.google_token_file))
    return credentials


def _save_token(credentials: Credentials, token_path: Path) -> None:
    """Persist credentials (including the refresh token) to disk as JSON."""
    token_path.write_text(credentials.to_json(), encoding="utf-8")


def main() -> None:
    """Terminal entry point for the one-time authorization.

    This is a standalone CLI the user runs by hand, so printing to stdout is
    fine here — unlike the MCP server, whose stdout carries the protocol.
    """
    settings = Settings.from_env()
    authorize(settings)
    print(f"Authorized. Token saved to '{settings.google_token_file}'.")


if __name__ == "__main__":
    main()
