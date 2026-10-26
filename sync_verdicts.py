#!/usr/bin/env python3
# Eclipse Bazaar MCP
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
# Single-source verdict sync for Eclipse Bazaar (EB-09).

"""Single-source verdict sync for Eclipse Bazaar (EB-09).

Source of truth: test-bench scorecards in ../test-bench/results/.
Newest card per tool wins: max by (bench_date, run-sequence suffix in
filename — base file = seq 1, -2/-3/.../-11 supersede in order).
Cards from every suite share one sequence per tool+date (scorecard.emit
assigns the suffix), so the newest card overall is the standing verdict,
even when an intermediate card was a control/transport run.

Surfaces checked (and, with --apply, machine-safe fields updated):
  * catalog.json            certification.bench_verdict / certified /
                            scorecard_ref (+ counts embedded in
                            certified_scope prose are verified, never
                            rewritten — prose stays human-owned)
  * product manifests       */bazaar-manifest.json bench block
  * storefront              ../eclipse-bazaar-site/index.html bench lines
  * README.md               catalog table in this repo

Dogfood logs (results/*-dogfood-*.md) are NOT scorecards: a log's
"After this run:" label is recorded in the ledger as a live-state
annotation, and surfaces must mention the dogfood run — the bench
verdict itself never changes because of a dogfood log.

Usage:
  python3 sync_verdicts.py [--apply] [--exclude <product-id> ...]
  --check (default) prints drift and exits 1 if any drift is found.
  --apply fixes machine-safe fields, then re-checks.
  verdict-ledger.json is (re)written on every run.
Excluded ids are reported as SKIPPED, never read for drift, never edited
(used when a parallel run owns a product's sync).
"""
import json
import re
import sys
from pathlib import Path

BAZAAR = Path(__file__).resolve().parent
CE = BAZAAR.parent
RESULTS = CE / "test-bench" / "results"
CATALOG = BAZAAR / "catalog.json"
README = BAZAAR / "README.md"
STOREFRONT = CE / "eclipse-bazaar-site" / "index.html"
LEDGER_OUT = BAZAAR / "verdict-ledger.json"
CARD_RE = re.compile(r"^(.+)-(\d{4}-\d{2}-\d{2})(?:-(\d+))?"
                     r"(?:-rebench-fixround(\d+))?(?:-r(\d+))?\.json$")
DOGFOOD_RE = re.compile(r"^(.+)-dogfood-(\d{4}-\d{2}-\d{2})\.md$")


def dump_compact(obj):
    """House style for catalog/manifests: one-line, sorted keys, UTF-8."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def counts(checks):
    c = {"pass": 0, "fail": 0, "na": 0, "untestable": 0}
    if isinstance(checks, dict):
        vals = list(checks.values())
        if vals and isinstance(vals[0], dict) and "verdict" in vals[0]:
            # Card-format variant (Covenant scoped re-bench, 2026-10-25):
            # lines ride in a "per_line" mapping of name ->
            # {"verdict": "PASS"/...} instead of a "checks" list. Tally
            # like a list card. Checker normalization, publish pass 8 —
            # scorecards untouched, same treatment as the Charter fix.
            for v in vals:
                vv = str(v.get("verdict", "")).lower()
                if vv in c:
                    c[vv] += 1
            c["total"] = len(vals)
            return c
        # Card-format variant (Charter suite): checks are a mapping of
        # name -> {"pass": bool, "detail": ...} instead of a list of
        # {"verdict": ...}. Checker normalization, publish pass 7 —
        # same treatment as the friction qualifier fix; cards untouched.
        c["pass"] = sum(1 for v in checks.values() if v.get("pass"))
        c["total"] = len(checks)
        c["fail"] = c["total"] - c["pass"]
        return c
    for ch in checks:
        if ch.get("verdict") in c:
            c[ch["verdict"]] += 1
    c["total"] = len(checks)
    return c


def build_ledger():
    tools, on_record = {}, {}
    for p in sorted(RESULTS.glob("*.json")):
        m = CARD_RE.match(p.name)
        if not m:
            continue
        tool, date = m.group(1), m.group(2)
        # Card-format variant (BC scoped re-bench, 2026-10-25): a fix-round
        # re-bench card carries a "-rebench-fixround<N>" suffix after the
        # date instead of a run-sequence number; it supersedes the same-date
        # base card, so it sorts as seq 100+N. Checker normalization,
        # Rook top-up 2026-10-26 — scorecards untouched, same treatment as
        # the friction qualifier and Charter format fixes.
        seq = int(m.group(3) or 1) + 100 * int(m.group(4) or 0)
        # Card-format variant (Strata scoped re-bench, 2026-10-25): the
        # fix-round cards carry a "-r<N>" run suffix instead of a run
        # sequence (…-2026-10-25.json = bench 1, -r2 = scoped re-bench,
        # -r3 = second scoped re-bench). Each r-run supersedes the
        # same-date cards before it, so it sorts as seq N (the base card
        # is seq 1, consistent with the -N band). Checker normalization,
        # Rook Strata listing 2026-10-26 — scorecards untouched, same
        # treatment as the BC fixround fix above.
        if m.group(5):
            seq = int(m.group(5))
        sc = json.loads(p.read_text())
        # Card-format variant (Charter suite): the tool id rides in a
        # "product" field instead of "tool". Checker normalization,
        # publish pass 7; the scorecard itself is untouched.
        # Card-format variant (Covenant suite): "product" carries the
        # DISPLAY name ("Eclipse Covenant MCP") and the id rides in a
        # "slug" field. Accept the slug as identity. Checker
        # normalization, publish pass 8; scorecards untouched.
        if tool not in (sc.get("tool"), sc.get("product"), sc.get("slug")):
            # Card-format variant (Attest suite): scoped re-bench cards
            # are named "<tool>-rebench-c12-<date>" and
            # "<tool>-rebench2-c12-<date>" — the marker rides BEFORE the
            # date, so CARD_RE reads it as part of the tool id and the
            # identity check would skip the card entirely, leaving the
            # FAILED base card as the standing verdict. Re-map to the
            # card's own tool id with a sequence above the same-date
            # base card (rebench = 60, rebench2 = 62; below the
            # -rebench-fixround 100+ band). Checker normalization,
            # publish pass 9 — scorecards untouched, same treatment as
            # the Charter/BC/Covenant format fixes.
            am = re.match(r"^(.+)-rebench(\d*)-c12-"
                          r"(\d{4}-\d{2}-\d{2})\.json$", p.name)
            if am and am.group(1) == sc.get("tool"):
                tool, date = am.group(1), am.group(3)
                seq = 60 + 2 * int(am.group(2) or 0)
            else:
                continue
        on_record[tool] = on_record.get(tool, 0) + 1
        prev = tools.get(tool)
        if prev and (date, seq) <= (prev["bench_date"], prev["seq"]):
            continue
        _v = sc["verdict"]
        _sl_str = sc.get("scope_label") \
            if isinstance(sc.get("scope_label"), str) else None
        if _v == "CERTIFIED" and _sl_str and _sl_str.startswith("CERTIFIED("):
            # Card-format variant (Meridian re-bench, 2026-10-26): the
            # card's own string scope_label IS the full standing verdict
            # ("CERTIFIED(local, synthetic scope)") while its qualifier
            # field carries longer prose. The bench's printed label wins.
            # Checker normalization, publish pass 8 — scorecards
            # untouched, same treatment as the friction qualifier fix.
            _v = _sl_str
        elif _v == "CERTIFIED" and sc.get("qualifier"):
            # Card-format variant: verdict and qualifier emitted as
            # separate fields (friction re-bench card, 2026-10-25). Compose
            # the standing verdict so the ledger's certified test and every
            # surface compare against the same string the card's own
            # certification text states. Checker normalization, publish
            # pass 6 top-up (friction), same treatment as the pass-2 fix.
            _v = f"CERTIFIED({sc['qualifier']})"
        elif _v == "CERTIFIED" and _sl_str:
            # Card-format variant (Covenant scoped re-bench -4,
            # 2026-10-25): no qualifier field; the string scope_label
            # carries the bare scope ("local/simulator") and the card's
            # verdict_qualifier + manifest instruction both state the
            # composed form. Checker normalization, publish pass 8.
            _v = f"CERTIFIED({_sl_str})"
        # Card-format variant (Charter suite): bench_date rides in "date",
        # environment/qualifier in scope_label.scope, and the bench
        # identity in bench_agent. Checker normalization, publish pass 7.
        _sl = sc.get("scope_label")
        _scope = _sl.get("scope") if isinstance(_sl, dict) else None
        tools[tool] = {"tool": tool, "verdict": _v,
                       "certified": _v.startswith("CERTIFIED("),
                       "bench_date": sc.get("bench_date") or sc.get("date"),
                       "bench_version": sc.get("bench_version")
                       or sc.get("bench_agent", ""),
                       "environment": sc.get("environment") or _scope,
                       "qualifier": sc.get("qualifier") or _scope
                       or (_sl_str if _sl_str
                           and not _sl_str.startswith("CERTIFIED(")
                           else None),
                       "seq": seq,
                       "counts": counts(sc.get("checks")
                                        or sc.get("per_line") or []),
                       "scorecard_ref": "test-bench/results/" + p.name}
    for tool, entry in tools.items():
        entry["cards_on_record"] = on_record[tool]
    annotations = {}
    for p in sorted(RESULTS.glob("*-dogfood-*.md")):
        m = DOGFOOD_RE.match(p.name)
        if not m:
            continue
        hit = re.search(r"After this run:\s*\*\*(.+?)\*\*", p.read_text())
        annotations[m.group(1)] = {
            "log_ref": "test-bench/results/" + p.name,
            "date": m.group(2),
            "label": hit.group(1) if hit else "(no After-this-run label)"}
    return tools, annotations


def scope_counts(scope):
    m = re.search(r"(\d+) pass, (\d+) na of (\d+) checks", scope or "")
    return tuple(int(x) for x in m.groups()) if m else None


def main():
    apply_mode = "--apply" in sys.argv
    exclude = set()
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--exclude" and i + 1 < len(args):
            exclude.add(args[i + 1])
    tools, annotations = build_ledger()
    catalog = json.loads(CATALOG.read_text())
    products = {p["id"]: p for p in catalog["products"]}
    ledger = {"source_of_truth": "test-bench/results/*.json (newest card "
              "per tool by bench_date + run-sequence suffix)",
              "dogfood_rule": "dogfood logs annotate live state only; "
              "they never change a bench verdict",
              "tools": {t: tools[t] for t in sorted(tools)},
              "live_state_annotations": annotations,
              "unmapped_tools": sorted(t for t in tools
                                       if t not in products)}
    LEDGER_OUT.write_text(json.dumps(ledger, indent=1) + "\n")

    drift, warns, skipped = [], [], []

    def rep(pid, surface, msg):
        (skipped if pid in exclude else drift).append(
            f"{'SKIP' if pid in exclude else 'DRIFT'} {pid} [{surface}] {msg}")

    # ---- catalog.json -------------------------------------------------
    for pid, p in products.items():
        cert = p.get("certification", {})
        led = tools.get(pid)
        if pid in exclude:
            rep(pid, "catalog", "excluded this run (parallel owner)")
            continue
        if led is None:
            if cert.get("bench_verdict") is not None or cert.get("certified"):
                rep(pid, "catalog", "claims a verdict but no scorecard exists")
            continue
        if cert.get("bench_verdict") != led["verdict"]:
            rep(pid, "catalog", f"bench_verdict={cert.get('bench_verdict')!r} "
                                f"!= ledger {led['verdict']!r}")
        if cert.get("certified") != led["certified"]:
            rep(pid, "catalog", f"certified={cert.get('certified')} "
                                f"!= ledger {led['certified']}")
        if cert.get("scorecard_ref") != led["scorecard_ref"]:
            rep(pid, "catalog", f"scorecard_ref={cert.get('scorecard_ref')!r} "
                                f"!= ledger {led['scorecard_ref']!r}")
        sc_counts = scope_counts(cert.get("certified_scope"))
        if led["certified"] and sc_counts is not None:
            want = (led["counts"]["pass"], led["counts"]["na"],
                    led["counts"]["total"])
            if sc_counts != want:
                rep(pid, "catalog", f"certified_scope counts {sc_counts} "
                                    f"!= card counts {want} (prose: human fix)")
        ann = annotations.get(pid)
        if ann and "dogfood" not in json.dumps(cert).lower():
            rep(pid, "catalog", f"live-state annotation missing: {ann['label']} "
                                f"({ann['log_ref']})")
        if apply_mode and led:
            cert["bench_verdict"] = led["verdict"]
            cert["certified"] = led["certified"]
            cert["scorecard_ref"] = led["scorecard_ref"]
            refs = p.setdefault("source_refs", [])
            if led["scorecard_ref"] not in refs:
                refs.append(led["scorecard_ref"])
    if apply_mode:
        catalog["verdicts_synced_from"] = "test-bench/results via sync_verdicts.py"
        CATALOG.write_text(dump_compact(catalog))

    # ---- product manifests ---------------------------------------------
    for mf in sorted(CE.glob("*/bazaar-manifest.json")):
        man = json.loads(mf.read_text())
        slug = man.get("slug", "")
        pid = slug if slug in products else slug + "-mcp"
        if pid not in products:
            continue
        bench = man.get("bench", {})
        led = tools.get(pid)
        surface = f"manifest {mf.parent.name}"
        if led is None:
            if bench.get("bench_verdict"):
                rep(pid, surface, "manifest claims verdict, no scorecard")
            continue
        if "bench_verdict" in bench:
            if bench["bench_verdict"] != led["verdict"]:
                rep(pid, surface, f"bench_verdict={bench['bench_verdict']!r} "
                                  f"!= ledger {led['verdict']!r}")
        status = bench.get("status", "")
        if status and led["verdict"] not in status:
            rep(pid, surface, f"bench.status lacks ledger verdict "
                              f"{led['verdict']!r}: {status[:80]!r}")
        if bench.get("scorecard_ref") not in (None, led["scorecard_ref"]):
            rep(pid, surface, f"scorecard_ref={bench['scorecard_ref']!r} "
                              f"!= ledger {led['scorecard_ref']!r}")
        if apply_mode and status.startswith("Bench pending") \
                and pid not in exclude:
            c = led["counts"]
            bench["bench_verdict"] = led["verdict"]
            bench["certified"] = led["certified"]
            bench["scorecard_ref"] = led["scorecard_ref"]
            bench["status"] = (
                f"{led['verdict']} — Eclipse Bazaar Test Bench "
                f"{led['bench_date']}, {c['pass']}/{c['total']} checks pass"
                + (f", {c['na']} na" if c["na"] else "")
                + ". Synced by bazaar-mcp/sync_verdicts.py (EB-09).")
            man["bench"] = bench
            mf.write_text(dump_compact(man))

    # ---- README table ----------------------------------------------------
    # Row assignment by LONGEST name-prefix match on the first cell:
    # "Eclipse Connect" (relay) is a prefix of "Eclipse Connect MCP"
    # (facade) — a first-substring match reads the relay's row for the
    # facade and false-flags drift (checker defect, fixed 2026-10-25,
    # publish pass 2; same treatment as prior bench-suite self-defects).
    readme = README.read_text()
    rows = [ln for ln in readme.splitlines() if ln.strip().startswith("|")]
    def first_cell(ln):
        parts = ln.split("|")
        return parts[1].strip() if len(parts) > 2 else ""
    assigned = {}
    for ln in rows:
        cell = first_cell(ln)
        segments = [seg.strip() for seg in cell.split("·")]
        best = None
        for pid, p in products.items():
            nm = p["name"]
            if cell == nm or cell.startswith(nm + " ") or cell.startswith(nm + " ("):
                if best is None or len(nm) > len(products[best]["name"]):
                    best = pid
        if best is not None:
            assigned.setdefault(best, ln)
        # combined spec row names several products in one cell: assign the
        # same row to each exactly-named segment product as well. Segment
        # matching applies ONLY to multi-segment cells — a single-name cell
        # ("Eclipse Connect") must never satisfy the facade via its short
        # name, or the collision above returns.
        if len(segments) > 1:
            for pid, p in products.items():
                nm = p["name"]
                if nm in segments or nm.replace(" MCP", "") in segments:
                    assigned.setdefault(pid, ln)
    for pid, p in products.items():
        if pid in exclude:
            continue
        led = tools.get(pid)
        row = assigned.get(pid)
        if row is None:
            rep(pid, "readme", "no catalog-table row")
        elif led and led["verdict"] not in row:
            rep(pid, "readme", f"table row lacks ledger verdict "
                               f"{led['verdict']!r}")
        elif led is None and "CERTIFIED" in row:
            rep(pid, "readme", "table row claims CERTIFIED, no scorecard")

    # ---- storefront -------------------------------------------------------
    html = STOREFRONT.read_text()
    blocks = re.split(r"<h3>", html)
    cards = {}
    for b in blocks[1:]:
        name = b.split("</h3>")[0].strip()
        m = re.search(r'bench-line">(.*?)</p>', b, re.S)
        if m:
            cards[name] = re.sub(r"<[^>]+>", "", m.group(1))
    for pid, p in products.items():
        if pid in exclude or p["status"] == "spec":
            continue
        led = tools.get(pid)
        line = cards.get(p["name"])
        if line is None:
            warns.append(f"WARN {pid} [storefront] no card (listing prep "
                         f"is a separate backlog item, not verdict drift)")
            continue
        if led and led["verdict"] not in line:
            rep(pid, "storefront", f"bench line lacks ledger verdict "
                                   f"{led['verdict']!r}: {line.strip()[:90]!r}")
        if led:
            want = f"{led['counts']['pass']}/{led['counts']['total']} checks"
            if want not in line:
                rep(pid, "storefront", f"bench line counts != {want}: "
                                       f"{line.strip()[:90]!r}")
        ann = annotations.get(pid)
        if ann and "dogfood" not in line.lower():
            rep(pid, "storefront", f"live-state annotation missing: "
                                   f"{ann['label']} ({ann['date']})")

    for s in skipped:
        print(s)
    for w in warns:
        print(w)
    for d in drift:
        print(d)
    print(f"ledger: {len(tools)} tools, newest cards -> {LEDGER_OUT.name}; "
          f"drift={len(drift)} warn={len(warns)} skipped={len(skipped)}")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())

# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
