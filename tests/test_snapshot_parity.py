#!/usr/bin/env python3
# Eclipse Bazaar MCP — gate A1 / A-M1 parity.
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""A1: a packaged run must return identical answers to a repo run on
the same catalog build. Two halves:
  1. every verdict snapshot summary equals the summary computed live
     from the referenced Test Bench card (same code path both sides);
  2. the server, run from a clean copied tree with NO test-bench
     sibling, answers get_certification / search identically to the
     in-repo server (parsed JSON; only data_freshness.served_from may
     differ — it honestly reports where the data came from).
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eclipse_bazaar import catalog as cat_mod  # noqa: E402


def run_server(cwd, env_extra, calls):
    reqs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "parity", "version": "0"}}}]
    for i, (name, args) in enumerate(calls, start=2):
        reqs.append({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                     "params": {"name": name, "arguments": args}})
    import os
    env = dict(os.environ)
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-m", "eclipse_bazaar.mcp_server"],
        input="\n".join(json.dumps(r) for r in reqs),
        capture_output=True, text=True, cwd=cwd, env=env, timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = {}
    for line in proc.stdout.splitlines():
        d = json.loads(line)
        if d.get("id", 0) >= 2:
            out[d["id"]] = json.loads(d["result"]["content"][0]["text"])
    return out


class SnapshotParity(unittest.TestCase):
    def test_snapshot_matches_live_cards(self):
        snap = json.loads(
            (ROOT / "src/eclipse_bazaar/data/verdict_snapshot.json").read_text())
        cat = json.loads((ROOT / "catalog.json").read_text())
        refs = {(p.get("certification") or {}).get("scorecard_ref")
                for p in cat["products"]}
        refs.discard(None)
        self.assertEqual(set(snap["cards"]), refs)
        if not (ROOT.parent / "test-bench").is_dir():
            self.skipTest("test-bench sibling absent (CI checkout) — "
                          "live-card comparison runs in the workspace only")
        for ref, rec in snap["cards"].items():
            raw = (ROOT.parent / ref).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), rec["sha256"],
                             f"snapshot stale for {ref} — rerun sync_package_data")
            live = cat_mod.summarize_card(json.loads(raw))
            self.assertEqual(live, rec["summary"], f"summary drift for {ref}")

    def test_bundled_catalog_is_current_copy(self):
        root_cat = (ROOT / "catalog.json").read_bytes()
        bundled = (ROOT / "src/eclipse_bazaar/data/catalog.json").read_bytes()
        self.assertEqual(hashlib.sha256(root_cat).hexdigest(),
                         hashlib.sha256(bundled).hexdigest())

    def test_clean_tree_server_parity(self):
        tmp = Path(tempfile.mkdtemp(prefix="bazaar-parity-"))
        clean = tmp / "pkg"
        shutil.copytree(ROOT / "src", clean / "src")
        calls = [("get_certification", {"id": "eclipse-charter-mcp"}),
                 ("get_certification", {"id": "eclipse-agent-wallet-mcp"}),
                 ("get_certification", {"id": "eclipse-stocktake"}),
                 ("search_products", {"query": "certificate renewal ssl"}),
                 ("list_categories", {})]
        repo_out = run_server(ROOT, {"PYTHONPATH": str(ROOT / "src")}, calls)
        clean_out = run_server(clean, {"PYTHONPATH": str(clean / "src")}, calls)
        self.assertEqual(set(repo_out), set(clean_out))
        for rid in repo_out:
            a, b = dict(repo_out[rid]), dict(clean_out[rid])
            fa, fb = a.pop("data_freshness", {}), b.pop("data_freshness", {})
            fa.pop("served_from", None)
            fb.pop("served_from", None)
            self.assertEqual(fa, fb)
            self.assertEqual(a, b, f"response {rid} differs clean vs repo")


if __name__ == "__main__":
    unittest.main()
