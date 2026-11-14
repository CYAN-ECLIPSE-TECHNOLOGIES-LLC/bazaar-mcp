#!/usr/bin/env python3
# Eclipse Bazaar MCP
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai

"""Eclipse Bazaar MCP — the agent-facing discovery layer for
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
Catalog: bundled snapshot (repo mode: the repo-root catalog.json;
override with $BAZAAR_CATALOG). Scorecards: the stamped verdict
snapshot bundled in eclipse_bazaar/data (gate A1 — an installed wheel
never reaches for ../test-bench/results/); repo mode falls back to the
referenced card when the snapshot lacks the ref.
"""
import json
import re
import sys

from ._version import __version__
from .catalog import catalog_dict, freshness, scorecard_summary

STOP = {"a", "an", "the", "i", "my", "me", "to", "for", "of", "is", "it",
        "can", "do", "does", "need", "want", "give", "get", "with",
        "without", "and", "or", "on", "in", "an", "agent", "agents",
        "mcp", "tool", "tools", "ai"}


class ToolError(Exception):
    pass


def load_catalog() -> dict:
    try:
        return catalog_dict()
    except FileNotFoundError as e:
        raise ToolError(f"catalog not found: {e.filename}")


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
def t_search_products(args, cat=None):
    query = str(args.get("query", "")).strip()
    if not query:
        raise ToolError("query is required")
    category = str(args.get("category", "")).strip().lower()
    cat = cat if cat is not None else load_catalog()
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


def t_find_solutions(args, cat=None):
    problem = str(args.get("problem", "")).strip()
    if not problem:
        raise ToolError("problem is required")
    cat = cat if cat is not None else load_catalog()
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


def t_get_product(args, cat=None):
    pid = str(args.get("id", "")).strip()
    if not pid:
        raise ToolError("id is required")
    cat = cat if cat is not None else load_catalog()
    p = dict(_get(cat, pid))
    # Ryan QA #4: not_tested entries refer readers to `live_state_note`;
    # surface it at the product level too (it also stays inside the
    # certification block) so no rendering can drop it silently.
    p["live_state_note"] = (p.get("certification") or {}).get(
        "live_state_note")
    # Ryan QA #2: no install-plan exists on any surface yet. Say so in
    # the record itself rather than letting a tagline imply one.
    p["install_plan"] = {
        "status": "not_available",
        "note": ("not available yet — no install plan exists for this "
                 "listing: no package command, client config snippet, "
                 "or install steps are provided")}
    p["honesty_note"] = (
        "certification.bench_verdict is null when no Test Bench run exists; "
        "not_tested lists what the bench did not cover — absence of a verdict "
        "is stated, never implied.")
    return {"product": p, "data_freshness": freshness(cat)}


def t_compare_products(args, cat=None):
    ids = args.get("ids") or []
    if not isinstance(ids, list) or len(ids) < 2:
        raise ToolError("ids must be a list of at least two product ids")
    cat = cat if cat is not None else load_catalog()
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


def t_get_certification(args, cat=None):
    pid = str(args.get("id", "")).strip()
    if not pid:
        raise ToolError("id is required")
    cat = cat if cat is not None else load_catalog()
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
    ref = c.get("scorecard_ref")
    base["scorecard_summary"] = scorecard_summary(ref) if ref else None
    return base


def t_list_categories(args, cat=None):
    cat = cat if cat is not None else load_catalog()
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
                        "Keyword search over the Bazaar catalog (names, capabilities, categories, problem statements). Every hit carries match_reasons — why it matched is never hidden. Optional category filter. Use find_solutions instead when you have a problem to describe rather than keywords; use get_product once you have a product id. Behaviour: read-only, no authentication, no side effects; results come from the bundled catalog snapshot (Cyan Eclipse's own catalog only — no third-party listings), ranked by weighted field match with the best match first and no result cap; every answer carries data_freshness for that snapshot. Scope: this server does discovery and certification lookup only — it does not sell, install, or run the listed products. Returns an object with query, count, results (id, name, vendor, tagline, status, pricing_model, categories, platforms, certification summary, score, match_reasons), and data_freshness.",
                        {"query": {"type": "string",
                                   "description": "Keyword or phrase matched against product names, capabilities, categories, and problem statements."},
                         "category": {"type": "string",
                                      "description": "Optional exact category name, as returned by list_categories, to restrict the search; omit to search the whole catalog."}}, ["query"]),
    "find_solutions": (t_find_solutions,
                       "Describe a problem in plain language; get ranked products with a fit explanation, status, and certification badge inline. Spec-stage products are labelled spec-stage, uncertified products say so. Use search_products instead when you already have keywords or a category in mind; use get_product once you have a product id. Behaviour: read-only, no authentication, no side effects; matching is keyword-based over the bundled catalog snapshot's problem statements and capabilities (not a semantic embedding search), and at most 8 solutions are returned while count reports the total number of matches. Returns an object with problem, count, solutions (id, name, score, fit explanation, match_reasons, status, certification_badge, certified, pricing_model, top_capabilities), and data_freshness.",
                       {"problem": {"type": "string",
                                    "description": "The problem to solve, in plain language — a sentence or two works best."}}, ["problem"]),
    "get_product": (t_get_product,
                    "Full catalog entry for one product id: capabilities, problem statements, pricing model, platforms, tools, and the certification block including what was NOT tested, plus the product's live_state_note and its explicit install_plan status (no install plan exists yet — this server provides no package command, client config, or install steps for any listing). Use get_certification instead when you only need the bench verdict, scope, and not_tested list for the same id. Behaviour: read-only, no authentication, no side effects; an unknown id returns an 'unknown product id' error. Returns an object with product (the full catalog entry, plus live_state_note, install_plan, and an honesty_note stating that a null bench_verdict means no Test Bench run exists) and data_freshness.",
                    {"id": {"type": "string",
                            "description": "Catalog product id, as returned by search_products, find_solutions, or list_categories."}}, ["id"]),
    "compare_products": (t_compare_products,
                         "Compare two or more catalog products side by side on the decision fields: status, pricing model, Test Bench certification verdict (or 'none on record') with its certified scope, platforms, categories, capability count, and tool list. Use this after search_products or find_solutions has given you a shortlist and you need to choose between specific products; use get_product instead when you need one product's full entry (capabilities, problem statements, not_tested list), and get_certification when you need one product's full verdict record and scorecard summary rather than a comparison row. Behaviour: read-only, no authentication, no side effects; it reads the same bundled catalog snapshot as every other tool here, and an unknown product id fails the whole call with an 'unknown product id' error — there are no partial comparisons. Parameter: ids must contain at least two catalog product ids (fewer returns an error). Returns an object with comparison (one row per requested id, in request order: id, name, status, pricing_model, certification, certified, certified_scope, platforms, categories, capability_count, tools) and data_freshness describing the catalog snapshot.",
                         {"ids": {"type": "array", "items": {"type": "string"},
                                  "description": "Two or more catalog product ids, as returned by search_products, find_solutions, or list_categories. At least two are required; an unknown id fails the whole call."}}, ["ids"]),
    "get_certification": (t_get_certification,
                          "The latest Test Bench verdict for a product, with a live scorecard summary, the certified scope, and the not_tested list. Returns an explicit NOT YET CERTIFIED answer when no verdict exists. Use get_product instead when you need the full catalog entry for the same id. Behaviour: read-only, no authentication, no side effects; an unknown id returns an 'unknown product id' error, while a known product with no bench run is not an error — it returns certification_status NOT YET CERTIFIED (for a spec-stage product, that no bench run is possible yet) with scorecard_summary null. Returns an object with id, name, status, bench_verdict, certified, certified_scope, scorecard_ref, not_tested, certification_status, scorecard_summary, and data_freshness.",
                          {"id": {"type": "string",
                                  "description": "Catalog product id, as returned by search_products, find_solutions, or list_categories."}}, ["id"]),
    "list_categories": (t_list_categories,
                        "All catalog categories with product counts broken down by status (live / first-party / in-development / spec), plus the product ids in each category. Start here to browse the catalog; use the returned ids with get_product or get_certification, and the category names as search_products' category filter. Behaviour: read-only, no authentication, no side effects, takes no parameters; the catalog covered is Cyan Eclipse's own (no third-party listings). Returns an object with categories (category, total, by_status, products), product_total, and data_freshness.",
                        {}, []),
}

TITLES = {
    "search_products": "Search Products",
    "find_solutions": "Find Solutions",
    "get_product": "Get Product",
    "compare_products": "Compare Products",
    "get_certification": "Get Certification",
    "list_categories": "List Categories",
}

# ------------------------------------------------------------- output schemas
# Derived from the return construction of each t_* function above and the
# catalog record shape; verified against real tool outputs in the audit of
# 2026-11-12. Fields whose values are copied verbatim from catalog records
# carry a description instead of a guessed type where the catalog itself
# allows more than one JSON type.
_FRESHNESS = {
    "type": "object",
    "description": "Catalog snapshot provenance for this answer.",
    "properties": {
        "catalog_built": {"type": ["string", "null"],
                          "description": "Build date of the catalog snapshot served."},
        "sources": {"type": "array", "items": {"type": "string"},
                    "description": "Source descriptions the catalog was built from."},
        "served_from": {"type": "string",
                        "description": "Which catalog copy was served (bundled snapshot, repo catalog, or refreshed source)."},
        "note": {"type": "string"}},
    "required": ["catalog_built", "sources", "served_from", "note"]}

_CERT_SUMMARY = {
    "type": "object",
    "properties": {
        "bench_verdict": {"type": ["string", "null"],
                          "description": "Test Bench verdict text, or null when no bench run exists."},
        "certified": {"type": "boolean"}},
    "required": ["bench_verdict", "certified"]}

_BRIEF = {
    "type": "object",
    "description": "Catalog brief for one product (the search/find result row shape).",
    "properties": {
        "id": {"type": "string"}, "name": {"type": "string"},
        "vendor": {"type": "string"}, "tagline": {"type": "string"},
        "status": {"type": "string"}, "pricing_model": {"type": "string"},
        "categories": {"type": "array", "items": {"type": "string"}},
        "platforms": {"type": "array", "items": {"type": "string"}},
        "certification": _CERT_SUMMARY},
    "required": ["id", "name", "vendor", "tagline", "status", "pricing_model",
                 "categories", "platforms", "certification"]}

_SCORECARD_SUMMARY = {
    "type": "object",
    "description": "Summary of the stamped Test Bench scorecard for the product.",
    "properties": {
        "tool": {"description": "Product/tool name as recorded on the scorecard."},
        "version": {"description": "Product version as recorded on the scorecard."},
        "bench_date": {"type": ["string", "null"]},
        "bench_version": {"type": ["string", "null"]},
        "environment": {"description": "Bench environment as recorded on the scorecard."},
        "verdict": {"type": ["string", "null"]},
        "checks_total": {"type": "integer"},
        "counts": {"type": "object",
                   "properties": {"pass": {"type": "integer"},
                                  "fail": {"type": "integer"},
                                  "na": {"type": "integer"},
                                  "other": {"type": "integer"}},
                   "required": ["pass", "fail", "na", "other"]},
        "not_tested_checks": {"type": "array",
                              "description": "Names of checks the bench marked not-applicable / not tested."},
        "failed_checks": {"type": "array",
                          "description": "Names of checks the bench marked failed."}},
    "required": ["tool", "version", "bench_date", "bench_version", "environment",
                 "verdict", "checks_total", "counts", "not_tested_checks",
                 "failed_checks"]}

OUTPUT_SCHEMAS = {
    "search_products": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "count": {"type": "integer",
                      "description": "Number of matching products returned."},
            "results": {"type": "array", "items": {
                "type": "object",
                "allOf": [_BRIEF],
                "properties": {
                    "score": {"type": "integer",
                              "description": "Weighted field-match score; higher is a stronger match."},
                    "match_reasons": {"type": "array", "items": {"type": "string"},
                                      "description": "One entry per matched field, naming the matched terms."}},
                "required": ["score", "match_reasons"]}},
            "data_freshness": _FRESHNESS},
        "required": ["query", "count", "results", "data_freshness"],
        "additionalProperties": False},
    "find_solutions": {
        "type": "object",
        "properties": {
            "problem": {"type": "string"},
            "count": {"type": "integer",
                      "description": "Total number of matching products; solutions is capped at 8."},
            "solutions": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"}, "name": {"type": "string"},
                    "score": {"type": "integer"},
                    "fit": {"type": "string",
                            "description": "One-line fit explanation naming the matching fields."},
                    "match_reasons": {"type": "array", "items": {"type": "string"}},
                    "status": {"type": "string"},
                    "certification_badge": {"type": "string",
                                            "description": "Bench verdict, or an explicit not-certified / spec-stage label."},
                    "certified": {"type": "boolean"},
                    "pricing_model": {"type": "string"},
                    "top_capabilities": {"type": "array", "items": {"type": "string"},
                                         "description": "Up to the product's first three capabilities."}},
                "required": ["id", "name", "score", "fit", "match_reasons", "status",
                             "certification_badge", "certified", "pricing_model",
                             "top_capabilities"]}},
            "data_freshness": _FRESHNESS},
        "required": ["problem", "count", "solutions", "data_freshness"],
        "additionalProperties": False},
    "get_product": {
        "type": "object",
        "properties": {
            "product": {
                "type": "object",
                "description": "The full catalog entry for the product, copied from the catalog record, plus live_state_note, install_plan, and honesty_note added by this tool. Catalog entries may carry further record fields beyond those listed here.",
                "properties": {
                    "id": {"type": "string"}, "name": {"type": "string"},
                    "vendor": {"type": "string"}, "tagline": {"type": "string"},
                    "status": {"type": "string"},
                    "pricing_model": {"type": "string"},
                    "listing_class": {"type": "string"},
                    "categories": {"type": "array", "items": {"type": "string"}},
                    "platforms": {"type": "array", "items": {"type": "string"}},
                    "capabilities": {"type": "array", "items": {"type": "string"}},
                    "problem_statements": {"type": "array", "items": {"type": "string"}},
                    "tools": {"type": "array", "items": {"type": "string"}},
                    "source_refs": {"type": "array", "items": {"type": "string"}},
                    "certification": {
                        "type": "object",
                        "properties": {
                            "bench_verdict": {"type": ["string", "null"]},
                            "certified": {"type": "boolean"},
                            "certified_scope": {"type": ["string", "null"]},
                            "not_tested": {"type": ["array", "null"],
                                           "items": {"type": "string"},
                                           "description": "What the bench did not cover; null on a small number of records."},
                            "scorecard_ref": {"type": ["string", "null"]},
                            "live_state_note": {"type": ["string", "null"]}},
                        "required": ["bench_verdict", "certified"]},
                    "live_state_note": {"type": ["string", "null"],
                                        "description": "The certification block's live-state note, surfaced at product level."},
                    "install_plan": {
                        "type": "object",
                        "properties": {"status": {"type": "string"},
                                       "note": {"type": "string"}},
                        "required": ["status", "note"]},
                    "honesty_note": {"type": "string"}},
                "required": ["id", "name", "vendor", "tagline", "status",
                             "pricing_model", "categories", "platforms",
                             "capabilities", "problem_statements", "tools",
                             "certification", "live_state_note", "install_plan",
                             "honesty_note"]},
            "data_freshness": _FRESHNESS},
        "required": ["product", "data_freshness"],
        "additionalProperties": False},
    "compare_products": {
        "type": "object",
        "properties": {
            "comparison": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"}, "name": {"type": "string"},
                    "status": {"type": "string"},
                    "pricing_model": {"type": "string"},
                    "certification": {"type": "string",
                                      "description": "Bench verdict text, or 'none on record'."},
                    "certified": {"type": "boolean"},
                    "certified_scope": {"type": ["string", "null"]},
                    "platforms": {"type": "array", "items": {"type": "string"}},
                    "categories": {"type": "array", "items": {"type": "string"}},
                    "capability_count": {"type": "integer"},
                    "tools": {"type": "array", "items": {"type": "string"}}},
                "required": ["id", "name", "status", "pricing_model", "certification",
                             "certified", "certified_scope", "platforms", "categories",
                             "capability_count", "tools"]}},
            "data_freshness": _FRESHNESS},
        "required": ["comparison", "data_freshness"],
        "additionalProperties": False},
    "get_certification": {
        "type": "object",
        "properties": {
            "id": {"type": "string"}, "name": {"type": "string"},
            "status": {"type": "string"},
            "bench_verdict": {"type": ["string", "null"]},
            "certified": {"type": "boolean"},
            "certified_scope": {"type": ["string", "null"]},
            "scorecard_ref": {"type": ["string", "null"]},
            "not_tested": {"type": ["array", "null"], "items": {"type": "string"}},
            "certification_status": {"type": "string",
                                     "description": "Either the on-record verdict statement or an explicit NOT YET CERTIFIED statement."},
            "scorecard_summary": {"anyOf": [_SCORECARD_SUMMARY, {"type": "null"}],
                                  "description": "Scorecard summary when a verdict is on record; null when not yet certified."},
            "data_freshness": _FRESHNESS},
        "required": ["id", "name", "status", "bench_verdict", "certified",
                     "certified_scope", "scorecard_ref", "not_tested",
                     "certification_status", "scorecard_summary", "data_freshness"],
        "additionalProperties": False},
    "list_categories": {
        "type": "object",
        "properties": {
            "categories": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "total": {"type": "integer"},
                    "by_status": {"type": "object",
                                  "additionalProperties": {"type": "integer"},
                                  "description": "Product counts keyed by status."},
                    "products": {"type": "array", "items": {"type": "string"}}},
                "required": ["category", "total", "by_status", "products"]}},
            "product_total": {"type": "integer"},
            "data_freshness": _FRESHNESS},
        "required": ["categories", "product_total", "data_freshness"],
        "additionalProperties": False},
}


def tool_list():
    return [{"name": name,
             "title": TITLES[name],
             "description": desc,
             "inputSchema": {"type": "object", "properties": props, "required": req},
             "outputSchema": OUTPUT_SCHEMAS[name],
             "annotations": {"title": TITLES[name], "readOnlyHint": True,
                             "destructiveHint": False, "idempotentHint": True,
                             "openWorldHint": False}}
            for name, (_, desc, props, req) in TOOLS.items()]


def handle(req: dict):
    method, rid = req.get("method", ""), req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": req.get("params", {}).get("protocolVersion", "2025-03-26"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "eclipse-bazaar", "version": __version__}}}
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
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32602, "message": "MALFORMED_CONTAINER: argument \'request\'"}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
