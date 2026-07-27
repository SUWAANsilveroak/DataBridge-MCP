"""Entry point for ``python -m local_data_mcp``.

Before importing the server, we process any ``.pth`` files in the directory this
package was loaded from. When the package runs from a plain directory on
``PYTHONPATH`` — as it does inside the packaged desktop extension — Python does
NOT process ``.pth`` files (that only happens for real site-packages dirs). Some
dependencies rely on them: pywin32 ships a ``pywin32.pth`` that sets up its DLL
directory, and without it ``import pywintypes`` fails (and ``mcp`` imports it on
Windows). ``site.addsitedir`` makes the vendored directory behave like
site-packages, fixing that. It is a harmless no-op in a normal venv install.
"""

import site
from pathlib import Path

site.addsitedir(str(Path(__file__).resolve().parent.parent))

from local_data_mcp.server import main  # noqa: E402 - must follow addsitedir

if __name__ == "__main__":
    main()
