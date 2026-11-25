# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 03:18 UTC
- **Phase:** A (setup and smoke test), blocked on the browser permission
- **Branch / commit:** `grok/train` (docs for the local checks are being committed on top of `f319e20`)
- **Running now:** nothing on GPU
- **Latest numbers:** none yet (no training or eval has run)
- **Next step:** after Local Network Access is allowed, `open_colab_browser_connection`, then `nvidia-smi`, mount Drive, sync `HEAD`, install TeX Live and Python deps, record versions, then the smoke run (`02 --max_papers 200`, `03` with small counts and `--describer context`, `04` for 30 steps on `Qwen/Qwen2.5-Coder-0.5B-Instruct`, `05 --n 20`)
- **Blockers:** Colab scratchpad is open and signed in, in Helium. `local_network_access` for `colab.research.google.com` has no allow entry, and no websocket is connected. Three `open_colab_browser_connection` calls returned MCP `-32001`. `~/.cursor/mcp.json` timeout is now 120000 ms (was 30000). The live client may still be on the old 30s value until it reloads that file.
- **Questions for the user:** In the Colab tab, click **Allow** on the prompt that `colab.research.google.com` wants to access devices on the local network (address-bar icon, or the dialog). Then click **Connect** and set **Runtime → Change runtime type → T4 GPU**. Reply once Allow has been clicked. Free T4 only.
