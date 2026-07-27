# Universal Local Data MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
lets LLM clients such as Claude Desktop interact with local data sources
through **safe, validated tools** — instead of handing the model raw database
or file access.

> **Status:** early development. Google Sheets works end-to-end (discovery,
> schema, read, and search tools) over an OAuth read-only connection, and the
> server ships as a one-click **Desktop Extension** (`.mcpb`). More data-source
> adapters (Google Docs, SQLite, CSV, JSON, Excel, Markdown, …) come next.

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

## Install as a Desktop Extension (recommended for teammates)

The easiest way to use this server in Claude Desktop is the packaged
**Desktop Extension** (`.mcpb`) — no Python setup, no virtualenv, no editing
JSON. The bundle vendors the package and all its dependencies, so a teammate
only needs Claude Desktop.

1. Get the bundle file `local-data-mcp.mcpb` (built by the maintainer — see
   *Building the extension* below).
2. In Claude Desktop: **Settings → Extensions**, then drag the `.mcpb` file
   onto the window (or **Advanced settings → Install Extension** and pick it).
3. In the extension's **Configure** screen, paste your **Google Spreadsheet
   ID** — the string in the sheet's URL between `/d/` and `/edit` (just the ID,
   not the whole URL). Click **Save**.
4. Open a chat and ask for your sheet (e.g. *"list the tabs in my sheet"*).
   The first time, Claude runs the `google_sign_in` tool: a browser opens for
   consent, then the data tools work. Your personal token is saved under
   `%USERPROFILE%\.local-data-mcp\token.json` — each teammate signs in as
   themselves.

To stop being prompted for approval on every call, open the extension's
**Configure → Tool permissions** and set the tools to **Allow always** — safe
here because every tool is **read-only**.

> **Two caveats for a wider rollout:**
> - The bundle includes a **compiled dependency** (`pydantic-core`), so it is
>   **OS-specific** — a bundle built on Windows is for Windows teammates. Build
>   once per OS.
> - Sign-in uses the maintainer's Google **OAuth client**. While that client's
>   consent screen is in *testing*, each teammate's Google account must be added
>   as a **test user** in the Google Cloud Console (or the app must be published
>   / made *Internal* to the organization). No code changes — just consent-screen
>   configuration.

## Using it from Claude Desktop (manual / development)

For local development you can skip the extension and point Claude Desktop
directly at your virtualenv. Add an entry to your `claude_desktop_config.json`,
pointing at the Python interpreter inside your virtual environment:

```json
{
  "mcpServers": {
    "universal-local-data": {
      "command": "C:\\Users\\Dell\\OneDrive\\Attachments\\Desktop\\MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "local_data_mcp"],
      "env": {
        "LOCAL_DATA_MCP_GOOGLE_SHEETS_ID": "your-spreadsheet-id-here"
      }
    }
  }
}
```

Restart Claude Desktop, then ask it to call the `server_info` tool. With a
`LOCAL_DATA_MCP_GOOGLE_SHEETS_ID` set (and after authorizing), the spreadsheet
appears as a source named `gsheets` — try `list_resources` then `read_rows`.

## Configuration

The server is configured through environment variables (namespaced with the
`LOCAL_DATA_MCP_` prefix). All are optional and have sensible defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_DATA_MCP_LOG_LEVEL` | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` (case-insensitive). |
| `LOCAL_DATA_MCP_GOOGLE_CREDENTIALS_FILE` | `credentials.json` | Path to the OAuth client secrets file from Google Cloud Console. |
| `LOCAL_DATA_MCP_GOOGLE_TOKEN_FILE` | `token.json` | Path where the user's OAuth token is saved after authorizing. |
| `LOCAL_DATA_MCP_GOOGLE_SHEETS_ID` | *(unset)* | ID of a Google Spreadsheet to expose (the string in its URL between `/d/` and `/edit`). If unset, no Sheets source is registered. |

Logs are written to **stderr**, never stdout — stdout is reserved for the MCP
protocol. When run from Claude Desktop, log output appears in the client's MCP
server logs.

## Authorizing with Google (one-time)

Google access is split into a one-time interactive sign-in and silent runtime
use (the server refreshes the token automatically afterwards).

1. In the Google Cloud Console, enable the **Google Sheets API** and **Google
   Docs API**, configure an **External** OAuth consent screen (add yourself as a
   test user), and create an **OAuth client ID → Desktop app**. Download its
   JSON and save it as `credentials.json` in the project root.
2. Sign in once, either way:
   - **From your MCP client (recommended):** run the **`google_sign_in`** tool —
     a browser opens for consent, and the Google sources become usable
     immediately, no restart.
   - **From a terminal:** `python -m local_data_mcp.google_workspace.auth`

   Either writes `token.json`, which the server then uses and refreshes
   automatically. **Neither `credentials.json` nor `token.json` is committed** —
   both are git-ignored.

The app requests only **read-only** scopes (`spreadsheets.readonly`,
`documents.readonly`) and no Google Drive access.

**Switching to an organization account later** requires no code changes: point
`LOCAL_DATA_MCP_GOOGLE_CREDENTIALS_FILE` at the org's OAuth client file (or
replace `credentials.json`) and re-run the authorize command.

## Running the tests

```powershell
pytest
```

## Building the extension (maintainer)

The `.mcpb` bundle is produced by a build script that vendors the package and
every dependency, then packs the result with the `mcpb` CLI (fetched via `npx`,
so Node must be on `PATH`):

```powershell
python scripts/build_extension.py
```

This writes `dist/local-data-mcp.mcpb`. The script assembles a staging
directory (`build/extension/`) containing:

- `manifest.json` — copied from `extension/manifest.json`; declares the run
  command, environment wiring, and the single `sheets_id` user-config field
  Claude renders as a form.
- `credentials.json` — the OAuth client, bundled so teammates don't each need
  their own (git-ignored in the repo; must be present at the project root when
  you build).
- `server/` — the package **plus all dependencies**, installed via
  `pip install --target` so the end user needs no `pip install`.

The manifest wires paths with extension variables: `${__dirname}` (the
installed bundle dir) for the code and credentials, and `${HOME}` for the
per-user token, so each teammate's sign-in is isolated.

## Available tools

| Tool | Input | Description |
|------|-------|-------------|
| `server_info` | none | Returns the server's name, version, and status. A health check. |
| `list_sources` | none | Lists the data sources this server exposes. |
| `list_resources` | `source` | Lists the resources (tables, sheets, documents) in a given source. |
| `read_rows` | `source`, `resource`, `limit` | Reads up to `limit` rows (1–1000, default 100) from a tabular resource, as header-keyed dicts. |
| `get_schema` | `source`, `resource` | Returns a tabular resource's column names (normalized) without reading rows. |
| `find_resources` | `source`, `query` | Finds resource names matching a query (case-insensitive) — locate the right tab among many. |
| `search_rows` | `source`, `resource`, `query`, `limit` | Returns rows whose any cell contains the query (scans up to 1000 rows). |
| `google_sign_in` | none | Opens the Google consent browser (one-time) and saves your token; run once before reading Google data. |

## Project layout

```
src/local_data_mcp/
  __init__.py         # package + single-source-of-truth __version__
  __main__.py         # `python -m local_data_mcp` entry point
  server.py           # builds the MCP server, registers tools, runs stdio
  config.py           # typed, env-driven Settings model
  logging_config.py   # stderr logging setup
  errors.py           # domain exceptions
  search.py           # pure matching helpers for the search tools
  adapters/           # the data-source abstraction
    base.py           #   DataSourceAdapter — the contract (ABC)
    capabilities.py   #   SupportsTabularRead — opt-in read capability
    registry.py       #   AdapterRegistry — holds & looks up adapters
    memory.py         #   InMemoryAdapter — reference implementation
  google_workspace/   # Google integration
    auth.py           #   OAuth: authorize (interactive) + load (silent)
    sheets.py         #   GoogleSheetsAdapter — reads one spreadsheet
tests/                # one test module per source module
extension/
  manifest.json       # Desktop Extension manifest (run command + config UI)
scripts/
  build_extension.py  # vendors deps + packs the .mcpb bundle
```

## Architecture: the adapter pattern

The MCP tools never talk to a concrete data source. They talk to an
**`AdapterRegistry`**, which hands back objects implementing the
**`DataSourceAdapter`** contract. Adding a new source (Google Sheets, SQLite,
CSV, …) means writing a new adapter class and registering it — **no existing
code changes.** That is the Open/Closed Principle in action, and it is what
makes this server "universal" rather than tied to one storage format.
