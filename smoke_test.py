#!/usr/bin/env python3
# Eclipse Bazaar MCP
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
# Smoke test for Eclipse Bazaar MCP v0.1.0.

"""Smoke test for Eclipse Bazaar MCP v0.1.0.

Speaks real stdio JSON-RPC to server.py and asserts:
  * initialize / tools/list (exactly the 6 discovery tools)
  * problem-first routing: each canonical problem lands on the right product
  * certification honesty: Wallet = CERTIFIED(sandbox); BidMatrix (spec)
    reports status=spec and NOT certified, never a fabricated verdict
  * every response carries the data_freshness note
Run: python3 smoke_test.py   (exit 0 = all pass)
"""
import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).with_name("server.py")

REQUESTS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "bazaar-smoke", "version": "0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
]
CALLS = [
    (3, "find_solutions", {"problem": "deploy a website to shared hosting"}),
    (4, "find_solutions", {"problem": "is a store ready for SI shopping agents"}),
    (5, "find_solutions", {"problem": "search crypto news and get article text"}),
    (6, "find_solutions", {"problem": "spending limits for agents"}),
    (7, "search_products", {"query": "certificate renewal ssl"}),
    (8, "get_certification", {"id": "eclipse-agent-wallet-mcp"}),
    (9, "get_product", {"id": "bidmatrix-mcp"}),
    (10, "get_certification", {"id": "bidmatrix-mcp"}),
    (11, "compare_products", {"ids": ["hostbridge-mcp", "certbridge-mcp"]}),
    (12, "list_categories", {}),
    (13, "get_certification", {"id": "white-report-mcp"}),
]
for rid, name, args in CALLS:
    REQUESTS.append({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                     "params": {"name": name, "arguments": args}})

proc = subprocess.run(
    [sys.executable, str(SERVER)],
    input="\n".join(json.dumps(r) for r in REQUESTS) + "\n",
    capture_output=True, text=True, timeout=60)
by_id = {}
for line in proc.stdout.splitlines():
    line = line.strip()
    if line:
        msg = json.loads(line)
        if msg.get("id") is not None:
            by_id[msg["id"]] = msg


def payload(rid):
    msg = by_id[rid]
    assert "result" in msg, f"id {rid}: {msg}"
    return json.loads(msg["result"]["content"][0]["text"])


results = []
def check(label, fn):
    try:
        fn()
        results.append((label, "PASS"))
    except AssertionError as e:
        results.append((label, f"FAIL — {e}"))


check("initialize answers with serverInfo eclipse-bazaar 0.1.0", lambda: (
    (_ for _ in ()).throw(AssertionError(by_id[1])) if
    by_id[1]["result"]["serverInfo"] != {"name": "eclipse-bazaar", "version": "0.1.0"}
    else None))

check("tools/list = the 6 discovery tools", lambda: (
    (_ for _ in ()).throw(AssertionError([t["name"] for t in by_id[2]["result"]["tools"]])) if
    sorted(t["name"] for t in by_id[2]["result"]["tools"]) !=
    ["compare_products", "find_solutions", "get_certification",
     "get_product", "list_categories", "search_products"] else None))


def top_is(rid, pid):
    def fn():
        out = payload(rid)
        assert out["count"] >= 1, "no solutions returned"
        top = out["solutions"][0]
        assert top["id"] == pid, f"top = {top['id']}, expected {pid}: {out['solutions'][:3]}"
        assert top["match_reasons"], "missing match_reasons"
        assert out["data_freshness"]["catalog_built"], "missing freshness note"
    return fn


check("problem 'deploy a website to shared hosting' -> HostBridge top",
      top_is(3, "hostbridge-mcp"))
check("problem 'is a store ready for SI shopping agents' -> AgentReady top",
      top_is(4, "agent-ready-mcp"))
check("problem 'search crypto news and get article text' -> White Report MCP top",
      top_is(5, "white-report-mcp"))
check("problem 'spending limits for agents' -> Agent Wallet top",
      top_is(6, "eclipse-agent-wallet-mcp"))


def wallet_cert():
    out = payload(8)
    assert out["bench_verdict"] == "CERTIFIED(sandbox)", out["bench_verdict"]
    assert out["certified"] is True
    s = out["scorecard_summary"]
    assert s and s["counts"]["pass"] == 12 and s["counts"]["na"] == 1, s
    assert s["checks_total"] == 13, s
    assert out["not_tested"], "not_tested must be non-empty"
check("Wallet certification = CERTIFIED(sandbox) w/ scorecard summary", wallet_cert)


def bidmatrix_spec():
    p = payload(9)["product"]
    assert p["status"] == "spec", p["status"]
    assert p["certification"]["certified"] is False
    assert p["certification"]["bench_verdict"] is None
    c = payload(10)
    assert c["certified"] is False and "NOT YET CERTIFIED" in c["certification_status"], c
check("BidMatrix: status=spec, certified=false, explicit not-certified", bidmatrix_spec)


def misc():
    cmp_ = payload(11)["comparison"]
    assert [r["id"] for r in cmp_] == ["hostbridge-mcp", "certbridge-mcp"]
    assert all(r["certification"].startswith("CERTIFIED") for r in cmp_), cmp_
    cats = payload(12)
    assert cats["product_total"] == 56, cats["product_total"]  # 54 + wave-1 completions (Blackbox/Docket), publish pass 4 top-up 2026-10-25
    assert cats["data_freshness"]["catalog_built"] == "2026-10-25"
    wr = payload(13)
    assert wr["bench_verdict"] == "CERTIFIED(live)" and wr["certified"] is True, wr
    sp = payload(7)
    assert sp["count"] >= 1 and sp["results"][0]["match_reasons"], sp
check("compare + categories + WR CERTIFIED(live) honesty + search reasons", misc)


failed = 0
for label, status in results:
    print(f"[{status}] {label}")
    if status.startswith("FAIL"):
        failed += 1
print(f"\n{len(results) - failed}/{len(results)} passed")
sys.exit(1 if failed else 0)

# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
