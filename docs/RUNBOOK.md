# Runbook

Exact commands to reproduce every artifact from scratch. Keep this runnable: only add steps that worked.

## 0. Connect Colab from the agent (Mac + Helium)

`colab-mcp` opens `https://colab.research.google.com/notebooks/empty.ipynb` and waits for that page to attach a websocket to `localhost`. Three things blocked that on 2026-11-25:

1. The agent browser never rendered Colab's "Connect to a local Colab MCP server" dialog, so the page never attached.
2. Helium's Local Network Access permission for `colab.research.google.com` was still "prompt", so the page could not open a websocket to localhost. Click **Allow** once. It is remembered for that origin.
3. The Cursor MCP client timeout was 30s (`~/.cursor/mcp.json`), shorter than the server's 60s wait, so the client returned MCP `-32001` while the server was still waiting.

Working setup:

- Browser is Helium. Cursor, Codex, Claude Code, and Grok set `BROWSER="open -a Helium %s"` on `colab-mcp`.
- Cursor's client timeout is 120000 ms.
- The command is `uvx --from git+https://github.com/googlecolab/colab-mcp python ~/.local/share/colab-mcp/colab_mcp_visible.py`. The same source is `scripts/colab_mcp_visible.py`.
- Helium Local Network Access for `colab.research.google.com` must be **Allow** (once per origin).

Handshake bug, fixed 2026-11-25 and verified with a client that allows 25s per call: `ColabProxyClient.await_proxy_connection` used `asyncio.wait_for(gather(connection_live.wait(), self._start_task))`. A timeout or a cancelled tool call cancelled that gather and `_start_task` with it. `_start_task` is what builds the MCP session on the websocket. After it was cancelled, every browser connection was accepted and dropped in the same second (`BrokenResourceError` in `_read_from_socket`). The replacement polls and never cancels `_start_task`. `open_colab_browser_connection` waits only `COLAB_UI_WAIT` (15s) so it returns before the client timeout. `colab_status` reports `connected` and `port` (no token). `colab_wait_connected` polls for up to 25s.

Agent sequence:

1. If a `colab-mcp` process is still running from before this file, stop it so the client starts the fixed entry.
2. Call `open_colab_browser_connection` **once**. It opens one Helium tab and returns within 15s.
3. `colab_status` gives the listen port. Click **Connect** on the dialog "Connect to a local Colab MCP server" in the Helium tab whose `mcpProxyPort` equals that port.
4. Poll `colab_wait_connected` until it returns `connected`. Do not call `open_colab_browser_connection` again while waiting. Another call opens another tab.
5. In the notebook: **Runtime → Change runtime type → T4 GPU → Save**, then **Connect** the runtime if it is not already connected.
6. Approve a Google Drive mount the first time it appears.

GPU, Python, and TeX versions below are filled in only after a cell on that runtime has printed them.

## Environment (fill in with exact versions)
| Thing | Version |
|---|---|
| Colab runtime / GPU | |
| Python | |
| torch | |
| transformers | |
| trl | |
| peft | |
| bitsandbytes | |
| TeX Live | |
| pandoc | |

## 1. Get the code onto Colab
```
# on the Mac, in the repo, after committing:
python3 scripts/make_colab_sync_cell.py > /tmp/sync_cell.py
# paste/run /tmp/sync_cell.py as a Colab cell (agents: add it with colab-mcp)
```

## 2. Install
```
!apt-get -qq update && apt-get -qq install -y texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-science pandoc
!pip -q install -r requirements.txt
```

## 3. Data
(to be filled with the exact commands that built each data version)

## 4. Bake-off, training, eval
(to be filled)
