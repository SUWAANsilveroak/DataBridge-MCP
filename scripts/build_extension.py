#!/usr/bin/env python
"""Build the Universal Data MCP Desktop Extensions (.mcpb), one per OS.

Each bundle is fully self-contained — a relocatable Python plus every
dependency — so a teammate installs it with zero setup (no Python, no version to
match). For each target OS we assemble:

    build/<target>/
      manifest.json          # generated from extension/manifest.json, with the
                             #   run command pointed at the bundled interpreter
      credentials.json       # the OAuth client (so teammates don't need their own)
      runtime/python/...     # a standalone CPython (python-build-standalone)
      server/...             # our package + all deps, vendored for that OS via uv

and pack it into ``dist/local-data-mcp-<target>.mcpb``.

Run from the project root (defaults to building all targets):

    python scripts/build_extension.py                 # windows, macos-arm64, linux
    python scripts/build_extension.py windows          # just one

Requires: ``uv`` (``pip install uv``) for cross-OS dependency resolution, and
Node's ``npx`` on PATH (the ``mcpb`` CLI is fetched via npx). Cross-building all
OSes from one machine works because deps ship as wheels and the standalone
Pythons are downloaded per target; only a runtime *smoke test* must happen on
each OS.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = ROOT / "build"
DIST_DIR = ROOT / "dist"
WHEEL_DIR = BUILD_ROOT / "wheel"

# npx has a .cmd shim on Windows; the bare name isn't directly executable there.
NPX = "npx.cmd" if sys.platform == "win32" else "npx"

# google-api-python-client bundles a static discovery document for EVERY Google
# API (~586 files, ~100 MB). We only ever call the Sheets and Docs APIs, so we
# keep those two discovery docs and delete the rest. `build()` still works fully
# offline for our APIs from the kept files.
KEEP_DISCOVERY_DOCS = {"sheets.v4.json", "docs.v1.json"}

# --- Level B: bundle a self-contained Python per OS -------------------------
#
# We ship a relocatable "standalone" CPython inside each bundle so the end user
# needs no Python at all, and so the interpreter minor version is fixed — which
# keeps the compiled `pydantic-core` wheel we vendor in lock-step with it (a
# cp312 wheel with a cp312 interpreter, always). Builds come from the
# python-build-standalone project (the same distributions uv/rye use).
PYTHON_MINOR = "3.12"
PBS_LATEST_API = (
    "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
)

# Per target OS: the python-build-standalone platform "triple", the relative
# path to the interpreter inside the extracted runtime, and the output name.
TARGETS = {
    "windows": {
        "triple": "x86_64-pc-windows-msvc",
        "python_exe": "python/python.exe",
        "output": "local-data-mcp-windows.mcpb",
    },
    # Apple Silicon (M-series). To add Intel Macs later, add a "macos-intel"
    # entry with triple "x86_64-apple-darwin".
    "macos-arm64": {
        "triple": "aarch64-apple-darwin",
        "python_exe": "python/bin/python3.12",
        "output": "local-data-mcp-macos-arm64.mcpb",
    },
    "linux": {
        "triple": "x86_64-unknown-linux-gnu",
        "python_exe": "python/bin/python3.12",
        "output": "local-data-mcp-linux.mcpb",
    },
}

_USER_AGENT = {"User-Agent": "local-data-mcp-build"}


def _standalone_python_asset(triple: str) -> tuple[str, str]:
    """Return (download_url, filename) for the standalone CPython we want.

    Queries the latest python-build-standalone release and picks the
    ``install_only`` archive for our Python minor + target triple, preferring
    the smaller ``install_only_stripped`` variant when it is published.
    """
    request = urllib.request.Request(PBS_LATEST_API, headers=_USER_AGENT)
    with urllib.request.urlopen(request) as response:
        release = json.loads(response.read())

    matches = [
        asset
        for asset in release.get("assets", [])
        if asset["name"].startswith(f"cpython-{PYTHON_MINOR}.")
        and triple in asset["name"]
        and asset["name"].endswith(".tar.gz")
        and "install_only" in asset["name"]
    ]
    if not matches:
        raise RuntimeError(
            f"No standalone Python {PYTHON_MINOR} '{triple}' build in the latest "
            "python-build-standalone release."
        )
    stripped = [a for a in matches if "install_only_stripped" in a["name"]]
    chosen = (stripped or matches)[0]
    return chosen["browser_download_url"], chosen["name"]


def download_standalone_python(triple: str, runtime_dir: Path) -> None:
    """Download and extract a relocatable CPython into ``runtime_dir`` (as python/)."""
    url, name = _standalone_python_asset(triple)
    print(f"  fetching {name}")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    archive = runtime_dir / name

    request = urllib.request.Request(url, headers=_USER_AGENT)
    with urllib.request.urlopen(request) as response, open(archive, "wb") as out:
        shutil.copyfileobj(response, out)

    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(runtime_dir, filter="data")
    archive.unlink()


# uv (Astral) does the dependency vendoring. Unlike pip, its --python-platform
# evaluates environment markers for the TARGET OS, so Windows-only deps
# (pywin32, colorama) are correctly excluded from macOS/Linux bundles and kept
# in the Windows one. It is a build-time tool only, never shipped.


def _uv() -> str:
    """Locate the uv executable (prefer the one in this venv), or explain how to get it."""
    local = Path(sys.executable).parent / ("uv.exe" if sys.platform == "win32" else "uv")
    if local.exists():
        return str(local)
    found = shutil.which("uv")
    if found:
        return found
    raise RuntimeError("uv is required to build the extension. Install it with: pip install uv")


def build_our_wheel() -> Path:
    """Build our pure-Python package into a wheel and return its path.

    Vendoring uses ``--only-binary :all:`` (nothing is built from source for the
    target platform), so our own package must be a wheel too. It is pure Python,
    so the single ``py3-none-any`` wheel is valid for every OS.
    """
    if WHEEL_DIR.exists():
        shutil.rmtree(WHEEL_DIR)
    WHEEL_DIR.mkdir(parents=True)
    run([sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(WHEEL_DIR), str(ROOT), "--quiet"])
    wheels = list(WHEEL_DIR.glob("local_data_mcp-*.whl"))
    if not wheels:
        raise RuntimeError("Failed to build the local_data_mcp wheel.")
    return wheels[0]


def vendor_dependencies(server_dir: Path, python_platform: str, our_wheel: Path) -> None:
    """Vendor our package + all deps for the target OS into ``server_dir``.

    ``python_platform`` is uv's target triple (e.g. ``aarch64-apple-darwin``);
    markers resolve against it, not the build host, which is what keeps a
    Windows-only dependency out of a macOS/Linux bundle.
    """
    run([
        _uv(), "pip", "install",
        "--target", str(server_dir),
        "--python-platform", python_platform,
        "--python-version", PYTHON_MINOR,
        "--only-binary", ":all:",
        str(our_wheel),
    ])


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def prune_bundle(server_dir: Path) -> None:
    """Delete files that are never used at runtime, shrinking the bundle.

    Everything removed here is provably irrelevant to *running* the server, so
    there is zero functional impact:

    - unused Google API discovery documents (we call only Sheets + Docs),
    - ``__pycache__`` bytecode caches (Python regenerates them on demand),
    - ``.chm`` help manuals and ``.pyi`` type stubs (docs / type-checker only).
    """
    before = _dir_size(server_dir)

    # 1. Unused Google API discovery documents — by far the biggest win.
    docs_dir = server_dir / "googleapiclient" / "discovery_cache" / "documents"
    if docs_dir.is_dir():
        for doc in docs_dir.glob("*.json"):
            if doc.name not in KEEP_DISCOVERY_DOCS:
                doc.unlink()

    # 2. Bytecode caches.
    for cache in server_dir.rglob("__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache)

    # 3. Help manuals and type stubs.
    for pattern in ("*.chm", "*.pyi"):
        for path in server_dir.rglob(pattern):
            if path.is_file():
                path.unlink()

    after = _dir_size(server_dir)
    print(
        f"  pruned deps {(before - after) / 1_000_000:.1f} MB "
        f"({before / 1_000_000:.1f} MB -> {after / 1_000_000:.1f} MB)"
    )


# Interpreter subtrees our server never imports. Removing them is safe and cuts
# the bundled Python a lot (the test suite and Tcl/Tk dominate). Names are
# matched wherever they live, since the Windows (``python/Lib``) and Unix
# (``python/lib/pythonX.Y``) standalone layouts differ.
_RUNTIME_PRUNE_NAMES = (
    "test",  # CPython's own test suite (large)
    "tkinter",  # GUI toolkit — unused by a headless server
    "turtledemo",
    "idlelib",  # the IDLE editor
    "ensurepip",  # we never pip-install at runtime
    "pydoc_data",  # backs help() text
    "lib2to3",
)


def prune_runtime(runtime_dir: Path) -> None:
    """Strip parts of the bundled interpreter the server never uses.

    Zero functional impact: our server is headless and never imports Tk, IDLE,
    the test suite, etc. Big size win on the standalone Python.
    """
    before = _dir_size(runtime_dir)
    py = runtime_dir / "python"

    # Standard-library dir: Windows -> python/Lib ; Unix -> python/lib/python3.x
    lib_dirs = [py / "Lib", *(py / "lib").glob("python3.*")]
    for lib in lib_dirs:
        if not lib.is_dir():
            continue
        for name in _RUNTIME_PRUNE_NAMES:
            victim = lib / name
            if victim.is_dir():
                shutil.rmtree(victim, ignore_errors=True)

    # Tcl/Tk (data dirs + shared libs) — only needed by tkinter, now removed.
    # Standalone builds ship Tcl/Tk 8 *or* 9, at python/tcl (Windows) or under
    # python/lib (Unix), plus the itcl/thread/tdbc companions.
    for parent in (py, py / "lib"):
        if not parent.is_dir():
            continue
        for prefix in ("tcl", "tk", "itcl", "thread", "tdbc"):
            for path in parent.glob(f"{prefix}*"):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
    for pattern in ("_tkinter*", "tk*.dll", "tcl*.dll", "libtcl*", "libtk*"):
        for path in py.rglob(pattern):
            if path.is_file():
                path.unlink()

    # Unix only: standalone builds ship the interpreter binary three times
    # (python, python3, python3.12), and cross-extracting on Windows turns the
    # symlinks into full copies. Keep only python3.12 (what the manifest
    # launches) and drop the CLI shims (pip, idle, 2to3, *-config).
    bin_dir = py / "bin"
    if bin_dir.is_dir():
        for entry in bin_dir.iterdir():
            if entry.name == "python3.12":
                continue
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink()

    # Unix only: a dev symlink-copy of libpython duplicates the real SONAME lib.
    soname = py / "lib" / "libpython3.12.so.1.0"
    devlink = py / "lib" / "libpython3.12.so"
    if soname.exists() and devlink.exists():
        devlink.unlink()

    # C headers and shared data (terminfo, man) — not needed to run a headless
    # server; nothing compiles at runtime since we ship prebuilt wheels.
    for extra in ("include", "share"):
        path = py / extra
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

    # Bytecode caches (regenerated on demand).
    for cache in py.rglob("__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache, ignore_errors=True)

    after = _dir_size(runtime_dir)
    print(
        f"  pruned runtime {(before - after) / 1_000_000:.1f} MB "
        f"({before / 1_000_000:.1f} MB -> {after / 1_000_000:.1f} MB)"
    )


def write_manifest(target_dir: Path, spec: dict) -> None:
    """Write a per-OS manifest: the base manifest with the run command pointed at
    the bundled interpreter (absolute via ``${__dirname}``, so no system Python)."""
    manifest = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
    manifest["server"]["mcp_config"]["command"] = "${__dirname}/runtime/" + spec["python_exe"]
    (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def copy_credentials(target_dir: Path) -> None:
    credentials = ROOT / "credentials.json"
    if credentials.exists():
        shutil.copy2(credentials, target_dir / "credentials.json")
    else:
        print(
            "  WARNING: credentials.json not found at the project root; "
            "Google sign-in will not work until it is bundled."
        )


def set_executable_in_mcpb(mcpb_path: Path, exec_arcname: str) -> None:
    """Set the Unix executable bit on one entry inside a packed ``.mcpb`` zip.

    Needed only for the Unix (macOS/Linux) bundles when building on Windows: a
    Windows filesystem has no executable bit, so the bundled ``python3.12`` gets
    zipped without it and macOS/Linux refuse to spawn it ("Permission denied").
    We rewrite the archive, forcing mode 0o755 on the interpreter. (Native Unix
    builds preserve the bit and this is a harmless no-op there.)
    """
    exec_arcname = exec_arcname.replace("\\", "/")
    temp = mcpb_path.with_name(mcpb_path.name + ".tmp")
    with zipfile.ZipFile(mcpb_path) as zin, zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            if item.filename.replace("\\", "/") == exec_arcname:
                # High 16 bits of external_attr hold the Unix st_mode. Set a
                # regular file (S_IFREG) with rwxr-xr-x so it extracts executable.
                info.external_attr = (0o100755 << 16) | (info.external_attr & 0xFFFF)
            zout.writestr(info, data)
    temp.replace(mcpb_path)


def build_target(name: str, spec: dict, our_wheel: Path) -> Path:
    """Assemble and pack the bundle for one OS; return the output path."""
    print(f"\n=== {name} ===")
    target_dir = BUILD_ROOT / name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    server_dir = target_dir / "server"
    runtime_dir = target_dir / "runtime"
    server_dir.mkdir(parents=True)

    vendor_dependencies(server_dir, spec["triple"], our_wheel)
    download_standalone_python(spec["triple"], runtime_dir)
    prune_bundle(server_dir)
    prune_runtime(runtime_dir)
    write_manifest(target_dir, spec)
    copy_credentials(target_dir)

    output = DIST_DIR / spec["output"]
    run([NPX, "--yes", "@anthropic-ai/mcpb@latest", "pack", str(target_dir), str(output)])
    # Unix bundles need the interpreter's executable bit restored (Windows zips
    # drop it). ``.exe`` targets (Windows) don't need it.
    if not spec["python_exe"].endswith(".exe"):
        set_executable_in_mcpb(output, "runtime/" + spec["python_exe"])
        print("  set +x on bundled python3.12")
    size_mb = output.stat().st_size / 1_000_000
    print(f"  built {output.name} ({size_mb:.1f} MB)")
    return output


def main() -> None:
    requested = sys.argv[1:] or list(TARGETS)
    unknown = [t for t in requested if t not in TARGETS]
    if unknown:
        raise SystemExit(f"Unknown target(s): {unknown}. Choose from {list(TARGETS)}.")

    DIST_DIR.mkdir(exist_ok=True)
    our_wheel = build_our_wheel()

    built = [build_target(name, TARGETS[name], our_wheel) for name in requested]

    print("\nBuilt:")
    for path in built:
        print(f"  {path}")


if __name__ == "__main__":
    main()
