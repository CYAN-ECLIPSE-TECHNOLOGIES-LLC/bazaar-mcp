# Eclipse Bazaar MCP

**Powered by Cyan Eclipse Technologies** — https://cetech.ai

The agent-facing discovery layer for **Eclipse Bazaar** (eclipsebazaar.com),
CETech's tested MCP marketplace. Agents search the catalog by problem or
keyword; every result carries transparent match reasons, the product's status,
and its Eclipse Test Bench certification state — verdict, certified scope,
and the not-tested list — or an explicit statement that no verdict exists yet.

## Who it is for
AI agents (and their builders) choosing tools: discovery by the problem to
solve, with certification receipts instead of registry metadata alone.

## Status
The live Eclipse Bazaar catalog: 156 first-party CETech MCP servers,
connectors, and tools (seeded from each product's `bazaar-manifest.json`
and the latest Test Bench scorecards — no invented products or verdicts).
This server is the catalog face — search, comparison, and certification
lookup; it has no purchasing tools. Priced Bazaar items are purchasable
via the bench-order/intake path at eclipsebazaar.com. Third-party
listings are not yet open.

Catalog snapshot: <img src="../seal-certified.svg" width="20" alt="Cyan Eclipse Certified"> Agent Wallet CERTIFIED(sandbox), CertBridge
CERTIFIED(staging), HostBridge CERTIFIED(simulator), Eclipse Connect
CERTIFIED(dogfood), White Report MCP PARTIAL (logic-level); AgentReady,
Florida Bid Intel and this server not yet certified (bench pending); six
spec-stage products (BidMatrix, Section 508 Evidence, FedScope, MCP Health
Check, Legacy Recon, Eclipse Mail) are labelled `spec`, `certified: false`.

## Quick start
```bash
python3 server.py        # MCP over stdio, stdlib only
python3 smoke_test.py    # 9 protocol/routing/honesty checks
```
