#!/usr/bin/env python3
# Eclipse Bazaar MCP
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""Repo-mode entry point. The implementation lives in
src/eclipse_bazaar/mcp_server.py (the eclipse-bazaar distribution);
this shim keeps `python3 server.py`, the Dockerfile, and the smoke
tests working from a plain repo checkout."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from eclipse_bazaar.mcp_server import *  # noqa: F401,F403,E402
from eclipse_bazaar.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()

# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
