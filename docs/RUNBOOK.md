# Runbook

Exact commands to reproduce every artifact from scratch. Keep this runnable: only add steps that worked.

## 0. Connect Colab from the agent (Mac + Helium)

`colab-mcp` opens `https://colab.research.google.com/notebooks/empty.ipynb` and waits for that page to attach a websocket to `localhost`. Three things blocked that on 2026-11-25:

1. The agent browser never rendered Colab's "Connect to a local Colab MCP server" dialog, so the page never attached.
2. Helium's Local Network Access permission for `colab.research.google.com` was still "prompt", so the page could not open a websocket to localhost. Click **Allow** once. It is remembered for that origin.
3. The Cursor MCP client timeout was 30s (`~/.cursor/mcp.json`), shorter than the server's 60s wait, so the client returned MCP `-32001` while the server was still waiting.

Working setup, verified by a standalone websocket test (Helium completed the handshake, `101 Switching Protocols`, Colab sent `tools/list_changed`):

- Browser is Helium. Each of Cursor, Codex, Claude Code, and Grok sets `BROWSER="open -a Helium %s"` on the `colab-mcp` server so `webbrowser.open` lands in Helium.
- Cursor's `colab-mcp` timeout is 120000 ms.
- If `open_colab_browser_connection` still times out, the running `colab-mcp` process was started before that env change. Restart it (reload MCP / new session) so it inherits `BROWSER`.

Agent sequence:

1. Call `open_colab_browser_connection`. Helium opens the scratchpad.
2. In Helium, click **Connect** on the dialog "Connect to a local Colab MCP server". Notebook tools (`add_code_cell`, `run_code_cell`, and the rest) appear only after that click.
3. In the notebook: **Runtime → Change runtime type → T4 GPU → Save**, then **Connect** the runtime if it is not already connected.
4. Approve a Google Drive mount the first time it appears.

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
