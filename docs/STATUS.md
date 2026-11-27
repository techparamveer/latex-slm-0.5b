# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-27 12:31 UTC
- **Automation:** The 10-minute loop checks the existing Colab session first. If that session has no free GPU, it uses `aside-cua` on the existing Helium window and runs the Kaggle notebook `https://www.kaggle.com/code/techparamveer/latex-slm/edit`. On the Colab usage-limit dialog, leave Close, Connect without GPU, and Pay As You Go unclicked. The schedule is paused until the user turns it on. The same order is in `AGENTS.md`.
- **Phase:** A smoke is done. EXP-008 is running on Kaggle: TeX install, then a 1500-paper rebuild, then training only if the leakage check passes.
- **Branch / commit:** `grok/train`. The notebook is unpacked at `cb59fe3`. This status update is the next commit.
- **Running now:** A Composer 2.5 check at 12:31 UTC measured the Kaggle draft session still running (`Running Draft Session (17m)`). The EXP-008 cell help text was still `Cell execution started at 12:22pm`. No stdout from that cell was in the accessibility tree. The setup cell was still `Cell executed in 21.405s at 12:14pm`, with `synced commit cb59fe3` and two Tesla T4 lines, `cuda True`, count 2. Quota text was not visible on this check. `colab_status` was `connected: false`, `websocket_live: false`, port `55783`. The Helium window title was the Kaggle notebook; no Colab tab was read. `open_colab_browser_connection` was not called. The 10-minute loop stays paused.
- **Latest numbers:** No new eval. Latest finished eval is EXP-007, stored in `results/EXP-001/`, train commit `f54f396`, all 12 synthetic test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. FIM similarity is still below the base. No real-test JSON is in `results/`.
- **Next step:** Leave this Kaggle cell running. Read `outputs/EXP-008/run.log` for the compile pass rate, then `leakage check passed`, then the train bar. Do not start a second build. Do not click Pay As You Go.
- **Blockers:** Colab still has no free GPU. EXP-008 has not printed a pass rate or a loss yet. TeX Live was not installed before this cell.
- **Questions for the user:** None. The loop is still paused.
