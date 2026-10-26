# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""Data access for the eclipse-bazaar distribution.

Resolution order (first hit wins):
  catalog   $BAZAAR_CATALOG -> repo-root catalog.json (repo mode, kept
            canonical by sync_verdicts.py) -> bundled data/catalog.json
  corpus    see eclipse_bazaar.check (bulk file, sha256-verified)
  scorecard bundled verdict snapshot first (stamped + hash-pinned by
            tools/make_verdict_snapshot.py); repo mode falls back to the
            live Test Bench card when the snapshot lacks the ref.

Gate A1: packaged mode never reaches for ../test-bench/results/ — the
snapshot is the only verdict source an installed wheel needs.
"""
import json
import os
import urllib.request
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
DATA_DIR = PKG_DIR / "data"
REPO_ROOT = PKG_DIR.parents[1]   # dev layout: bazaar-mcp/ (site-packages when installed)
CETECH_DIR = PKG_DIR.parents[2]  # dev layout: cyan-eclipse/ (meaningless when installed)

REFRESH_URLS = [
    "https://raw.githubusercontent.com/CYAN-ECLIPSE-TECHNOLOGIES-LLC/bazaar-mcp/main/catalog.json",
]

_LAST_SOURCE = "bundled snapshot"
_SNAPSHOT = None


def catalog_path() -> Path:
    env = os.environ.get("BAZAAR_CATALOG")
    if env:
        return Path(env)
    repo_cat = REPO_ROOT / "catalog.json"
    if repo_cat.exists():
        return repo_cat
    return DATA_DIR / "catalog.json"


def fetch_catalog(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def catalog_dict(refresh: bool = False) -> dict:
    """The catalog as a dict. refresh=True tries the public HTTPS JSON
    source first (one bulk document — never per-product queries) and
    falls back to the local snapshot on any failure."""
    global _LAST_SOURCE
    if refresh:
        for url in REFRESH_URLS:
            try:
                cat = fetch_catalog(url)
                if isinstance(cat, dict) and "products" in cat:
                    _LAST_SOURCE = f"refreshed from {url}"
                    return cat
            except Exception:
                continue
    path = catalog_path()
    cat = json.loads(path.read_text())
    _LAST_SOURCE = ("repo catalog.json" if path == REPO_ROOT / "catalog.json"
                    else "bundled snapshot")
    return cat


def freshness(cat: dict) -> dict:
    return {"catalog_built": cat.get("built"),
            "sources": cat.get("sources", []),
            "served_from": _LAST_SOURCE,
            "note": "Statuses and verdicts are as of the catalog build date; "
                    "scorecard summaries come from the stamped verdict "
                    "snapshot bundled with this package (hash-pinned to the "
                    "Test Bench cards), or the referenced card in repo mode."}


# ------------------------------------------------------------ scorecards
def _check_rows(sc: dict):
    """Normalise the three Test Bench card shapes to (name, verdict):
    list-of-dicts (original), dict-of-results (later cards), and
    checks-absent (scoped re-bench cards -> no rows)."""
    checks = sc.get("checks")
    if isinstance(checks, list):
        for ch in checks:
            if isinstance(ch, dict):
                yield ch.get("name"), ch.get("verdict", "other")
    elif isinstance(checks, dict):
        for name, res in checks.items():
            if isinstance(res, dict):
                if "verdict" in res:
                    yield name, res["verdict"]
                elif "pass" in res:
                    yield name, "pass" if res["pass"] else "fail"
                else:
                    yield name, "other"
            else:
                yield name, "other"


def summarize_card(sc: dict) -> dict:
    """Scorecard file -> the summary the server returns. Pure function —
    tools/make_verdict_snapshot.py builds the snapshot with this exact
    code, which is what makes packaged/repo parity testable. (The
    pre-packaging server crashed on dict-shaped and checks-absent cards;
    the summary for list-shaped cards is unchanged.)"""
    counts = {"pass": 0, "fail": 0, "na": 0, "other": 0}
    na_names, fail_names = [], []
    total = 0
    for name, v in _check_rows(sc):
        total += 1
        counts[v if v in counts else "other"] += 1
        if v == "na":
            na_names.append(name)
        if v == "fail":
            fail_names.append(name)
    return {"tool": sc.get("tool") or sc.get("product"),
            "version": sc.get("version"),
            "bench_date": sc.get("bench_date") or sc.get("date"),
            "bench_version": sc.get("bench_version"),
            "environment": sc.get("environment"),
            "verdict": sc.get("verdict"),
            "checks_total": total, "counts": counts,
            "not_tested_checks": na_names,
            "failed_checks": fail_names}


def load_snapshot():
    global _SNAPSHOT
    if _SNAPSHOT is None:
        path = DATA_DIR / "verdict_snapshot.json"
        _SNAPSHOT = json.loads(path.read_text()) if path.exists() else {}
    return _SNAPSHOT


def scorecard_summary(ref: str):
    """Summary for a catalog scorecard_ref, or None if unavailable."""
    snap = load_snapshot()
    rec = (snap.get("cards") or {}).get(ref)
    if rec is not None:
        return rec["summary"]
    path = CETECH_DIR / ref  # repo mode only; absent in an installed wheel
    if path.exists():
        return summarize_card(json.loads(path.read_text()))
    return None
