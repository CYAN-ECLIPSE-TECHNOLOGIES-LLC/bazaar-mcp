#!/usr/bin/env python3
# Eclipse Bazaar MCP · © 2026 Cyan Eclipse Technologies LLC · cetech.ai
"""make_corpus — build the Phase-1 `bazaar check` corpus from the catalog.

One JSONL record per Bazaar listing: listing facts (status, Tier-2
verdict, certified scope, listing version) plus the machine identities a
client config might use to reach that listing (catalog id, source repo
name, registry server name, package identifiers harvested from the
listing's own server.json / pyproject.toml / package.json, and the
house GHCR image pattern). The join in eclipse_bazaar.check is exact
match over these identities — nothing here ranks or scores anything.

Outputs (kept identical; sync_package_data copies both into the wheel):
  corpus/corpus.jsonl          — the bulk corpus (gate S1: downloaded
                                 whole, joined locally, zero per-server
                                 queries leave the user's machine)
  corpus/corpus.manifest.json  — sha256 manifest the client verifies
                                 before any downloaded corpus is used
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CETECH = ROOT.parent
GHCR_OWNER = "cyan-eclipse-technologies-llc"
LISTING_URL = "https://eclipsebazaar.com"


def _image_identities(identifier: str):
    """OCI identifier -> (full path, basename), tag/digest stripped."""
    ident = identifier.split("@", 1)[0]
    parts = ident.rsplit("/", 1)
    if len(parts) == 2 and ":" in parts[1]:
        ident = ident[: ident.rfind(":")]
    return {ident.lower(), ident.rsplit("/", 1)[-1].lower()}


def resolve_repo(product: dict):
    """The product's own repo, proven by its bazaar-manifest slug —
    source_refs are evidence pointers (scorecards, slate docs, library
    files inside other repos), not repo claims. No manifest match ->
    no repo, and the record carries the catalog id as its only
    identity (no borrowed aliases)."""
    for ref in product.get("source_refs") or []:
        if ref.endswith("/bazaar-manifest.json"):
            manifest_path = CETECH / ref
            if manifest_path.exists():
                try:
                    slug = json.loads(manifest_path.read_text()).get("slug")
                except Exception:
                    slug = None
                if slug == product["id"]:
                    return ref.split("/", 1)[0]
    return None


def harvest(product: dict) -> dict:
    cert = product.get("certification") or {}
    identities = {product["id"].lower()}
    repo_name = resolve_repo(product)
    listing_version = None
    if repo_name:
        identities.add(repo_name.lower())
        identities.add(f"ghcr.io/{GHCR_OWNER}/{repo_name}".lower())
    repo = CETECH / repo_name if repo_name else None
    if repo and repo.is_dir():
        sj = repo / "server.json"
        if sj.exists():
            try:
                doc = json.loads(sj.read_text())
            except Exception:
                doc = {}
            listing_version = doc.get("version") or listing_version
            if doc.get("name"):
                identities.add(doc["name"].rsplit("/", 1)[-1].lower())
            for pkg in doc.get("packages") or []:
                ident = pkg.get("identifier")
                if not ident:
                    continue
                if pkg.get("registryType") == "oci":
                    identities |= _image_identities(ident)
                else:
                    identities.add(ident.lower())
                    identities.add(ident.rsplit("/", 1)[-1].lower())
        pp = repo / "pyproject.toml"
        if pp.exists():
            m = re.search(r'(?m)^name\s*=\s*"([^"]+)"', pp.read_text())
            if m:
                identities.add(m.group(1).lower())
        pj = repo / "package.json"
        if pj.exists():
            try:
                name = json.loads(pj.read_text()).get("name")
            except Exception:
                name = None
            if name:
                identities.add(name.lower())
    return {
        "id": product["id"],
        "name": product["name"],
        "vendor": product.get("vendor"),
        "status": product["status"],
        "certified": bool(cert.get("certified")),
        "bench_verdict": cert.get("bench_verdict"),
        "certified_scope": cert.get("certified_scope"),
        "scorecard_ref": cert.get("scorecard_ref"),
        "listing_version": listing_version,
        "identities": sorted(identities),
        "listing_url": LISTING_URL,
    }


def main():
    cat = json.loads((ROOT / "catalog.json").read_text())
    records = [harvest(p) for p in cat["products"]]
    lines = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    raw = lines.encode()
    manifest = {
        "file": "corpus.jsonl",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "records": len(records),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "tools/make_corpus.py",
        "catalog_built": cat.get("built"),
    }
    out_dir = ROOT / "corpus"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "corpus.jsonl").write_bytes(raw)
    (out_dir / "corpus.manifest.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"corpus: {len(records)} records, sha256 {manifest['sha256'][:16]}… "
          f"-> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
