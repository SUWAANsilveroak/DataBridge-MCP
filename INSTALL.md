# Installing the Universal Data MCP extension (for teammates)

This lets Claude Desktop read our Google Sheets safely (read-only). It takes
about **2 minutes** and you need **nothing installed** — the extension carries
its own Python inside it.

## 1. Download the file for your computer

Get the bundle that matches your OS (ask the maintainer for the link/location):

| Your computer | File to download |
|---------------|------------------|
| **Windows** | `local-data-mcp-windows.mcpb` |
| **Mac (Apple Silicon — M1/M2/M3/M4)** | `local-data-mcp-macos-arm64.mcpb` |
| **Linux** | `local-data-mcp-linux.mcpb` |

> Not sure if your Mac is Apple Silicon? Apple menu →  **About This Mac**. If the
> chip says "Apple M…", it's Apple Silicon. (Intel Macs aren't covered yet — ask
> the maintainer.)

## 2. Install it in Claude Desktop

1. Open **Claude Desktop**.
2. Go to **Settings → Extensions**.
3. **Drag the `.mcpb` file onto the window** (or click **Advanced settings →
   Install Extension** and pick the file).
4. When it asks, keep it **Enabled**.

## 3. Add your Google Sheet

1. Still in **Settings → Extensions**, click **Configure** on *Universal Data
   MCP*.
2. In **Google Spreadsheet ID**, paste **just the ID** from your sheet's URL —
   the part between `/d/` and `/edit`:

   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit#gid=0
                                           ^^^^^^^^^^^^^^
   ```
   Paste only `THIS_IS_THE_ID` — not the whole URL.
3. Click **Save**.

## 4. Sign in to Google (first time only)

1. Open a **new chat** in Claude Desktop.
2. Type: **"list the tabs in my sheet"** (or *"sign in to Google"*).
3. Claude will ask to run a tool — **approve** it. A **browser window opens** —
   pick your Google account and click through the consent screen.
4. That's it. Claude can now read the sheet. Your sign-in is yours alone.

> If you see an **"unverified app"** warning during sign-in, that's expected
> while we're testing — the maintainer must add your Google account as a
> **test user** first. Ping them if you're blocked.

## 5. (Optional) Stop the approval pop-ups

If Claude keeps asking permission on every action: **Settings → Extensions →
Configure → Tool permissions**, and set the tools to **Allow always**. This is
safe — every tool in this extension is **read-only** (it can never change or
delete your data).

## Troubleshooting

- **"Server disconnected" right after install** → you probably grabbed the wrong
  OS file. Re-download the one matching your computer from the table above.
- **Sign-in won't complete / "app not verified"** → your Google account needs to
  be added as a test user; contact the maintainer.
- **"Spreadsheet not found"** → the ID field likely has the whole URL or extra
  characters. Paste only the ID (step 3).
