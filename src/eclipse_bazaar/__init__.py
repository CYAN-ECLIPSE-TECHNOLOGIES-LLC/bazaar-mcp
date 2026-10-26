# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""eclipse-bazaar — one distribution, three surfaces (gate A5):

  * the Eclipse Bazaar MCP server (console script: eclipse-bazaar)
  * the `bazaar` CLI (search / product / categories / check)
  * the Python SDK (from eclipse_bazaar import Bazaar)

Catalog data ships as a stamped bundled snapshot; verdict summaries
ship as a hash-pinned verdict snapshot (gate A1). Powered by Cyan
Eclipse Technologies (cetech.ai).
"""
from ._version import __version__
from .client import Bazaar

__all__ = ["__version__", "Bazaar"]
