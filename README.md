# Universal Local Data MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
lets LLM clients such as Claude Desktop interact with local data sources
through **safe, validated tools** — instead of handing the model raw database
or file access.

> **Status:** early development. Current milestone is the *walking skeleton* —
> a running server that exposes a single `server_info` health-check tool.
> Data-source adapters (SQLite, CSV, JSON, Excel, Markdown, …) come next.

## Why this exists

Giving an LLM direct access to a database or filesystem is risky: it can read
data it shouldn't, or run destructive operations. This server inverts the
model — it exposes a small set of **explicit tools** that are the *only* way in.
Every tool validates its input and only performs the operations we allow.

## Requirements

- Python 3.10+

## Setup

```powershell
# From the project root
python -m venv venv
venv\Scripts\Activate.ps1

# Install the package (editable) plus dev tools
pip install -e ".[dev]"
```

## Running the server

The server speaks the **stdio** transport, so it is normally launched by an MCP
client rather than run by hand. To confirm it starts:

```powershell
python -m local_data_mcp
```

(It will wait silently for a client to connect. Press `Ctrl+C` to stop.)

## Using it from Claude Desktop

Add an entry to your `claude_desktop_config.json`, pointing at the Python
interpreter inside your virtual environment:

```json
{
  "mcpServers": {
    "universal-local-data": {
      "command": "C:\\Users\\Dell\\OneDrive\\Attachments\\Desktop\\MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "local_data_mcp"]
    }
  }
}
```

Restart Claude Desktop, then ask it to call the `server_info` tool.

## Configuration

The server is configured through environment variables (namespaced with the
`LOCAL_DATA_MCP_` prefix). All are optional and have sensible defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_DATA_MCP_LOG_LEVEL` | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` (case-insensitive). |
| `LOCAL_DATA_MCP_GOOGLE_CREDENTIALS_FILE` | `credentials.json` | Path to the OAuth client secrets file from Google Cloud Console. |
| `LOCAL_DATA_MCP_GOOGLE_TOKEN_FILE` | `token.json` | Path where the user's OAuth token is saved after authorizing. |

Logs are written to **stderr**, never stdout — stdout is reserved for the MCP
protocol. When run from Claude Desktop, log output appears in the client's MCP
server logs.

## Authorizing with Google (one-time)

Google access is split into a one-time interactive step and silent runtime use,
because the MCP server itself cannot open a browser.

1. In the Google Cloud Console, enable the **Google Sheets API** and **Google
   Docs API**, configure an **External** OAuth consent screen (add yourself as a
   test user), and create an **OAuth client ID → Desktop app**. Download its
   JSON and save it as `credentials.json` in the project root.
2. Run the one-time authorization (opens a browser, asks you to consent):

   ```powershell
   python -m local_data_mcp.google_workspace.auth
   ```

   This writes `token.json`, which the server then uses automatically and
   refreshes as needed. **Neither `credentials.json` nor `token.json` is
   committed** — both are git-ignored.

The app requests only **read-only** scopes (`spreadsheets.readonly`,
`documents.readonly`) and no Google Drive access.

**Switching to an organization account later** requires no code changes: point
`LOCAL_DATA_MCP_GOOGLE_CREDENTIALS_FILE` at the org's OAuth client file (or
replace `credentials.json`) and re-run the authorize command.

## Running the tests

```powershell
pytest
```

## Available tools

| Tool | Input | Description |
|------|-------|-------------|
| `server_info` | none | Returns the server's name, version, and status. A health check. |
| `list_sources` | none | Lists the data sources this server exposes. |
| `list_resources` | `source` | Lists the resources (tables, sheets, documents) in a given source. |

## Project layout

```
src/local_data_mcp/
  __init__.py         # package + single-source-of-truth __version__
  __main__.py         # `python -m local_data_mcp` entry point
  server.py           # builds the MCP server, registers tools, runs stdio
  config.py           # typed, env-driven Settings model
  logging_config.py   # stderr logging setup
  errors.py           # domain exceptions
  adapters/           # the data-source abstraction
    base.py           #   DataSourceAdapter — the contract (ABC)
    registry.py       #   AdapterRegistry — holds & looks up adapters
    memory.py         #   InMemoryAdapter — reference implementation
tests/                # one test module per source module
```

## Architecture: the adapter pattern

The MCP tools never talk to a concrete data source. They talk to an
**`AdapterRegistry`**, which hands back objects implementing the
**`DataSourceAdapter`** contract. Adding a new source (Google Sheets, SQLite,
CSV, …) means writing a new adapter class and registering it — **no existing
code changes.** That is the Open/Closed Principle in action, and it is what
makes this server "universal" rather than tied to one storage format.
