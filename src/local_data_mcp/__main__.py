"""Entry point for ``python -m local_data_mcp``.

Kept intentionally thin: it only forwards to ``server.main()`` so the "how to
start the server" logic lives in exactly one place.
"""

from local_data_mcp.server import main

if __name__ == "__main__":
    main()
