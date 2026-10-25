#!/usr/bin/env python3
"""Eclipse Bazaar MCP — v0.1.0, the agent-facing discovery layer for
Eclipse Bazaar, Cyan Eclipse Technologies' tested MCP marketplace.

Powered by Cyan Eclipse Technologies (cetech.ai).

Why this exists: agents shop by problem, not by product name. A listing
in a registry tells an agent a server exists; it does not tell it what
problem the tool solves, whether anyone tested it, or — just as
important — what was NOT tested. This server answers those questions
from the Bazaar catalog:

  * search_products  — keyword search with transparent match reasons
  * find_solutions   — problem-first matching with fit explanations
  * get_product      — full entry incl. certification + not-tested list
  * compare_products — status / pricing / certification side by side
  * get_certification — latest Test Bench verdict + scorecard summary
  * list_categories  — catalog shape, counts by status

Honesty rules (inherited from the Bazaar concept): a product with no
Test Bench verdict says so; spec-stage products are labelled spec and
never certified; nothing in the catalog is invented — every entry is
seeded from a bazaar-manifest.json, a Test Bench scorecard, or the
CETech MCP product slate (see catalog.json "sources").

v0.1.0 scope: CETech catalog only. Third-party listings are P2.
No purchasing yet — purchase hooks are future work: x402 pay-per-call
for paid tools and an Agent Wallet policy check before any charge.

Transport: MCP over stdio (newline-delimited JSON-RPC 2.0), stdlib only.
Catalog: catalog.json beside this file (override with $BAZAAR_CATALOG).
Scorecards: read live from ../test-bench/results/ when summarised.
"""
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
CATALOG_PATH = Path(os.environ.get("BAZAAR_CATALOG", BASE / "catalog.json"))
CETECH_DIR = BASE.parent  # ~/workspace/cyan-eclipse

STOP = {"a", "an", "the", "i", "my", "me", "to", "for", "of", "is", "it",
        "can", "do", "does", "need", "want", "give", "get", "with",
        "without", "and", "or", "on", "in", "an", "agent", "agents",
        "mcp", "tool", "tools", "ai"}


class ToolError(Exception):
    pass


def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        raise ToolError(f"catalog not found: {CATALOG_PATH}")
    return json.loads(CATALOG_PATH.read_text())


def freshness(cat: dict) -> dict:
    return {"catalog_built": cat.get("built"),
            "sources": cat.get("sources", []),
            "note": "Statuses and verdicts are as of the catalog build date; "
                    "scorecard summaries are read live from the referenced files."}


def toks(text: str) -> list:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9\-]*", text.lower())
            if len(t) >= 3 and t not in STOP]


def match_terms(qtoks: list, text: str) -> list:
    tt = set(toks(text))
    return [t for t in qtoks if t in tt]


def brief(p: dict) -> dict:
    c = p["certification"]
    return {"id": p["id"], "name": p["name"], "vendor": p["vendor"],
            "tagline": p["tagline"], "status": p["status"],
            "pricing_model": p["pricing_model"],
            "categories": p["categories"], "platforms": p["platforms"],
            "certification": {"bench_verdict": c["bench_verdict"],
                              "certified": c["certified"]}}


def score_product(p: dict, qtoks: list, weights: dict):
    """Returns (score, match_reasons[]). weights keyed by field."""
    score, reasons = 0, []
    fields = [("name", p["name"]), ("tagline", p["tagline"]),
              ("categories", " ".join(p["categories"])),
              ("capabilities", " ".join(p["capabilities"])),
              ("problem_statements", " ".join(p["problem_statements"]))]
    for field, text in fields:
        hits = match_terms(qtoks, text)
        if hits:
            score += weights[field] * len(hits)
            reasons.append(f"{field} matched: {', '.join(sorted(set(hits)))}")
    return score, reasons


# --------------------------------------------------------------------- tools
def t_search_products(args):
    query = str(args.get("query", "")).strip()
    if not query:
        raise ToolError("query is required")
    category = str(args.get("category", "")).strip().lower()
    cat = load_catalog()
    qt = toks(query)
    weights = {"name": 5, "categories": 4, "capabilities": 3,
               "problem_statements": 2, "tagline": 2}
    hits = []
    for p in cat["products"]:
        if category and category not in [c.lower() for c in p["categories"]]:
            continue
        s, reasons = score_product(p, qt, weights)
        if s > 0:
            h = brief(p)
            h["score"] = s
            h["match_reasons"] = reasons
            hits.append(h)
    hits.sort(key=lambda h: (-h["score"], h["name"]))
    return {"query": query, "count": len(hits), "results": hits,
            "data_freshness": freshness(cat)}


def t_find_solutions(args):
    problem = str(args.get("problem", "")).strip()
    if not problem:
        raise ToolError("problem is required")
    cat = load_catalog()
    qt = toks(problem)
    weights = {"problem_statements": 4, "capabilities": 3, "categories": 2,
               "name": 2, "tagline": 2}
    out = []
    for p in cat["products"]:
        s, reasons = score_product(p, qt, weights)
        if s > 0:
            c = p["certification"]
            badge = c["bench_verdict"] or (
                "not certified (spec-stage)" if p["status"] == "spec"
                else "not yet certified")
            out.append({
                "id": p["id"], "name": p["name"], "score": s,
                "fit": f"{p['name']} — {p['tagline']} "
                       f"Matched on: {'; '.join(reasons)}.",
                "match_reasons": reasons, "status": p["status"],
                "certification_badge": badge,
                "certified": c["certified"],
                "pricing_model": p["pricing_model"],
                "top_capabilities": p["capabilities"][:3]})
    out.sort(key=lambda h: (-h["score"], h["name"]))
    return {"problem": problem, "count": len(out), "solutions": out[:8],
            "data_freshness": freshness(cat)}


def _get(cat, pid):
    for p in cat["products"]:
        if p["id"] == pid:
            return p
    raise ToolError(f"unknown product id: {pid}")


def t_get_product(args):
    pid = str(args.get("id", "")).strip()
    if not pid:
        raise ToolError("id is required")
    cat = load_catalog()
    p = dict(_get(cat, pid))
    p["honesty_note"] = (
        "certification.bench_verdict is null when no Test Bench run exists; "
        "not_tested lists what the bench did not cover — absence of a verdict "
        "is stated, never implied.")
    return {"product": p, "data_freshness": freshness(cat)}


def t_compare_products(args):
    ids = args.get("ids") or []
    if not isinstance(ids, list) or len(ids) < 2:
        raise ToolError("ids must be a list of at least two product ids")
    cat = load_catalog()
    rows = []
    for pid in ids:
        p = _get(cat, str(pid))
        c = p["certification"]
        rows.append({"id": p["id"], "name": p["name"], "status": p["status"],
                     "pricing_model": p["pricing_model"],
                     "certification": c["bench_verdict"] or "none on record",
                     "certified": c["certified"],
                     "certified_scope": c["certified_scope"],
                     "platforms": p["platforms"],
                     "categories": p["categories"],
                     "capability_count": len(p["capabilities"]),
                     "tools": p["tools"]})
    return {"comparison": rows, "data_freshness": freshness(cat)}


def t_get_certification(args):
    pid = str(args.get("id", "")).strip()
    if not pid:
        raise ToolError("id is required")
    cat = load_catalog()
    p = _get(cat, pid)
    c = p["certification"]
    base = {"id": p["id"], "name": p["name"], "status": p["status"],
            "bench_verdict": c["bench_verdict"], "certified": c["certified"],
            "certified_scope": c["certified_scope"],
            "scorecard_ref": c["scorecard_ref"],
            "not_tested": c["not_tested"],
            "data_freshness": freshness(cat)}
    if not c["bench_verdict"]:
        base["certification_status"] = (
            "NOT YET CERTIFIED — no Test Bench verdict on record for this "
            "product. " + ("This product is spec-stage (not built), so no "
                           "bench run is possible yet." if p["status"] == "spec"
                           else "A bench run is pending; treat all capability "
                                "claims as vendor-stated, not bench-verified."))
        base["scorecard_summary"] = None
        return base
    base["certification_status"] = (
        f"Bench verdict on record: {c['bench_verdict']} — scope and "
        f"not_tested state exactly what that verdict does and does not cover.")
    summary = None
    ref = c.get("scorecard_ref")
    if ref:
        path = CETECH_DIR / ref
        if path.exists():
            sc = json.loads(path.read_text())
            checks = sc.get("checks", [])
            counts = {"pass": 0, "fail": 0, "na": 0, "other": 0}
            na_names, fail_names = [], []
            for ch in checks:
                v = ch.get("verdict", "other")
                counts[v if v in counts else "other"] += 1
                if v == "na":
                    na_names.append(ch.get("name"))
                if v == "fail":
                    fail_names.append(ch.get("name"))
            summary = {"tool": sc.get("tool"), "version": sc.get("version"),
                       "bench_date": sc.get("bench_date"),
                       "bench_version": sc.get("bench_version"),
                       "environment": sc.get("environment"),
                       "verdict": sc.get("verdict"),
                       "checks_total": len(checks), "counts": counts,
                       "not_tested_checks": na_names,
                       "failed_checks": fail_names}
    base["scorecard_summary"] = summary
    return base


def t_list_categories(args):
    cat = load_catalog()
    cats = {}
    for p in cat["products"]:
        for cname in p["categories"]:
            e = cats.setdefault(cname, {"category": cname, "total": 0,
                                        "by_status": {}, "products": []})
            e["total"] += 1
            e["by_status"][p["status"]] = e["by_status"].get(p["status"], 0) + 1
            e["products"].append(p["id"])
    return {"categories": sorted(cats.values(), key=lambda e: e["category"]),
            "product_total": len(cat["products"]),
            "data_freshness": freshness(cat)}


TOOLS = {
    "search_products": (t_search_products,
                        "Keyword search over the Bazaar catalog (names, capabilities, categories, problem statements). Every hit carries match_reasons — why it matched is never hidden. Optional category filter.",
                        {"query": {"type": "string"}, "category": {"type": "string"}}, ["query"]),
    "find_solutions": (t_find_solutions,
                       "Describe a problem in plain language; get ranked products with a fit explanation, status, and certification badge inline. Spec-stage products are labelled spec-stage, uncertified products say so.",
                       {"problem": {"type": "string"}}, ["problem"]),
    "get_product": (t_get_product,
                    "Full catalog entry for one product id: capabilities, problem statements, pricing model, platforms, tools, and the certification block including what was NOT tested.",
                    {"id": {"type": "string"}}, ["id"]),
    "compare_products": (t_compare_products,
                         "Side-by-side comparison of 2+ product ids: status, pricing model, certification verdict and scope, platforms, categories.",
                         {"ids": {"type": "array", "items": {"type": "string"}}}, ["ids"]),
    "get_certification": (t_get_certification,
                          "The latest Test Bench verdict for a product, with a live scorecard summary, the certified scope, and the not_tested list. Returns an explicit NOT YET CERTIFIED answer when no verdict exists.",
                          {"id": {"type": "string"}}, ["id"]),
    "list_categories": (t_list_categories,
                        "All catalog categories with product counts broken down by status (live / dogfood / in-development / spec).",
                        {}, []),
}


def tool_list():
    return [{"name": name,
             "description": desc,
             "inputSchema": {"type": "object", "properties": props, "required": req}}
            for name, (_, desc, props, req) in TOOLS.items()]


def handle(req: dict):
    method, rid = req.get("method", ""), req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": req.get("params", {}).get("protocolVersion", "2025-03-26"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "eclipse-bazaar", "version": "0.1.0"}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": tool_list()}}
    if method == "tools/call":
        name = req["params"]["name"]
        args = req["params"].get("arguments", {})
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
        try:
            out = TOOLS[name][0](args)
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps(out, indent=1)}]}}
        except ToolError as e:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True}}
    if rid is not None:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None  # notification


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp = handle(json.loads(line))
        except Exception as e:  # never crash the transport
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
