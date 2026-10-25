# Configuration

| Variable | Meaning |
|---|---|
| `BAZAAR_CATALOG` | Path to the catalog JSON. Default: `catalog.json` beside `server.py`. |

Scorecard summaries are read at call time from `../test-bench/results/`
(relative to the server location) when that directory exists. No secrets,
no network configuration.
