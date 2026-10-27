# eclipse-bazaar

mcp-name: io.github.CYAN-ECLIPSE-TECHNOLOGIES-LLC/bazaar

**Eclipse Bazaar is Cyan Eclipse Technologies' marketplace** for its own
bench-verified MCP servers, connectors, and tools (147 listings). Every
listing is a Cyan Eclipse Technologies product today — third-party
listings are not yet open — and every listing carries its Test Bench
verdict and scope, or states plainly that it has none. Priced items are
purchasable through the Bazaar's bench-order/intake path at
eclipsebazaar.com (operator-confirmed ordering; no self-serve buy-now).
This package is the Bazaar's agent-facing catalog face; it is not a
general index of every MCP server, and does not claim to be one.

One distribution, three surfaces:

## 1. The Bazaar MCP server

```json
{ "mcpServers": { "eclipse-bazaar": { "command": "uvx", "args": ["eclipse-bazaar"] } } }
```

Six tools — `search_products`, `find_solutions`, `get_product`,
`compare_products`, `get_certification`, `list_categories` — that let an
agent shop by *problem*, with transparent match reasons. Every listing
carries its Test Bench verdict and scope, or states plainly that it has
none; every entry carries a `not_tested` list. A product labelled
spec-stage is a spec, not a product; an uncertified product says so.

Catalog data ships as a stamped snapshot bundled in the wheel, and
verdict summaries ship as a hash-pinned verdict snapshot generated from
the Test Bench cards — an installed run never reads files outside the
package.

## 2. The `bazaar` CLI

```console
$ bazaar search "certificate renewal"
$ bazaar product certbridge-mcp
$ bazaar categories
$ bazaar check            # classify your configured MCP servers
```

`bazaar check` reads your MCP client configs, extracts each configured
server's *identity* (package / image / URL / local path), and joins it
locally against the published Bazaar corpus — downloaded whole and
verified against its sha256 manifest first. Each entry is classified
`CERTIFIED` (listed, Tier-2 verdict on record), `LISTED` (in the
catalog, no verdict yet), `NOT LISTED` (no record — a neutral fact), or
`UNRESOLVABLE` (no identity could be extracted, with the reason).
Version pins that differ from the listed version are flagged as drift.

Privacy, by construction: config `env` **values are never read, copied,
hashed, logged, or transmitted** — the parser redacts them structurally
before anything else runs. There is no telemetry. The check never
executes a configured server and never contacts one.

## 3. The Python SDK

```python
from eclipse_bazaar import Bazaar

bz = Bazaar()                    # bundled snapshot, works offline
bz.search("ssl certificate")     # same ranking/reasons as the MCP tool
bz.get_listing("certbridge-mcp")
bz.check()                       # the Phase-1 standing check, as a dict
```

Optional framework adapters (standard adapter pattern):

```console
$ pip install "eclipse-bazaar[langchain]"   # or [crewai]
```

```python
from eclipse_bazaar.integrations.langchain_tools import make_langchain_tools
tools = make_langchain_tools()
```

## Scope and honesty

- Statuses and verdicts are as of the catalog build date stamped in
  every response (`data_freshness`).
- Spec-stage listings are labelled spec; in-development listings say
  so; absence of a verdict is stated, never implied.
- `bazaar check` v0.1 is Phase 1: it speaks only about listing and
  Tier-2 verdict records. Further record classes join the vocabulary
  only when the underlying records themselves are public.

Powered by Cyan Eclipse Technologies LLC (cetech.ai) — a Veteran-Owned
Small Business. MIT licensed.
