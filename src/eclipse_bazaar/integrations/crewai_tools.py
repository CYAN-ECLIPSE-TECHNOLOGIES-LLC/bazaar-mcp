# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""CrewAI adapter — the Bazaar SDK as CrewAI tools, so a crew agent can
query the marketplace mid-task without an MCP client configured.

Install: pip install "eclipse-bazaar[crewai]"
Usage:
    from eclipse_bazaar.integrations.crewai_tools import make_crewai_tools
    tools = make_crewai_tools()
"""
import json

from ..client import Bazaar


def make_crewai_tools(bazaar: Bazaar = None):
    try:
        from crewai.tools import BaseTool
    except ImportError as e:  # pragma: no cover - optional extra
        raise RuntimeError(
            "crewai is not installed — "
            "pip install 'eclipse-bazaar[crewai]'") from e
    bz = bazaar or Bazaar()

    class BazaarSearchTool(BaseTool):
        name: str = "bazaar_search"
        description: str = (
            "Search Eclipse Bazaar (Cyan Eclipse Technologies' catalog of "
            "tested MCP products) by keyword. Input: a search query string. "
            "Returns listings with status and Test Bench verdicts.")

        def _run(self, query: str) -> str:
            return json.dumps(bz.search(query), indent=1)

    class BazaarListingTool(BaseTool):
        name: str = "bazaar_get_listing"
        description: str = (
            "Full Eclipse Bazaar catalog entry for one product id, "
            "including its certification block and what was NOT tested. "
            "Input: the product id.")

        def _run(self, product_id: str) -> str:
            return json.dumps(bz.get_listing(product_id), indent=1)

    return [BazaarSearchTool(), BazaarListingTool()]
