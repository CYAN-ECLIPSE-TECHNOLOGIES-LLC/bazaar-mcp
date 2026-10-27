# Eclipse Bazaar MCP

**Powered by Cyan Eclipse Technologies** — https://cetech.ai
The agent-facing discovery layer for **Eclipse Bazaar** (eclipsebazaar.com) — CETech's tested MCP marketplace.

## Why this exists

Agents shop by problem, not by product name. A registry listing tells an agent that a server *exists*; it does not say what problem the tool solves, whether anyone tested it, or what was **not** tested. Eclipse Bazaar's differentiator is exactly that honesty layer — every listing carries its Test Bench verdict, its certified scope, and its not-tested list, or states plainly that no verdict exists yet.

This MCP server is how agents query that catalog:

- **By problem** — `find_solutions` matches a plain-language problem against problem statements + capabilities and explains the fit, with status and certification badges inline.
- **By keyword** — `search_products` ranks across names, capabilities, and categories, and every hit carries `match_reasons[]`: the ranking is never a black box.
- **With receipts** — `get_certification` returns the latest Test Bench verdict plus a live summary of the underlying scorecard (check counts, environment, date), the certified scope, and the `not_tested` list.
- **Honestly labelled** — spec-stage products are `status: spec` and `certified: false`; products whose bench run is pending say "not yet certified"; The White Report MCP's verdict is CERTIFIED(live) — the 2026-10-25 live-host bench (card -11) superseded its earlier logic-level PARTIAL, and every surface is kept in sync from the newest scorecard by `sync_verdicts.py`.

## Tools (6)

| Tool | What it does |
|---|---|
| `search_products(query, category?)` | Ranked keyword search; every hit carries `match_reasons[]`. |
| `find_solutions(problem)` | Problem-first matching with fit explanation + status/certification badges. |
| `get_product(id)` | Full entry incl. certification block and what was NOT tested. |
| `compare_products(ids[])` | Side-by-side: status, pricing model, certification, platforms. |
| `get_certification(id)` | Latest bench verdict + scorecard summary + scope + not_tested; explicit "NOT YET CERTIFIED" when none exists. |
| `list_categories()` | Categories with counts by status. |

Every response includes a `data_freshness` note (catalog build date + source references). Scorecard summaries are read live from `../test-bench/results/` at call time.

## Catalog (v0.1.0 — 64 products, CETech only)

Seeded only from real sources — each product's `bazaar-manifest.json`, the latest Test Bench scorecard, the MCP product slate, and the Eclipse Mail spec. No invented products, no invented verdicts.

| Product | Status | Bench verdict |
|---|---|---|
| Eclipse Agent Wallet MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(sandbox) |
| CertBridge MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(staging) |
| HostBridge MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Connect | dogfood | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(dogfood) |
| The White Report MCP | live | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(live) |
| Eclipse Apply MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(sandbox) |
| Eclipse Herald MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Beacon MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Cluster MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Thread MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Constellation MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Deep Field MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Pantry MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Marquee MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Dispatch MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Social Core MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Aperture MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Zephyr MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(live-read) |
| Eclipse Environment MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Procure MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Gig Core MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Compass MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Stage MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Zenith MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Muster MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Haven MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Orbit MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Voice Core MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Trunk MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Connect MCP | dogfood | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(dogfood-facade) |
| Eclipse Connect · Beyond Compare MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulated) |
| AgentReady MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Florida Bid Intel MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Bazaar MCP (this server) | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Envoy MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Fathom MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Codex MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Ledger MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Till MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) · Ads Rail P1 extension CERTIFIED(local/simulator), Stripe test mode only — NOT PROVEN IN STRIPE |
| Eclipse Book MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Forecast MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Strike MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Meter MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Tripwire MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Umbra MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Blackbox MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Docket MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Countermark MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Census MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Crosswalk MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Redteam MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Span MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Airtime MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local/simulator) |
| Eclipse Friction MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Test Bench | in-development | not certified — in-house artifact, productization in progress (slate T1) |
| Eclipse Stocktake | in-development | not certified — in-house artifact, productization in progress (slate T4) |
| Eclipse Press | in-development | not certified — in-house artifact, productization in progress (slate T3) |
| Herald Card Kit | in-development | not certified — in-house artifact, productization in progress (slate T7) |
| Eclipse BidMatrix MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Section 508 Evidence MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| FedScope MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Health Check MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Legacy Recon MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) — at the NARROWED OBSERVED SCOPE (CLAIM-SCOPE.md), scoped re-bench card -11 (30/30 checks); cards -1..-10 retained append-only (card -10 FAILED at the former universal claim) |
| Eclipse Steward MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Mail MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local / fixture-only) |
| Eclipse Proof MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Charter MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Colophon MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local/simulator) |
| Eclipse Tether MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Proving MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Wageward MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Covenant MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local/simulator) |
| Eclipse Meridian MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local, synthetic scope) |
| Eclipse Consent MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Lineage MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Attest MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Revoke MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Keyhold MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Loft MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(simulator) |
| Eclipse Corona MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Crosslist MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(split per facet) |
| Eclipse Verbatim MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Roll MCP | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Verbatim — Executive Orders | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Flood Witness | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Recall Witness | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED(local) |
| Eclipse Sunset | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (local, fixture) |
| Eclipse Nexus Witness | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (local, fixture-vintage) |
| Eclipse Warranty | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (local, fixture) |
| Eclipse Toolprint | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (local) |
| Eclipse Boomerang | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (local, fixture) |
| Eclipse Rebuttal | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (local, fixture) |
| Eclipse Crawlway | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (local, fixture) |
| Eclipse Outwatch | in-development | <img src="seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> CERTIFIED (LOCAL) |

## The `bazaar` CLI — including `bazaar check`

```console
$ bazaar search "certificate renewal"
$ bazaar product certbridge-mcp
$ bazaar categories
$ bazaar check            # classify your configured MCP servers
```

`bazaar check` reads your MCP client configs, extracts each configured server's *identity* (package / image / URL / local path), and joins it locally against the published Bazaar corpus — downloaded whole and verified against its sha256 manifest first. Each entry is classified `CERTIFIED` (listed, Tier-2 verdict on record), `LISTED` (in the catalog, no verdict yet), `NOT LISTED` (no record — a neutral fact), or `UNRESOLVABLE` (no identity could be extracted, with the reason). Version pins that differ from the listed version are flagged as drift.

Privacy, by construction: config `env` **values are never read, copied, hashed, logged, or transmitted** — the parser redacts them structurally before anything else runs. There is no telemetry. The check never executes a configured server and never contacts one. (The CLI ships in the `eclipse-bazaar` PyPI distribution alongside the MCP server above.)

## Run it

```bash
python3 server.py        # MCP over stdio, stdlib only, no dependencies
python3 smoke_test.py    # protocol + routing + honesty assertions (9 checks)
```

Catalog lives in `catalog.json` beside the server (override with `$BAZAAR_CATALOG`).

## Verdict sync (EB-09)

Bench verdicts have ONE source of truth: the newest scorecard per tool in `../test-bench/results/` (run-sequence suffix decides — a `-11` card supersedes `-2`). `python3 sync_verdicts.py` rebuilds `verdict-ledger.json` and checks catalog.json, product `bazaar-manifest.json` files, this README's table, and the storefront bench lines against it (exit 1 on drift); `--apply` fixes the machine-safe fields. Dogfood logs annotate live state only — they never change a bench verdict. Run it after every bench run.

## Scope & roadmap

- **v0.1.0 (this):** CETech catalog only, discovery only. **No purchasing.**
- **P2:** third-party listings (the vendor catalog opens; listings pass the Test Bench gate before they can carry a badge).
- **Future purchase hooks (noted, not built):** x402 pay-per-call for paid tools, and an **Agent Wallet policy check before any charge** — an agent's granted spending scope governs Bazaar purchases the same way it governs everything else.

## License / attribution

A Cyan Eclipse Technologies product. The "Powered by Cyan Eclipse Technologies" attribution travels with it.
