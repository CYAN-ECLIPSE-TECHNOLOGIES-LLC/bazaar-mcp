#!/usr/bin/env python3
# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""sync_package_data — regenerate every stamped artifact the wheel ships.

Run before building a wheel/sdist (CI does this in the publish
workflow; tests/test_version_drift.py + the snapshot parity test fail
on a stale tree):
  1. version      server.json -> VERSION + src/eclipse_bazaar/_version.py
  2. catalog      catalog.json -> src/eclipse_bazaar/data/catalog.json (copy)
  3. snapshot     test-bench cards -> src/eclipse_bazaar/data/verdict_snapshot.json
  4. corpus       catalog -> corpus/ + copy into src/eclipse_bazaar/data/
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script):
    print(f"== {script}")
    subprocess.run([sys.executable, str(ROOT / "tools" / script)],
                   check=True, cwd=ROOT)


def main():
    run("sync_version.py")
    data = ROOT / "src/eclipse_bazaar/data"
    data.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "catalog.json", data / "catalog.json")
    print("== catalog copied -> src/eclipse_bazaar/data/catalog.json")
    run("make_verdict_snapshot.py")
    run("make_corpus.py")
    shutil.copyfile(ROOT / "corpus/corpus.jsonl", data / "corpus.jsonl")
    shutil.copyfile(ROOT / "corpus/corpus.manifest.json",
                    data / "corpus.manifest.json")
    print("== corpus copied -> src/eclipse_bazaar/data/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
