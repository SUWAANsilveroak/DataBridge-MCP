"""Entry point for ``python -m local_data_mcp``.

Three things happen here *before* the server is imported, in order:

1. **Python version guard + self-upgrade.** ``mcp`` uses 3.10+ ``match`` syntax,
   so importing the server on an older interpreter dies with a cryptic
   ``SyntaxError`` deep in a dependency. Claude Desktop may launch us with an old
   system Python (macOS ships 3.9 at ``/usr/bin/python3``). So if the current
   interpreter is too old, we look for a newer one already installed on the
   machine and **re-exec into it** with ``os.execv`` (which replaces this process
   in place, keeping the stdio pipes Claude connected). Only if none is found do
   we print an actionable message and exit. A one-shot env flag guards against
   ever re-exec'ing in a loop. These checks live in ``_runtime`` — a dependency-
   free, old-Python-safe module — so they run before anything that needs 3.10.

2. **``.pth`` processing (Windows only).** When the package runs from a plain
   directory on ``PYTHONPATH`` — as it does inside the packaged desktop
   extension — Python does NOT process ``.pth`` files (that only happens for
   real site-packages dirs). pywin32 ships a ``pywin32.pth`` that sets up its
   DLL directory, and without it ``import pywintypes`` fails (and ``mcp`` imports
   it on Windows). ``site.addsitedir`` makes the vendored directory behave like
   site-packages. It is only needed on Windows — pywin32 is Windows-only — and
   skipping it elsewhere avoids a spurious ``pywin32.pth`` error on macOS/Linux.
"""

import os
import sys

from local_data_mcp._runtime import find_newer_python, python_version_error

# Set once before we re-exec, so a re-exec'd child that is *somehow* still too
# old (e.g. a mislabeled ``python3.12``) reports the error instead of looping.
_REEXEC_GUARD = "LOCAL_DATA_MCP_PY_REEXEC"

_error = python_version_error(sys.version_info)
if _error:
    import shutil

    _newer = None if os.environ.get(_REEXEC_GUARD) else find_newer_python(shutil.which)
    if _newer:
        os.environ[_REEXEC_GUARD] = "1"
        try:
            # Replace this process with the newer interpreter, re-running the same
            # module. execv keeps our stdin/stdout/stderr, so Claude's stdio pipes
            # survive the swap. On success it never returns.
            os.execv(_newer, [_newer, "-m", "local_data_mcp", *sys.argv[1:]])
        except OSError:
            pass  # fall through to the clear error below
    sys.stderr.write(_error + "\n")
    raise SystemExit(1)

if sys.platform == "win32":
    import site
    from pathlib import Path

    site.addsitedir(str(Path(__file__).resolve().parent.parent))

from local_data_mcp.server import main  # noqa: E402 - must follow the guards above

if __name__ == "__main__":
    main()
