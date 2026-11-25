# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 17:08 UTC
- **Phase:** A smoke is done. EXP-002 leakage check passed. The free T4 cannot be reattached: Colab reports a GPU usage limit.
- **Branch / commit:** `grok/train`. This status update is the next commit.
- **Running now:** The Colab socket on port 50531 reports `connected: false` and `websocket_live: false`. Two checks, a few seconds apart, agreed. `aside-cua` could not read Helium: `screen_locked`. `open_colab_browser_connection` was not called, because that opens another Helium tab and then needs a Connect click. No bridge process was killed. Last successful train read remains 07:49 UTC: pid 163716 elapsed 09:41, bar `51/234` at 08:54, 10.27 s/it, tqdm remaining 31:19.
- **Latest numbers:** No new eval. EXP-001 (`results/EXP-001/`, train commit `f54f396`), all 12 test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. EXP-002 task build printed `leakage check passed`. sft counts: train fix/gen/fim/conv 503/688/1804/727 (3722 rows), val 21/34/91/33 (179), test 27/25/106/38 (196). Compile pass rate remains `66.0% (23038/34890)`. Smoke pass rate remains 58.4% (2732/4678). 30-step `train_loss` 0.4748 was EXP-001. GPU Tesla T4.
- **Next step:** When the screen is unlocked, observe the existing Helium scratchpad. Do not call `open_colab_browser_connection` while a Colab tab is already open. Do not open a second tab. Do not kill a bridge. If the dialog is still the GPU usage limit, do not click Pay As You Go and do not click Connect without GPU. When a free T4 reconnect is offered on that same tab, click it, then read `outputs/EXP-002/04_train.log` before any eval. The VM disk was the only copy of EXP-002; Drive is still unmounted, so a reclaimed VM means that log is gone.
- **Blockers:** The Colab websocket is down, and the Mac screen is locked, so the notebook cannot be read. Before that, Colab reported a free GPU usage limit. Drive is still unmounted. Code cells still do not execute.
- **Questions for the user:** none.
