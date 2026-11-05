# Installation

Requirements: Python 3.10+, standard library only for the server
itself. The published package is `eclipse-bazaar` on PyPI:

```bash
uvx eclipse-bazaar          # run the MCP server via uvx
# or
pip install eclipse-bazaar  # provides the `bazaar` CLI + Python SDK
```

## Claude Desktop

Current Claude Desktop has no "Developer" menu. To add a local MCP
server:

1. Open **Settings → Desktop app → Extensions (Manage) → Local MCP
   servers → Edit config**.
2. Add an entry to the `mcpServers` object, for example:

   ```json
   { "mcpServers": { "eclipse-bazaar": { "command": "uvx", "args": ["eclipse-bazaar"] } } }
   ```

3. Save the file and restart Claude Desktop. The Bazaar tools appear
   in the new session.

## Running from a checkout

```bash
git clone https://github.com/CYAN-ECLIPSE-TECHNOLOGIES-LLC/bazaar-mcp.git
cd bazaar-mcp
python3 server.py
```

Point any stdio MCP client at `python3 /path/to/bazaar-mcp/server.py`.
The catalog ships as `catalog.json` beside the server (see
Configuration). Scorecard summaries are read live from
`../test-bench/results/` when present.

## Container note (Docker)

If the Bazaar runs inside a Docker container, `bazaar check` discovers
client configs **inside the container only** — it cannot see the host
machine's Claude Desktop config. To check a host config from a
container, mount or copy the file in and pass it explicitly:

```bash
bazaar check --config /path/inside/container/claude_desktop_config.json
```
