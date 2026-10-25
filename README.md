# Eclipse Bazaar MCP

**Powered by Cyan Eclipse Technologies** — https://cetech.ai
The agent-facing discovery layer for **Eclipse Bazaar** (eclipsebazaar.com) — CETech's tested MCP marketplace.

## Why this exists

Agents shop by problem, not by product name. A registry listing tells an agent that a server *exists*; it does not say what problem the tool solves, whether anyone tested it, or what was **not** tested. Eclipse Bazaar's differentiator is exactly that honesty layer — every listing carries its Test Bench verdict, its certified scope, and its not-tested list, or states plainly that no verdict exists yet.

This MCP server is how agents query that catalog:

- **By problem** — `find_solutions` matches a plain-language problem against problem statements + capabilities and explains the fit, with status and certification badges inline.
- **By keyword** — `search_products` ranks across names, capabilities, and categories, and every hit carries `match_reasons[]`: the ranking is never a black box.
- **With receipts** — `get_certification` returns the latest Test Bench verdict plus a live summary of the underlying scorecard (check counts, environment, date), the certified scope, and the `not_tested` list.
- **Honestly labelled** — spec-stage products are `status: spec` and `certified: false`; products whose bench run is pending say "not yet certified"; The White Report MCP's verdict is PARTIAL (logic-level bench) and is presented as exactly that.

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

## Catalog (v0.1.0 — 14 products, CETech only)

Seeded only from real sources — each product's `bazaar-manifest.json`, the latest Test Bench scorecard, the MCP product slate, and the Eclipse Mail spec. No invented products, no invented verdicts.

| Product | Status | Bench verdict |
|---|---|---|
| Eclipse Agent Wallet MCP | in-development | CERTIFIED(sandbox) |
| CertBridge MCP | in-development | CERTIFIED(staging) |
| HostBridge MCP | in-development | CERTIFIED(simulator) |
| Eclipse Connect | dogfood | CERTIFIED(dogfood) |
| The White Report MCP | live | PARTIAL (logic-level) |
| AgentReady MCP | in-development | not yet certified (bench pending) |
| Florida Bid Intel MCP | in-development | not yet certified (bench pending) |
| Eclipse Bazaar MCP (this server) | in-development | not yet certified (bench pending) |
| BidMatrix · Section 508 Evidence · FedScope · MCP Health Check · Legacy Recon · Eclipse Mail | spec | not certified (not built) |

## Run it

```bash
python3 server.py        # MCP over stdio, stdlib only, no dependencies
python3 smoke_test.py    # protocol + routing + honesty assertions (9 checks)
```

Catalog lives in `catalog.json` beside the server (override with `$BAZAAR_CATALOG`).

## Scope & roadmap

- **v0.1.0 (this):** CETech catalog only, discovery only. **No purchasing.**
- **P2:** third-party listings (the vendor catalog opens; listings pass the Test Bench gate before they can carry a badge).
- **Future purchase hooks (noted, not built):** x402 pay-per-call for paid tools, and an **Agent Wallet policy check before any charge** — an agent's granted spending scope governs Bazaar purchases the same way it governs everything else.

## License / attribution

A Cyan Eclipse Technologies product. The "Powered by Cyan Eclipse Technologies" attribution travels with it.
