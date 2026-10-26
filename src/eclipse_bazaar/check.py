# Eclipse Bazaar · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""`bazaar check` — marketplace-standing check for configured MCP servers.

Phase 1 (this build). Every configured server is classified into
exactly one of four classes, from config text + the published Bazaar
corpus only:

  CERTIFIED    listed, with a Tier-2 Test Bench verdict on record
  LISTED       in the catalog, no Tier-2 verdict (listing status shown)
  NOT LISTED   no Bazaar record for the resolved identity (a neutral
               fact — not a warning, not a failure)
  UNRESOLVABLE no identity could be extracted from the config entry

Later-phase vocabulary for not-yet-public record classes does not exist
in this binary by construction: score/record fields for unpublished
data classes are absent — not null, not stubbed, not behind a flag —
and ship only in a later phase, once the underlying records themselves
are public (the gate binds the data, not the channel).

Fences (breach = gate K1): this module never executes a configured
server, never reads a tool description, never contacts a configured
server's endpoint, and never scores or ranks an unlisted server.
There is deliberately no aggregate score over the report.

Architecture (gate S1): the corpus is one bulk file, downloaded whole
and sha256-verified against its manifest before use, then joined
locally. Zero per-server queries leave the machine. The bundled corpus
snapshot is the offline default; a per-name lookup mode does not exist.
"""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

from .catalog import DATA_DIR
from .configparse import (default_config_paths, extract_identity,
                          load_config_entries, unresolvable_reason)

CERTIFIED = "CERTIFIED"
LISTED = "LISTED"
NOT_LISTED = "NOT LISTED"
UNRESOLVABLE = "UNRESOLVABLE"
CLASSES = (CERTIFIED, LISTED, NOT_LISTED, UNRESOLVABLE)

CORPUS_BASE = ("https://raw.githubusercontent.com/"
               "CYAN-ECLIPSE-TECHNOLOGIES-LLC/bazaar-mcp/main/corpus")
CORPUS_URL = CORPUS_BASE + "/corpus.jsonl"
MANIFEST_URL = CORPUS_BASE + "/corpus.manifest.json"


class CorpusError(Exception):
    pass


# ---------------------------------------------------------------- corpus
def _verify(raw: bytes, manifest: dict):
    digest = hashlib.sha256(raw).hexdigest()
    if manifest.get("sha256") != digest:
        raise CorpusError(
            f"corpus sha256 mismatch: manifest {manifest.get('sha256')}, "
            f"downloaded {digest} — refusing unverified corpus")
    return digest


def _parse_corpus(raw: bytes):
    records = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _bundled_corpus():
    raw = (DATA_DIR / "corpus.jsonl").read_bytes()
    manifest = json.loads((DATA_DIR / "corpus.manifest.json").read_text())
    digest = _verify(raw, manifest)
    return _parse_corpus(raw), {"source": "bundled snapshot",
                                "sha256": digest, "manifest": manifest}


def _download(url, timeout=20):
    req = urllib.request.Request(url, headers={"Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _refreshed_corpus():
    manifest = json.loads(_download(MANIFEST_URL).decode("utf-8"))
    raw = _download(CORPUS_URL)
    digest = _verify(raw, manifest)
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) \
        / "eclipse-bazaar"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "corpus.jsonl").write_bytes(raw)
    (cache / "corpus.manifest.json").write_text(json.dumps(manifest, indent=1))
    return _parse_corpus(raw), {"source": f"refreshed from {CORPUS_URL}",
                                "sha256": digest, "manifest": manifest}


def load_corpus(corpus_path=None, refresh=False):
    """(records, meta). Explicit local file wins; then refresh; the
    bundled snapshot is the always-available fallback."""
    if corpus_path:
        raw = Path(corpus_path).read_bytes()
        manifest_path = Path(str(corpus_path).replace(
            "corpus.jsonl", "corpus.manifest.json"))
        meta = {"source": f"local file {corpus_path}", "sha256": None,
                "manifest": None}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            meta["sha256"] = _verify(raw, manifest)
            meta["manifest"] = manifest
            meta["source"] += " (sha256 verified against sibling manifest)"
        return _parse_corpus(raw), meta
    if refresh:
        try:
            return _refreshed_corpus()
        except Exception as e:
            records, meta = _bundled_corpus()
            meta["refresh_error"] = f"{type(e).__name__}: {e}"
            meta["source"] += " (refresh failed, bundled fallback)"
            return records, meta
    return _bundled_corpus()


def build_index(records):
    index = {}
    for rec in records:
        for ident in rec.get("identities", []):
            index.setdefault(ident.lower(), rec)
    return index


# ------------------------------------------------------------ classify
def classify(config_name, entry, index):
    identity = extract_identity(entry)
    if identity is None:
        return {"config_name": config_name, "class": UNRESOLVABLE,
                "identity": None,
                "reason": unresolvable_reason(entry),
                "listing": None, "drift": None}
    rec = index.get(identity["name"])
    if rec is None and "/" in identity["name"]:
        rec = index.get(identity["name"].rsplit("/", 1)[-1])
    if rec is None:
        return {"config_name": config_name, "class": NOT_LISTED,
                "identity": identity,
                "reason": "no Bazaar listing record for this identity",
                "listing": None, "drift": None}
    cls = CERTIFIED if (rec.get("certified") and rec.get("bench_verdict")) else LISTED
    drift = None
    pin, listed = identity.get("pin"), rec.get("listing_version")
    if pin and listed and pin != listed:
        drift = {"pinned": pin, "listed": listed,
                 "note": f"config pins version {pin}; the listing's current "
                         f"version is {listed} — the tested standing below "
                         f"belongs to the listed version"}
    listing = {"id": rec["id"], "name": rec["name"], "status": rec["status"],
               "bench_verdict": rec.get("bench_verdict"),
               "certified_scope": rec.get("certified_scope"),
               "listing_version": listed,
               "scorecard_ref": rec.get("scorecard_ref"),
               "listing_url": rec.get("listing_url")}
    return {"config_name": config_name, "class": cls, "identity": identity,
            "reason": None, "listing": listing, "drift": drift}


def run_check(config_paths=None, corpus_path=None, refresh_corpus=False):
    """The full Phase-1 check. Returns the report dict (no score —
    counts per class only)."""
    paths = [Path(p) for p in config_paths] if config_paths \
        else default_config_paths()
    records, corpus_meta = load_corpus(corpus_path, refresh_corpus)
    index = build_index(records)
    entries, file_notes = [], []
    for path in paths:
        loaded, error = load_config_entries(path)
        if error:
            file_notes.append({"config_file": str(path), "error": error})
            continue
        for name, entry in loaded:
            row = classify(name, entry, index)
            row["config_file"] = str(path)
            entries.append(row)
    summary = {c: 0 for c in CLASSES}
    for row in entries:
        summary[row["class"]] += 1
    return {
        "tool": "eclipse-bazaar check (phase 1)",
        "corpus": {"records": len(records),
                   "source": corpus_meta["source"],
                   "sha256": corpus_meta["sha256"],
                   "generated_at": (corpus_meta.get("manifest") or {}).get("generated_at"),
                   "refresh_error": corpus_meta.get("refresh_error")},
        "config_files": [str(p) for p in paths],
        "file_notes": file_notes,
        "summary": summary,
        "entries": entries,
        "notes": [
            "Classes are facts about listing/verdict records, not safety "
            "judgements. NOT LISTED is neutral: the Bazaar catalog v0.1 "
            "covers Cyan Eclipse Technologies products.",
            "env values in your configs were never read, copied, or "
            "transmitted; the join ran locally against the bulk corpus.",
        ],
    }
