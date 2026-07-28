"""Runtime environment checks that must run *before* importing the server.

This module is deliberately **dependency-free** and written to be importable on
old Python interpreters (it uses ``from __future__ import annotations`` so the
type hints never evaluate). That matters because it runs as the very first step
of ``python -m local_data_mcp`` — before we import ``mcp``, which uses 3.10+
``match`` syntax and would otherwise crash with a cryptic ``SyntaxError`` deep
in a dependency when launched on an older Python.
"""

from __future__ import annotations

# The oldest interpreter we support. `mcp` requires 3.10+ (it uses `match`), and
# `pyproject.toml` declares the same floor via `requires-python`.
MINIMUM_PYTHON = (3, 10)


def python_version_error(version_info) -> str | None:
    """Return an actionable message if the interpreter is too old, else ``None``.

    ``version_info`` is a ``sys.version_info``-like tuple; only the
    ``(major, minor)`` prefix is considered.
    """
    if tuple(version_info[:2]) < MINIMUM_PYTHON:
        found = f"{version_info[0]}.{version_info[1]}"
        required = f"{MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}"
        return (
            f"local-data-mcp requires Python {required} or newer, but this "
            f"server was launched with Python {found}. Install Python "
            f"{required}+ and point the extension at that interpreter."
        )
    return None


# Generous upper bound for the version-qualified interpreter names we probe.
# Extend when new CPython minors ship; probing a name that doesn't exist is free.
_NEWEST_KNOWN_MINOR = 15


def find_newer_python(which) -> str | None:
    """Return the path to a version-qualified Python >= ``MINIMUM_PYTHON``, or None.

    ``which`` is a ``shutil.which``-like callable (name -> path or None). We probe
    ``python3.15`` down to ``python3.10`` (newest first) and **trust the qualified
    name to imply the version** — those names (``python3.12`` etc.) are created by
    the standard installers (python.org, Homebrew, distro packages), so no
    subprocess call is needed to confirm the version.

    This is what lets the launcher recover when Claude Desktop starts us with an
    old system Python (e.g. macOS's ``/usr/bin/python3`` == 3.9) while a newer
    interpreter is already installed elsewhere on ``PATH``.
    """
    for minor in range(_NEWEST_KNOWN_MINOR, MINIMUM_PYTHON[1] - 1, -1):
        path = which(f"python3.{minor}")
        if path:
            return path
    return None
