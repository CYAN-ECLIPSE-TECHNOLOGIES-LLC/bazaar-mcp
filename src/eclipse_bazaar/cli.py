# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""`bazaar` command line — terminal face of the eclipse-bazaar SDK.

  bazaar search <query> [--category C] [--refresh] [--json]
  bazaar product <id> [--json]
  bazaar categories [--json]
  bazaar check [--config PATH ...] [--corpus PATH] [--refresh-corpus]
               [--out PATH] [--json]
  bazaar version

`check` prints the config files it is about to read *before* reading
them, and its report carries counts per class — never an aggregate
score (see eclipse_bazaar.check for the Phase-1 fences).
"""
import argparse
import json
import sys

from ._version import __version__
from .check import run_check
from .client import Bazaar
from .configparse import default_config_paths


def _emit(obj, as_json, render):
    if as_json:
        print(json.dumps(obj, indent=1))
    else:
        print(render(obj))


def _render_search(res):
    lines = [f"{res['count']} result(s) for {res['query']!r}:"]
    for h in res["results"]:
        cert = h["certification"]
        badge = cert["bench_verdict"] or "no verdict on record"
        lines.append(f"  {h['id']} — {h['name']} [{h['status']}] "
                     f"({badge})")
        lines.append(f"    {h['tagline']}")
        for r in h["match_reasons"]:
            lines.append(f"    · {r}")
    return "\n".join(lines)


def _render_product(res):
    p = res["product"]
    c = p["certification"]
    lines = [f"{p['name']} ({p['id']}) — {p['status']}",
             f"  {p['tagline']}",
             f"  pricing: {p['pricing_model']}",
             f"  categories: {', '.join(p['categories'])}",
             f"  certification: {c['bench_verdict'] or 'NOT YET CERTIFIED'}",
             "  capabilities:"]
    lines += [f"    - {cap}" for cap in p["capabilities"]]
    if c.get("not_tested"):
        lines.append("  not tested:")
        lines += [f"    - {n}" for n in c["not_tested"]]
    return "\n".join(lines)


def _render_categories(res):
    lines = [f"{res['product_total']} products in "
             f"{len(res['categories'])} categories:"]
    for c in res["categories"]:
        by = ", ".join(f"{k}={v}" for k, v in sorted(c["by_status"].items()))
        lines.append(f"  {c['category']}: {c['total']} ({by})")
    return "\n".join(lines)


def _render_check(rep):
    lines = [f"Corpus: {rep['corpus']['records']} listing records "
             f"({rep['corpus']['source']}, sha256 "
             f"{(rep['corpus']['sha256'] or 'n/a')[:16]}…)"]
    for note in rep["file_notes"]:
        lines.append(f"  ! {note['config_file']}: {note['error']}")
    current = None
    for e in rep["entries"]:
        if e["config_file"] != current:
            current = e["config_file"]
            lines.append(f"\n{current}:")
        ident = e["identity"]
        idtxt = "—" if ident is None else \
            f"{ident['kind']}:{ident['name']}" + \
            (f"@{ident['pin']}" if ident.get("pin") else "")
        lines.append(f"  {e['config_name']:<28} {e['class']:<13} {idtxt}")
        if e["listing"]:
            li = e["listing"]
            verdict = li["bench_verdict"] or "no Tier-2 verdict"
            lines.append(f"      -> {li['name']} [{li['status']}] — {verdict}")
        if e["drift"]:
            lines.append(f"      drift: {e['drift']['note']}")
        if e["reason"] and e["class"] in ("UNRESOLVABLE",):
            lines.append(f"      reason: {e['reason']}")
    s = rep["summary"]
    lines.append("\nSummary: " + " · ".join(f"{k} {v}" for k, v in s.items()))
    lines += [f"Note: {n}" for n in rep["notes"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="bazaar",
        description="Eclipse Bazaar — Cyan Eclipse Technologies' catalog "
                    "of tested MCP products: search it, inspect listings, "
                    "and check your MCP client configs against it.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="keyword search over the catalog")
    p.add_argument("query")
    p.add_argument("--category", default=None)
    p.add_argument("--refresh", action="store_true",
                   help="refresh the catalog (one bulk HTTPS fetch) first")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("product", help="full listing for one product id")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("categories", help="catalog categories + counts")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("check", help="classify your configured MCP servers "
                                     "against the Bazaar corpus (phase 1)")
    p.add_argument("--config", action="append", default=None,
                   metavar="PATH", help="config file (repeatable); default: "
                                        "discover known client locations")
    p.add_argument("--corpus", default=None, metavar="PATH",
                   help="local corpus.jsonl (default: bundled snapshot)")
    p.add_argument("--refresh-corpus", action="store_true",
                   help="download the current corpus + manifest and verify "
                        "its sha256 before use")
    p.add_argument("--out", default=None, metavar="PATH",
                   help="also write the JSON report to this path")
    p.add_argument("--json", action="store_true")

    sub.add_parser("version", help="print the package version")

    args = ap.parse_args(argv)

    if args.cmd == "version":
        print(__version__)
        return 0
    if args.cmd == "search":
        bz = Bazaar(refresh=args.refresh)
        _emit(bz.search(args.query, args.category), args.json, _render_search)
        return 0
    if args.cmd == "product":
        _emit(Bazaar().get_listing(args.id), args.json, _render_product)
        return 0
    if args.cmd == "categories":
        _emit(Bazaar().categories(), args.json, _render_categories)
        return 0
    if args.cmd == "check":
        paths = args.config
        if not paths:
            found = default_config_paths()
            print("Config files to read (discovered client locations):",
                  file=sys.stderr)
            for fp in found:
                print(f"  {fp}", file=sys.stderr)
            if not found:
                print("  (none found — pass --config PATH)", file=sys.stderr)
                return 2
            paths = [str(fp) for fp in found]
        rep = run_check(config_paths=paths, corpus_path=args.corpus,
                        refresh_corpus=args.refresh_corpus)
        if args.out:
            from pathlib import Path
            Path(args.out).write_text(json.dumps(rep, indent=1) + "\n")
        _emit(rep, args.json, _render_check)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
