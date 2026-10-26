#!/usr/bin/env python3
# Eclipse Bazaar MCP — gate A3 two-system version law.
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""server.json is the single source of truth for the version. The
Registry version, the VERSION file (pyproject dynamic version), and
the runtime __version__ must agree — drift here is the ecosystem's
known failure mode (directories keep serving the stale version)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eclipse_bazaar import __version__  # noqa: E402


class VersionDrift(unittest.TestCase):
    def test_all_version_surfaces_agree(self):
        server_json = json.loads((ROOT / "server.json").read_text())
        canonical = server_json["version"]
        self.assertEqual((ROOT / "VERSION").read_text().strip(), canonical)
        self.assertEqual(__version__, canonical)
        # the pypi package entry inside server.json carries it too
        pypi = [p for p in server_json["packages"]
                if p.get("registryType") == "pypi"]
        self.assertEqual(len(pypi), 1)
        self.assertEqual(pypi[0]["identifier"], "eclipse-bazaar")
        self.assertEqual(pypi[0]["version"], canonical)

    def test_pyproject_version_is_dynamic_from_version_file(self):
        text = (ROOT / "pyproject.toml").read_text()
        self.assertIn('dynamic = ["version"]', text)
        self.assertIn('version = { file = "VERSION" }', text)
        self.assertIn('name = "eclipse-bazaar"', text)

    def test_installed_metadata_when_available(self):
        try:
            from importlib.metadata import version
            installed = version("eclipse-bazaar")
        except Exception:
            self.skipTest("eclipse-bazaar not installed in this environment")
        canonical = json.loads((ROOT / "server.json").read_text())["version"]
        self.assertEqual(installed, canonical)


if __name__ == "__main__":
    unittest.main()
