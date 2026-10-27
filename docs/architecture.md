# Architecture

Single-file stdlib Python MCP server (`server.py`) over stdio.

- **Catalog** — `catalog.json`, built from real sources only: each product's
  `bazaar-manifest.json`, the latest Test Bench scorecard, the MCP product
  slate, and the Eclipse Mail spec.
- **Ranking** — keyword ranking over names/capabilities/categories with
  per-hit `match_reasons[]`; problem matching over problem statements +
  capabilities with a fit explanation.
- **Certification reads** — `get_certification` summarises the referenced
  scorecard file live at call time; absence of a verdict is reported
  explicitly, never implied.
- **Data flow** — MCP client → stdio → in-memory catalog → response with
  `data_freshness`. No purchasing path exists in this server — ordering
  runs through the Bazaar's bench-order/intake path at eclipsebazaar.com,
  not through the MCP.
