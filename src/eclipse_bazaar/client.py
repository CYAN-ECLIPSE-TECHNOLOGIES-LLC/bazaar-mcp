# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""Python SDK for Eclipse Bazaar (candidate C1 — plumbing, no novelty
claim). A small read-only client over the same catalog and corpus the
MCP server and CLI serve: identical ranking, identical match reasons,
identical status labels, because it calls the same functions.

    from eclipse_bazaar import Bazaar
    bz = Bazaar()                      # bundled snapshot (offline)
    bz = Bazaar(refresh=True)          # one bulk HTTPS refresh, fallback local
    bz.search("certificate renewal")   # -> dict like the MCP tool's result
    bz.get_listing("certbridge-mcp")   # full catalog entry
    bz.check()                         # Phase-1 standing check of your configs

No API key (year-one posture: free reads). No telemetry — the client
sends nothing anywhere except the optional bulk catalog refresh.
"""
from . import mcp_server as _srv
from .catalog import catalog_dict
from .check import run_check


class Bazaar:
    def __init__(self, refresh: bool = False):
        self._cat = catalog_dict(refresh=refresh)

    # ------------------------------------------------------ discovery
    def search(self, query: str, category: str = None) -> dict:
        return _srv.t_search_products(
            {"query": query, "category": category or ""}, self._cat)

    def find_solutions(self, problem: str) -> dict:
        return _srv.t_find_solutions({"problem": problem}, self._cat)

    def get_listing(self, product_id: str) -> dict:
        return _srv.t_get_product({"id": product_id}, self._cat)

    get_product = get_listing

    def compare(self, ids) -> dict:
        return _srv.t_compare_products({"ids": list(ids)}, self._cat)

    def get_certification(self, product_id: str) -> dict:
        return _srv.t_get_certification({"id": product_id}, self._cat)

    def categories(self) -> dict:
        return _srv.t_list_categories({}, self._cat)

    # ------------------------------------------------------ standing check
    def check(self, config_paths=None, corpus_path=None,
              refresh_corpus: bool = False) -> dict:
        return run_check(config_paths=config_paths,
                         corpus_path=corpus_path,
                         refresh_corpus=refresh_corpus)
