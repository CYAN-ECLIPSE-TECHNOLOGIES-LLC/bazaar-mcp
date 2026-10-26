#!/usr/bin/env python3
# Eclipse Bazaar — C1 SDK/CLI parity + framework wrapper smoke.
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""The SDK and CLI are plumbing over the same functions the MCP server
runs — these tests pin that: identical search results across all three
surfaces, and wrappers that either work (extra installed) or fail with
the install instruction (extra absent), never silently."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eclipse_bazaar import Bazaar, __version__  # noqa: E402
from eclipse_bazaar import mcp_server  # noqa: E402


def cli(*argv, cwd=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run([sys.executable, "-m", "eclipse_bazaar.cli", *argv],
                          capture_output=True, text=True, cwd=cwd or ROOT,
                          env=env, timeout=60)
    assert proc.returncode == 0, f"{argv}: {proc.stderr}"
    return proc.stdout


class SdkParity(unittest.TestCase):
    def test_search_matches_mcp_tool(self):
        bz = Bazaar()
        sdk = bz.search("certificate renewal ssl")
        mcp = mcp_server.t_search_products(
            {"query": "certificate renewal ssl"})
        self.assertEqual(sdk, mcp)
        self.assertGreater(sdk["count"], 0)
        self.assertTrue(all("match_reasons" in h for h in sdk["results"]))

    def test_listing_and_certification(self):
        bz = Bazaar()
        full = bz.get_listing("eclipse-bazaar-mcp")
        self.assertEqual(full["product"]["id"], "eclipse-bazaar-mcp")
        cert = bz.get_certification("eclipse-bazaar-mcp")
        self.assertEqual(cert["bench_verdict"], "CERTIFIED(local)")
        self.assertIsNotNone(cert["scorecard_summary"])
        cats = bz.categories()
        self.assertEqual(cats["product_total"], 86)

    def test_sdk_check(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {
                "bz": {"command": "uvx", "args": ["eclipse-bazaar"]}}}))
            rep = Bazaar().check(config_paths=[str(cfg)])
        self.assertEqual(rep["summary"]["CERTIFIED"], 1)


class CliSurface(unittest.TestCase):
    def test_version(self):
        self.assertEqual(cli("version").strip(), __version__)

    def test_search_json(self):
        out = json.loads(cli("search", "spending limits", "--json"))
        self.assertGreater(out["count"], 0)
        self.assertEqual(out["results"][0]["id"], "eclipse-agent-wallet-mcp")

    def test_product_and_categories(self):
        out = json.loads(cli("product", "certbridge-mcp", "--json"))
        self.assertEqual(out["product"]["id"], "certbridge-mcp")
        cats = json.loads(cli("categories", "--json"))
        self.assertEqual(cats["product_total"], 86)

    def test_check_json_and_outfile(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {
                "proc": {"command": "uvx",
                         "args": ["eclipse-procure-mcp@0.1.0"]},
                "mystery": {"command": "uvx", "args": ["totally-unknown-mcp"]}}}))
            out_path = Path(td) / "report.json"
            out = json.loads(cli("check", "--config", str(cfg),
                                 "--out", str(out_path), "--json"))
            written = json.loads(out_path.read_text())
        self.assertEqual(out, written)
        self.assertEqual(out["summary"]["CERTIFIED"], 1)
        self.assertEqual(out["summary"]["NOT LISTED"], 1)
        self.assertIsNotNone(out["entries"][0]["drift"])


class Wrappers(unittest.TestCase):
    def test_langchain_wrapper(self):
        try:
            import langchain_core  # noqa: F401
            have = True
        except ImportError:
            have = False
        from eclipse_bazaar.integrations.langchain_tools import make_langchain_tools
        if not have:
            with self.assertRaises(RuntimeError) as cm:
                make_langchain_tools()
            self.assertIn("eclipse-bazaar[langchain]", str(cm.exception))
            return
        tools = make_langchain_tools()
        self.assertEqual([t.name for t in tools],
                         ["bazaar_search", "bazaar_get_listing"])
        out = json.loads(tools[0].invoke({"query": "certificate renewal"}))
        self.assertGreater(out["count"], 0)

    def test_crewai_wrapper(self):
        try:
            import crewai  # noqa: F401
            have = True
        except ImportError:
            have = False
        from eclipse_bazaar.integrations.crewai_tools import make_crewai_tools
        if not have:
            with self.assertRaises(RuntimeError) as cm:
                make_crewai_tools()
            self.assertIn("eclipse-bazaar[crewai]", str(cm.exception))
            return
        tools = make_crewai_tools()
        self.assertEqual([t.name for t in tools],
                         ["bazaar_search", "bazaar_get_listing"])


if __name__ == "__main__":
    unittest.main()
