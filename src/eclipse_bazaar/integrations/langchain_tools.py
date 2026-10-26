# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""LangChain adapter — the Bazaar SDK as LangChain tools, so an agent
mid-task can query the marketplace without an MCP client configured.

Install: pip install "eclipse-bazaar[langchain]"
Usage:
    from eclipse_bazaar.integrations.langchain_tools import make_langchain_tools
    tools = make_langchain_tools()
"""
import json

from ..client import Bazaar


def make_langchain_tools(bazaar: Bazaar = None):
    try:
        from langchain_core.tools import BaseTool
    except ImportError as e:  # pragma: no cover - optional extra
        raise RuntimeError(
            "langchain-core is not installed — "
            "pip install 'eclipse-bazaar[langchain]'") from e
    bz = bazaar or Bazaar()

    class BazaarSearchTool(BaseTool):
        name: str = "bazaar_search"
        description: str = (
            "Search Eclipse Bazaar (Cyan Eclipse Technologies' catalog of "
            "tested MCP products) by keyword. Returns listings with status "
            "and Test Bench verdicts, plus why each matched.")

        def _run(self, query: str) -> str:
            return json.dumps(bz.search(query), indent=1)

    class BazaarListingTool(BaseTool):
        name: str = "bazaar_get_listing"
        description: str = (
            "Full Eclipse Bazaar catalog entry for one product id, "
            "including its certification block and what was NOT tested.")

        def _run(self, product_id: str) -> str:
            return json.dumps(bz.get_listing(product_id), indent=1)

    return [BazaarSearchTool(), BazaarListingTool()]
