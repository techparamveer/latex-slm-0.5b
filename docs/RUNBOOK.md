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

## Local Mac TeX (user install, 2026-11-25)

Full MacTeX was not installed. BasicTeX's installer needs an admin password. TinyTeX is TeX Live 2026 in the home directory:

```
export PATH="$PATH:$HOME/Library/TinyTeX/bin/universal-darwin"
latex --version   # pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026)
```

That line is in `~/.zshrc`. `compile_one` of a one-line equation returned true after `tlmgr install` of the preamble packages.

## Environment (fill in with exact versions)
| Thing | Version |
|---|---|
| Colab runtime / GPU | Tesla T4, free tier. Measured 2026-11-25 on the reconnected runtime (cell `MtjtYD6szRfK`): `python 3.13.16`, `torch 2.14.1+cu130 cuda True`, `gpu Tesla T4`, `nvidia-smi -L` → `GPU 0: Tesla T4`. The runtime-type dialog had T4 GPU selected. Host RAM shown in the UI at connect: 12.67 GB. |
| Python | 3.13.16 |
| torch | 2.14.1+cu130 |
| transformers | 5.22.1 |
| trl | 1.18.2 |
| peft | 0.21.2 |
| bitsandbytes | 0.50.2 |
| torchao | 0.18.0 (peft 0.21.2 refused the preinstalled 0.10.0) |
| TeX Live | 2023/Debian. `pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian)` |
| pandoc | 3.1.3 |

## Discord updates

After a measured update, post the provider and the base-vs-tuned summary:

```
python3 scripts/notify_discord.py \
  --provider "Kaggle, two Tesla T4s" \
  --results results/EXP-001 \
  --exp EXP-007 \
  --commit f54f396 \
  --note "one sentence on what just finished"
```

The URL is `DISCORD_WEBHOOK_URL` or `~/.config/latex-slm/discord_webhook` (mode 600). It is not in git. A finished eval is an embed: a plain-English summary, a PNG of the base-vs-tuned bars, then the numeric lines, with the provider in the footer. While training is still running, post status only and do not attach an older chart:

```
python3 scripts/notify_discord.py --status \
  --provider "Kaggle, one Tesla T4. Colab is not connected." \
  --exp EXP-008 \
  --note "One model is under training. The other T4 is idle."
```

With no URL the script prints `discord notify skipped: no webhook configured` and exits 0. `--dry-run` prints the text and does not post.

## Kaggle

Use this when the Colab session has no free GPU. The account is already logged in as `techparamveer` in the existing Helium window. Drive that window with `aside-cua`. Stay on one Helium window.

Measured 2026-11-27 while creating the notebook:

1. The open tab was `https://www.kaggle.com/code/techparamveer/latex-slm/edit` (draft title `latex-slm`).
2. Session options offered accelerator `None`, `GPU T4 x2`, and `TPU v5e-8`. A single T4 was not in the list. `GPU T4 x2` was turned on. The confirm dialog said availability is limited to 30 hours per week and that 30 hours remained. Internet was already on. Persistence was set to `Files only`.
3. On the Mac, after committing:

```
python3 scripts/make_colab_sync_cell.py --dest /kaggle/working/latex-slm --no-drive > /tmp/kaggle_sync_cell.py
```

Paste that file into the first notebook cell. `aside-cua set` rejected the cell (`invalid_argument`). Clipboard paste (`pbcopy`, then Command-A, Command-V in the cell) worked. Append this so the same run also installs and downloads the model:

```
import runpy
runpy.run_path(DST + "/scripts/kaggle_setup.py", run_name="__main__")
```

4. Run the cell. Measured on the draft session at commit `cb59fe3`: `synced commit cb59fe3 to /kaggle/working/latex-slm`, `nvidia-smi -L` listed two `Tesla T4` devices, `cuda True`, `count 2`, and `model /kaggle/working/models/Qwen2.5-Coder-0.5B-Instruct`. Python on that image is 3.13. The cell does not start `04_train.py`.

TeX Live is not installed by that script. The Colab apt line in section 2 is the compile install when a session is up.

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

Smoke on the 2026-11-25 T4 VM, from `/content/latex-slm`, after the installs above. Drive was not mounted.

```
python -u scripts/02_build_snippets.py --max_papers 200 --workers 2
python -u scripts/03_build_tasks.py --n1 60 --n2 60 --n3_per_doc 1 --n3_max 40 --n4 40 --describer context
python -u scripts/04_train.py --model Qwen/Qwen2.5-Coder-0.5B-Instruct --max_steps 30 --out outputs/EXP-001/train
python -u scripts/05_eval.py --model Qwen/Qwen2.5-Coder-0.5B-Instruct --tag base --n 20 --out outputs/EXP-001/eval
python -u scripts/05_eval.py --model outputs/EXP-001/train/merged --tag tuned --n 20 --out outputs/EXP-001/eval
```

`03` printed `leakage check passed` before `04` was started. Measured results are in `results/EXP-001/`.

## 4. Bake-off, training, eval
(to be filled)
