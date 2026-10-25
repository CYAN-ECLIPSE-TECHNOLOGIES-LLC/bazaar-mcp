# Usage — tool reference

| Tool | What it does |
|---|---|
| `search_products(query, category?)` | Ranked keyword search across names, capabilities, categories; every hit carries `match_reasons[]`. |
| `find_solutions(problem)` | Problem-first matching with a fit explanation plus status/certification badges. |
| `get_product(id)` | Full entry including the certification block and what was NOT tested. |
| `compare_products(ids[])` | Side-by-side: status, pricing model, certification, platforms. |
| `get_certification(id)` | Latest bench verdict + live scorecard summary (check counts, environment, date) + certified scope + `not_tested`; returns an explicit "NOT YET CERTIFIED" when none exists. |
| `list_categories()` | Categories with counts by status. |

Every response includes a `data_freshness` note (catalog build date + source
references). Spec-stage products report `status: spec` and `certified: false`.
