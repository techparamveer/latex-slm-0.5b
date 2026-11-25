# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 15:09 UTC
- **Phase:** A smoke is done. EXP-002 leakage check passed. The free T4 cannot be reattached: Colab reports a GPU usage limit.
- **Branch / commit:** `grok/train`. This status update is the next commit.
- **Running now:** MCP port 50531 is still connected to the existing Helium scratchpad. At 15:09 UTC the same dialog was still up: "Cannot connect to GPU backend. You cannot currently connect to a GPU due to usage limits in Colab." Buttons remained Close and Connect without GPU, plus Pay As You Go. None of those were clicked. No second tab. The bridge was not killed. Last successful train read remains 07:49 UTC: pid 163716 elapsed 09:41, bar `51/234` at 08:54, 10.27 s/it, tqdm remaining 31:19.
- **Latest numbers:** No new eval. EXP-001 (`results/EXP-001/`, train commit `f54f396`), all 12 test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. EXP-002 task build printed `leakage check passed`. sft counts: train fix/gen/fim/conv 503/688/1804/727 (3722 rows), val 21/34/91/33 (179), test 27/25/106/38 (196). Compile pass rate remains `66.0% (23038/34890)`. Smoke pass rate remains 58.4% (2732/4678). 30-step `train_loss` 0.4748 was EXP-001. GPU Tesla T4.
- **Next step:** On each tick, use `aside-cua` on the existing Helium tab whose address has `mcpProxyPort=50531`. Do not call `open_colab_browser_connection` while that port is connected. Do not open a second tab. Do not kill the bridge. If the dialog is the GPU usage limit, do not click Pay As You Go and do not click Connect without GPU. When a free T4 reconnect is offered on that same tab, click it, then read `outputs/EXP-002/04_train.log` before any eval. The VM disk is the only copy of EXP-002; Drive is still unmounted.
- **Blockers:** Colab free GPU usage limit. The resources panel showed zero compute units. Drive is still unmounted. Code cells still do not execute.
- **Questions for the user:** none.
