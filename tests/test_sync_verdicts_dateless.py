#!/usr/bin/env python3
# Eclipse Bazaar MCP — regression: dateless scorecards (Friction fnd-0003)
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""Regression for the Steward sync_verdicts.py dateless-card crash
(Friction fnd-0003; Verity campaign-20261026-f3-fixverify item 3a).

Replicates the f3 staging shapes with synthetic cards (the staging
files themselves are NOT imported):

  1. neither-field pair — two same-tool cards carrying NEITHER
     bench_date NOR date NOR benched_at. Pre-fix: the first stored
     bench_date None and the second crashed build_ledger with
     TypeError ('<=' str vs NoneType) at the (date, seq) compare.
     Post-fix: the filename date is the final fallback; newest wins.
  2. single dateless card — stored bench_date must be the filename
     date, never null (the silent landmine shape).
  3. disagreeing-fields pair — a card whose bench_date field differs
     from its filename date: the field wins the precedence chain
     (bench_date -> date -> benched_at -> filename date), for both
     the stored value and the newest-card compare.
  4. non-string date field — a card whose bench_date is an int still
     resolves dateless after the chain: it is skipped with a printed
     warning naming the file (a named outcome, not a crash, not a
     silent null).
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "sync_verdicts", HERE.parent / "sync_verdicts.py")
sv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sv)


def card(tool, verdict, **fields):
    c = {"tool": tool, "verdict": verdict,
         "checks": [{"verdict": "pass"}, {"verdict": "pass"}]}
    c.update(fields)
    return c


class DatelessCardRegression(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.results = Path(self._tmp.name)
        self._orig_results = sv.RESULTS
        sv.RESULTS = self.results

    def tearDown(self):
        sv.RESULTS = self._orig_results
        self._tmp.cleanup()

    def write(self, name, obj):
        (self.results / name).write_text(json.dumps(obj))

    def test_neither_field_pair_newest_wins_no_crash(self):
        self.write("widget-mcp-2026-10-25.json",
                   card("widget-mcp", "PARTIAL"))
        self.write("widget-mcp-2026-10-26.json",
                   card("widget-mcp", "FAILED"))
        tools, _ = sv.build_ledger()
        self.assertIn("widget-mcp", tools)
        self.assertEqual(tools["widget-mcp"]["verdict"], "FAILED")
        self.assertEqual(tools["widget-mcp"]["bench_date"], "2026-10-26")
        self.assertEqual(tools["widget-mcp"]["cards_on_record"], 2)

    def test_single_dateless_card_stores_filename_date(self):
        self.write("solo-mcp-2026-10-24.json",
                   card("solo-mcp", "CERTIFIED(local)"))
        tools, _ = sv.build_ledger()
        self.assertEqual(tools["solo-mcp"]["bench_date"], "2026-10-24")

    def test_disagreeing_fields_pair_field_wins(self):
        # Older filename, LATER bench_date field -> field wins compare.
        self.write("disagree-mcp-2026-10-25.json",
                   card("disagree-mcp", "PARTIAL",
                        bench_date="2026-10-27"))
        # Newer filename, EARLIER bench_date field -> loses.
        self.write("disagree-mcp-2026-10-26.json",
                   card("disagree-mcp", "FAILED",
                        bench_date="2026-10-26"))
        tools, _ = sv.build_ledger()
        self.assertEqual(tools["disagree-mcp"]["verdict"], "PARTIAL")
        self.assertEqual(tools["disagree-mcp"]["bench_date"], "2026-10-27")

    def test_benched_at_precedence_over_filename(self):
        self.write("floodshape-mcp-2026-10-25.json",
                   card("floodshape-mcp", "PARTIAL",
                        benched_at="2026-10-25"))
        tools, _ = sv.build_ledger()
        self.assertEqual(tools["floodshape-mcp"]["bench_date"],
                         "2026-10-25")

    def test_nonstring_date_field_skips_with_named_warning(self):
        self.write("broken-mcp-2026-10-25.json",
                   card("broken-mcp", "PARTIAL", bench_date=20261025))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            tools, _ = sv.build_ledger()
        self.assertNotIn("broken-mcp", tools)
        self.assertIn("broken-mcp-2026-10-25.json", out.getvalue())
        self.assertIn("WARN", out.getvalue())


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))

# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
