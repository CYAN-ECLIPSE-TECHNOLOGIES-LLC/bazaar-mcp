#!/usr/bin/env python3
# Eclipse Bazaar MCP — regression: impossible filename dates
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""Regression for the Steward sync_verdicts.py invalid-filename-date
defect (Friction fnd-0003 FIX_VERIFIED replay, fresh shape F4).

A shape-valid but impossible filename date (e.g. 2026-13-40) matched
CARD_RE, was stored verbatim as bench_date via the filename fallback,
and WON the lexicographic (date, seq) compare over a real 2026-10-26
card — a malformed filename could displace a standing verdict. The
checker had no date parser. Post-fix: the filename date is validated
as a real calendar date (strict strptime) at ledger build; an invalid
one skips the card with a printed warning naming the file — never
stored, never compared. Same law on the Attest rebench-c12 remap path.

Shapes:
  1. invalid-date card alone — skipped, warning names the file.
  2. invalid-date card paired vs a real card — the real card stands.
  3. Feb-29 leap/non-leap pair — 2024-02-29 (leap) is a real date and
     stands; 2026-02-29 (non-leap) is impossible, skipped, and cannot
     displace it despite sorting later lexicographically.
  4. Attest rebench-c12 remap with an impossible date — skipped with
     warning; the valid remap path is unchanged (rebench still wins).
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


class InvalidFilenameDateRegression(unittest.TestCase):
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

    def build(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            tools, _ = sv.build_ledger()
        return tools, out.getvalue()

    def test_invalid_date_alone_skipped_with_named_warning(self):
        self.write("widget-mcp-2026-13-40.json",
                   card("widget-mcp", "CERTIFIED(local)"))
        tools, out = self.build()
        self.assertNotIn("widget-mcp", tools)
        self.assertIn("WARN", out)
        self.assertIn("widget-mcp-2026-13-40.json", out)

    def test_invalid_date_paired_real_card_stands(self):
        # F4 shape byte-for-byte: 2026-13-40 sorts AFTER 2026-10-26
        # lexicographically, so pre-fix the malformed card displaced
        # the standing verdict.
        self.write("widget-mcp-2026-10-26.json",
                   card("widget-mcp", "CERTIFIED(local)"))
        self.write("widget-mcp-2026-13-40.json",
                   card("widget-mcp", "FAILED"))
        tools, out = self.build()
        self.assertEqual(tools["widget-mcp"]["verdict"],
                         "CERTIFIED(local)")
        self.assertEqual(tools["widget-mcp"]["bench_date"], "2026-10-26")
        self.assertEqual(tools["widget-mcp"]["cards_on_record"], 1)
        self.assertIn("widget-mcp-2026-13-40.json", out)

    def test_feb29_leap_valid_nonleap_skipped(self):
        # 2024 is a leap year: 2024-02-29 is a real date, stands.
        self.write("leap-mcp-2024-02-29.json",
                   card("leap-mcp", "CERTIFIED(local)"))
        # 2026 is not: 2026-02-29 is impossible. It sorts after the
        # leap card, so pre-fix it would have displaced it.
        self.write("leap-mcp-2026-02-29.json",
                   card("leap-mcp", "FAILED"))
        tools, out = self.build()
        self.assertEqual(tools["leap-mcp"]["verdict"], "CERTIFIED(local)")
        self.assertEqual(tools["leap-mcp"]["bench_date"], "2024-02-29")
        self.assertEqual(tools["leap-mcp"]["cards_on_record"], 1)
        self.assertIn("leap-mcp-2026-02-29.json", out)

    def test_attest_remap_invalid_date_skipped(self):
        self.write("attestshape-mcp-2026-10-26.json",
                   card("attestshape-mcp", "FAILED"))
        self.write("attestshape-mcp-rebench-c12-2026-13-40.json",
                   card("attestshape-mcp", "CERTIFIED(local)"))
        tools, out = self.build()
        self.assertEqual(tools["attestshape-mcp"]["verdict"], "FAILED")
        self.assertEqual(tools["attestshape-mcp"]["cards_on_record"], 1)
        self.assertIn("attestshape-mcp-rebench-c12-2026-13-40.json", out)

    def test_attest_remap_valid_date_unchanged(self):
        self.write("attestshape-mcp-2026-10-26.json",
                   card("attestshape-mcp", "FAILED"))
        self.write("attestshape-mcp-rebench-c12-2026-10-26.json",
                   card("attestshape-mcp", "CERTIFIED(local)"))
        tools, _ = self.build()
        self.assertEqual(tools["attestshape-mcp"]["verdict"],
                         "CERTIFIED(local)")
        self.assertEqual(tools["attestshape-mcp"]["cards_on_record"], 2)


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))

# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
