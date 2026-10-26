#!/usr/bin/env python3
# Eclipse Bazaar — C-M1 correctness matrix + fences (gate §7, §5.2, S1–S3).
# Copyright © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""M1 for `bazaar check` (Phase 1), all on our own estate:
  * a generated config references all 86 catalog listings across the
    shape matrix (uvx / npx / docker image / local path / bare command)
    — every entry must classify to its listing (CERTIFIED when a Tier-2
    verdict is on record, else LISTED);
  * planted traps: a typosquat name -> NOT LISTED; a stale version pin
    -> drift flag against the listed version; a shell-wrapped entry ->
    UNRESOLVABLE with a reason;
  * canary secrets planted in env, in a `docker -e` arg, and in a
    remote entry's headers must appear in NO output, and the check must
    make NO network requests doing it (urlopen is trapped);
  * the Phase-1 vocabulary is closed: every emitted class is one of the
    four, and the later-phase class tokens do not exist in the shipped
    code, the PyPI readme, or any check output;
  * the fence: check never executes a configured server (a marker-file
    command must leave no marker) and the module imports no subprocess.
"""
import json
import os
import re
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eclipse_bazaar import catalog as catalog_mod  # noqa: E402
from eclipse_bazaar import check as check_mod  # noqa: E402
from eclipse_bazaar import cli as cli_mod  # noqa: E402
from eclipse_bazaar import configparse  # noqa: E402

# Built dynamically so this test file itself stays free of the tokens.
FORBIDDEN = ["SCR" + "EENED", "CHE" + "CKED"]
CANARIES = ["CANARY-ENV-7f3a9d21", "CANARY-DOCKER-91bc44", "CANARY-HDR-55e1aa"]


def corpus_records():
    raw = (ROOT / "src/eclipse_bazaar/data/corpus.jsonl").read_text()
    return [json.loads(l) for l in raw.splitlines() if l.strip()]


def expected_class(rec):
    return check_mod.CERTIFIED if (rec["certified"] and rec["bench_verdict"]) \
        else check_mod.LISTED


def shape_entry(i, rec):
    """One config entry reaching rec's listing, shape rotating by i."""
    repo = next((x for x in rec["identities"]
                 if x.startswith("ghcr.io/")), None)
    base = repo.rsplit("/", 1)[-1] if repo else rec["id"]
    shape = i % 5
    if shape == 0:
        return {"command": "uvx", "args": [rec["id"]]}
    if shape == 1:
        return {"command": "npx", "args": ["-y", base]}
    if shape == 2 and repo:
        return {"command": "docker",
                "args": ["run", "-i", "--rm", repo + ":latest"]}
    if shape == 3:
        return {"command": "python3", "args": [f"/opt/mcp/{base}/server.py"]}
    if shape == 4:
        return {"command": f"/usr/local/bin/{base}", "args": []}
    return {"command": "uvx", "args": [rec["id"]]}


class ShapeMatrix(unittest.TestCase):
    def test_all_86_listings_classify(self):
        records = corpus_records()
        self.assertEqual(len(records), 86)
        servers = {}
        expect = {}
        for i, rec in enumerate(records):
            name = f"s{i:02d}-{rec['id']}"
            servers[name] = shape_entry(i, rec)
            expect[name] = expected_class(rec)
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps({"mcpServers": servers}))
            rep = check_mod.run_check(config_paths=[str(cfg)])
        self.assertEqual(len(rep["entries"]), 86)
        for row in rep["entries"]:
            self.assertEqual(row["class"], expect[row["config_name"]],
                             f"{row['config_name']}: {row}")
            self.assertEqual(row["listing"]["id"],
                             row["config_name"].split("-", 1)[1])
        s = rep["summary"]
        self.assertEqual(s[check_mod.CERTIFIED] + s[check_mod.LISTED], 86)
        self.assertEqual(s[check_mod.NOT_LISTED], 0)
        self.assertEqual(s[check_mod.UNRESOLVABLE], 0)


class Traps(unittest.TestCase):
    def _run(self, servers):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "claude_desktop_config.json"
            cfg.write_text(json.dumps({"mcpServers": servers}))
            return check_mod.run_check(config_paths=[str(cfg)])

    def test_typosquat_is_not_listed(self):
        rep = self._run({"typo": {"command": "uvx",
                                  "args": ["eclipse-procure-mpc"]}})
        row = rep["entries"][0]
        self.assertEqual(row["class"], check_mod.NOT_LISTED)
        self.assertIsNone(row["listing"])

    def test_stale_pin_flags_drift(self):
        rep = self._run({"stale": {"command": "uvx",
                                   "args": ["eclipse-procure-mcp@0.1.0"]}})
        row = rep["entries"][0]
        self.assertEqual(row["class"], check_mod.CERTIFIED)
        self.assertIsNotNone(row["drift"])
        self.assertEqual(row["drift"]["pinned"], "0.1.0")
        self.assertEqual(row["drift"]["listed"], "0.2.1")
        # a current pin produces no drift note
        rep2 = self._run({"cur": {"command": "uvx",
                                  "args": ["eclipse-procure-mcp@0.2.1"]}})
        self.assertIsNone(rep2["entries"][0]["drift"])

    def test_shell_wrapper_is_unresolvable(self):
        rep = self._run({"wrapped": {"command": "sh",
                                     "args": ["-c", "run-the-thing"]}})
        row = rep["entries"][0]
        self.assertEqual(row["class"], check_mod.UNRESOLVABLE)
        self.assertIn("shell", row["reason"])

    def test_remote_url_entry_is_identity_not_probe(self):
        rep = self._run({"remote": {"url": "https://mcp.example.com/sse"}})
        row = rep["entries"][0]
        self.assertEqual(row["identity"]["kind"], "remote")
        self.assertEqual(row["class"], check_mod.NOT_LISTED)


class CanaryAndFence(unittest.TestCase):
    def test_canary_secrets_never_escape_and_no_network(self):
        servers = {
            "withenv": {"command": "uvx", "args": ["eclipse-bazaar"],
                        "env": {"API_KEY": CANARIES[0], "PLAIN": "x"}},
            "dockerenv": {"command": "docker",
                          "args": ["run", "-i", "--rm", "-e",
                                   f"DB_PASS={CANARIES[1]}",
                                   "ghcr.io/cyan-eclipse-technologies-llc/bazaar-mcp"]},
            "remotehdr": {"url": "https://mcp.example.com/sse",
                          "headers": {"Authorization": f"Bearer {CANARIES[2]}"}},
        }
        calls = []
        real_urlopen = urllib.request.urlopen

        def trap(*a, **k):
            calls.append((a, k))
            raise AssertionError("network use during check")

        urllib.request.urlopen = trap
        try:
            with tempfile.TemporaryDirectory() as td:
                cfg = Path(td) / "mcp.json"
                cfg.write_text(json.dumps({"mcpServers": servers}))
                rep = check_mod.run_check(config_paths=[str(cfg)])
        finally:
            urllib.request.urlopen = real_urlopen
        self.assertEqual(calls, [])
        blob = json.dumps(rep)
        for canary in CANARIES:
            self.assertNotIn(canary, blob)
        by_name = {r["config_name"]: r for r in rep["entries"]}
        self.assertEqual(by_name["withenv"]["class"], check_mod.CERTIFIED)
        self.assertEqual(by_name["dockerenv"]["class"], check_mod.CERTIFIED)

    def test_check_never_executes_configured_servers(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / "EXECUTED"
            script = Path(td) / "evil.py"
            script.write_text(f"open({str(marker)!r}, 'w').write('x')\n")
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {
                "evil": {"command": "python3", "args": [str(script)]}}}))
            check_mod.run_check(config_paths=[str(cfg)])
            self.assertFalse(marker.exists())

    def test_no_subprocess_in_check_path(self):
        for mod in (check_mod, configparse):
            src = Path(mod.__file__).read_text()
            self.assertNotIn("subprocess", src)
            self.assertNotIn("os.system", src)
            self.assertNotIn("Popen", src)


class Vocabulary(unittest.TestCase):
    def test_closed_vocabulary_and_absent_later_phase_tokens(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "empty.json"
            cfg.write_text(json.dumps({"mcpServers": {}}))
            rep = check_mod.run_check(config_paths=[str(cfg)])
        self.assertEqual({r["class"] for r in rep["entries"]} |
                         set(rep["summary"]), set(check_mod.CLASSES))
        surfaces = [json.dumps(rep)]
        for py in (ROOT / "src/eclipse_bazaar").rglob("*.py"):
            surfaces.append(py.read_text())
        surfaces.append((ROOT / "PYPI_README.md").read_text())
        for text in surfaces:
            for tok in FORBIDDEN:
                self.assertIsNone(re.search(rf"\b{tok}\b", text),
                                  f"forbidden Phase-1 token {tok!r} present")

    def test_redaction_is_structural(self):
        doc = {"mcpServers": {"x": {"command": "uvx", "args": ["eclipse-bazaar"],
                                    "env": {"K": CANARIES[0]}}}}
        red = configparse.redact_config(doc)
        self.assertNotIn(CANARIES[0], json.dumps(red))
        entries = list(configparse.server_entries(red))
        self.assertEqual(entries[0][1]["env"],
                         {"<redacted-env-key-count>": 1})


UI_CANARY = "CANARY-UI-3f9c1e77"


class UserinfoCanaries(unittest.TestCase):
    """PY-D2 (gate S3; K4 strike 1): credentials in URL userinfo must
    be ABSENT from the identity and from every output channel — report
    object, CLI --json stdout, --out file content, text render. Not
    masked: absent. (The report object is what --json prints and --out
    writes verbatim, so it is asserted alongside the text render.)"""

    def _run(self, servers):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps({"mcpServers": servers}))
            return check_mod.run_check(config_paths=[str(cfg)])

    def test_userinfo_absent_from_identity_and_all_outputs(self):
        servers = {
            "remote-ui": {"url":
                          f"https://svc:{UI_CANARY}@mcp.example.net/sse"},
            "remote-ui-port": {"url":
                               f"https://svc:{UI_CANARY}@mcp.example.net:8443/sse"},
            "user-only": {"url": f"https://{UI_CANARY}@mcp.example.net/sse"},
            "from-https": {"command": "uvx", "args": [
                "--from",
                f"https://oauth2:{UI_CANARY}@gitlab.example.net/group/proj.git",
                "proj"]},
            "from-git": {"command": "uvx", "args": [
                "--from",
                f"git+https://oauth2:{UI_CANARY}@github.example.com/owner/repo.git",
                "repo"]},
            "registry-ui": {"command": "npx", "args": [
                "-y", "--registry",
                f"https://user:{UI_CANARY}@npm.example.net/", "some-pkg"]},
            "query-token": {"url":
                            f"https://mcp.example.net/sse?token={UI_CANARY}"},
        }
        rep = self._run(servers)
        for text in (json.dumps(rep), cli_mod._render_check(rep)):
            self.assertNotIn(UI_CANARY, text)
            self.assertNotIn(UI_CANARY.lower(), text)
        by_name = {r["config_name"]: r for r in rep["entries"]}
        # The credential is gone; the identity itself survives intact.
        self.assertEqual(by_name["remote-ui"]["identity"]["name"],
                         "mcp.example.net/sse")
        self.assertEqual(by_name["remote-ui-port"]["identity"]["name"],
                         "mcp.example.net:8443/sse")
        self.assertEqual(by_name["user-only"]["identity"]["name"],
                         "mcp.example.net/sse")
        self.assertEqual(by_name["from-https"]["identity"]["name"],
                         "https://gitlab.example.net/group/proj.git")
        self.assertEqual(by_name["from-git"]["identity"]["name"],
                         "git+https://github.example.com/owner/repo.git")
        for row in rep["entries"]:
            self.assertIn(row["class"], check_mod.CLASSES)


class QualifiedSourceMatching(unittest.TestCase):
    """PY-D3: standing binds to the full qualified identity. A bare
    name under a foreign registry / owner / scope is NOT LISTED —
    never CERTIFIED or LISTED by inheritance."""

    def _run1(self, entry):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {"x": entry}}))
            rep = check_mod.run_check(config_paths=[str(cfg)])
        return rep["entries"][0]

    def test_foreign_registry_image_is_not_listed(self):
        row = self._run1({"command": "docker",
                          "args": ["run", "-i", "--rm",
                                   "evil.io/certbridge-mcp"]})
        self.assertEqual(row["class"], check_mod.NOT_LISTED)
        self.assertIsNone(row["listing"])
        self.assertIn("different source", row["reason"])

    def test_foreign_ghcr_owner_is_not_listed(self):
        row = self._run1({"command": "docker",
                          "args": ["run", "-i", "--rm",
                                   "ghcr.io/someone-else/certbridge-mcp"]})
        self.assertEqual(row["class"], check_mod.NOT_LISTED)
        self.assertIsNone(row["listing"])

    def test_foreign_npm_scope_is_not_listed(self):
        row = self._run1({"command": "npx",
                          "args": ["-y", "@evil-scope/certbridge-mcp"]})
        self.assertEqual(row["class"], check_mod.NOT_LISTED)
        self.assertIsNone(row["listing"])

    def test_own_qualified_identities_still_match(self):
        row = self._run1({"command": "docker",
                          "args": ["run", "-i", "--rm",
                                   "ghcr.io/cyan-eclipse-technologies-llc/"
                                   "certbridge-mcp"]})
        self.assertEqual(row["class"], check_mod.CERTIFIED)
        row = self._run1({"command": "uvx", "args": ["certbridge-mcp"]})
        self.assertEqual(row["class"], check_mod.CERTIFIED)
        row = self._run1({"command": "docker",
                          "args": ["run", "-i", "--rm", "certbridge-mcp"]})
        self.assertEqual(row["class"], check_mod.CERTIFIED)


class DualBlockConfigs(unittest.TestCase):
    """PY-D4: a config carrying BOTH top-level blocks loses nothing —
    every entry of every block is examined and reported."""

    def test_both_blocks_are_read_25_of_25(self):
        doc = {"mcpServers": {f"a{i:02d}": {"command": "uvx",
                                            "args": ["eclipse-bazaar"]}
                              for i in range(13)},
               "servers": {f"b{i:02d}": {"command": "uvx",
                                         "args": ["eclipse-procure-mcp"]}
                           for i in range(12)}}
        self.assertEqual(len(list(configparse.server_entries(doc))), 25)
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps(doc))
            rep = check_mod.run_check(config_paths=[str(cfg)])
        self.assertEqual(len(rep["entries"]), 25)
        names = {r["config_name"] for r in rep["entries"]}
        self.assertEqual(len(names), 25)


class VersionNotChecked(unittest.TestCase):
    """PY-D5: a pin against a versionless listing discloses that the
    version was not — and cannot be — checked, in JSON and in text."""

    def _run1(self, entry):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "mcp.json"
            cfg.write_text(json.dumps({"mcpServers": {"x": entry}}))
            return check_mod.run_check(config_paths=[str(cfg)])

    def test_pin_against_versionless_listing_discloses(self):
        rep = self._run1({"command": "uvx",
                          "args": ["agent-ready-mcp@9.9.9"]})
        row = rep["entries"][0]
        self.assertIsNotNone(row["listing"])
        self.assertIsNone(row["listing"]["listing_version"])
        self.assertIsNone(row["drift"])
        self.assertIn("version not checked", row["version_note"])
        self.assertIn("version not checked", cli_mod._render_check(rep))

    def test_pin_against_versioned_listing_has_no_note(self):
        rep = self._run1({"command": "uvx",
                          "args": ["eclipse-procure-mcp@0.2.1"]})
        row = rep["entries"][0]
        self.assertIsNone(row["version_note"])
        self.assertNotIn("version not checked", cli_mod._render_check(rep))


class RepoModeGate(unittest.TestCase):
    """PY-D1: repo-mode fallbacks fire only behind a real repo-mode
    signal (checkout markers or BAZAAR_REPO_MODE=1). Files planted at
    an installed wheel's computed tree levels are never served."""

    def test_installed_tree_plants_are_never_served(self):
        with tempfile.TemporaryDirectory() as td:
            lib = Path(td) / "lib"
            site = lib / "site-packages"
            site.mkdir(parents=True)
            (site / "catalog.json").write_text(json.dumps(
                {"products": [{"id": "poison-plant"}]}))
            ref = "test-bench/results/poison-plant.json"
            card_path = lib / ref
            card_path.parent.mkdir(parents=True)
            card_path.write_text(json.dumps(
                {"tool": "poison-plant", "verdict": "CERTIFIED(poisoned)"}))
            saved = (catalog_mod.REPO_ROOT, catalog_mod.CETECH_DIR,
                     os.environ.pop("BAZAAR_REPO_MODE", None),
                     os.environ.pop("BAZAAR_CATALOG", None))
            catalog_mod.REPO_ROOT, catalog_mod.CETECH_DIR = site, lib
            try:
                self.assertFalse(catalog_mod._repo_mode())
                self.assertEqual(catalog_mod.catalog_path(),
                                 catalog_mod.DATA_DIR / "catalog.json")
                self.assertIsNone(catalog_mod.scorecard_summary(ref))
                # The checkout's own markers flip repo mode back on —
                # the gate is a signal, not a removal of repo behavior.
                (site / ".git").mkdir()
                (site / "server.json").write_text("{}")
                self.assertTrue(catalog_mod._repo_mode())
                self.assertEqual(
                    catalog_mod.scorecard_summary(ref)["verdict"],
                    "CERTIFIED(poisoned)")
            finally:
                catalog_mod.REPO_ROOT, catalog_mod.CETECH_DIR = saved[:2]
                if saved[2] is not None:
                    os.environ["BAZAAR_REPO_MODE"] = saved[2]
                if saved[3] is not None:
                    os.environ["BAZAAR_CATALOG"] = saved[3]

    def test_env_opt_in_enables_repo_mode(self):
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td)
            saved = (catalog_mod.REPO_ROOT,
                     os.environ.pop("BAZAAR_REPO_MODE", None))
            catalog_mod.REPO_ROOT = empty
            try:
                self.assertFalse(catalog_mod._repo_mode())
                os.environ["BAZAAR_REPO_MODE"] = "1"
                self.assertTrue(catalog_mod._repo_mode())
            finally:
                catalog_mod.REPO_ROOT = saved[0]
                del os.environ["BAZAAR_REPO_MODE"]
                if saved[1] is not None:
                    os.environ["BAZAAR_REPO_MODE"] = saved[1]


if __name__ == "__main__":
    unittest.main()
