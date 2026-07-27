#!/usr/bin/env python
"""Build the Universal Data MCP Desktop Extension (.mcpb).

Assembles a bundle directory and packs it into ``dist/local-data-mcp.mcpb``:

    build/extension/
      manifest.json          # copied from extension/manifest.json
      credentials.json       # the OAuth client (so teammates don't need their own)
      server/                # our package + ALL dependencies, vendored via pip
                             #   --target, so the end user needs no `pip install`

Run from the project root:

    python scripts/build_extension.py

Requires Node's ``npx`` on PATH (the `mcpb` CLI is fetched via npx).

Caveat: the vendored dependencies include a compiled wheel (pydantic-core), so
the produced bundle is specific to the OS it is built on. Build on Windows for
Windows teammates.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build" / "extension"
SERVER_DIR = BUILD_DIR / "server"
DIST_DIR = ROOT / "dist"
OUTPUT = DIST_DIR / "local-data-mcp.mcpb"

# npx has a .cmd shim on Windows; the bare name isn't directly executable there.
NPX = "npx.cmd" if sys.platform == "win32" else "npx"


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    # 1. Clean any previous build.
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    SERVER_DIR.mkdir(parents=True)
    DIST_DIR.mkdir(exist_ok=True)

    # 2. Vendor the package + every dependency into server/ so the end user
    #    needs no pip install — `python -m local_data_mcp` just works with
    #    PYTHONPATH pointed here.
    run(
        [
            sys.executable, "-m", "pip", "install",
            "--target", str(SERVER_DIR),
            str(ROOT), "--quiet",
        ]
    )

    # 3. Copy the manifest.
    shutil.copy2(ROOT / "extension" / "manifest.json", BUILD_DIR / "manifest.json")

    # 4. Copy the OAuth client (needed for Google sign-in).
    credentials = ROOT / "credentials.json"
    if credentials.exists():
        shutil.copy2(credentials, BUILD_DIR / "credentials.json")
    else:
        print(
            "WARNING: credentials.json not found at the project root; "
            "Google sign-in will not work until it is bundled."
        )

    # 5. Pack into a signed-off .mcpb via the mcpb CLI.
    run([NPX, "--yes", "@anthropic-ai/mcpb@latest", "pack", str(BUILD_DIR), str(OUTPUT)])
    print(f"\nBuilt: {OUTPUT}")


if __name__ == "__main__":
    main()
