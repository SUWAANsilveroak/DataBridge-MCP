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

## Running the tests

```powershell
pytest
```

## Available tools

| Tool | Input | Description |
|------|-------|-------------|
| `server_info` | none | Returns the server's name, version, and status. A health check. |

## Project layout

```
src/local_data_mcp/
  __init__.py    # package + single-source-of-truth __version__
  __main__.py    # `python -m local_data_mcp` entry point
  server.py      # builds the MCP server, registers tools, runs stdio
tests/
  test_server.py # tests the tool logic
```
