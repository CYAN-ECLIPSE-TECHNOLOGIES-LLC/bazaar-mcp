# Installation

Requirements: Python 3, standard library only.

```bash
git clone https://github.com/cetech-ai/bazaar-mcp.git
cd bazaar-mcp
python3 server.py
```

Point any stdio MCP client at `python3 /path/to/bazaar-mcp/server.py`.
The catalog ships as `catalog.json` beside the server (see Configuration).
Scorecard summaries are read live from `../test-bench/results/` when present.
