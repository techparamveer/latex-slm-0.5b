# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 08:09 UTC
- **Phase:** A smoke is done. EXP-002 leakage check passed. Code execution on the Colab runtime is still failing.
- **Branch / commit:** `grok/train`. This status update is the next commit.
- **Running now:** MCP port 50531 is still connected. One retry cell was added and `run_code_cell` timed out at 25s. Execution count stayed null. The cell was deleted. No newer train bar. Last successful read remains 07:49 UTC: pid 163716 elapsed 09:41, bar `51/234` at 08:54, 10.27 s/it, tqdm remaining 31:19. No second tab. The bridge was not killed. This is the fourth failed code execution in a row.
- **Latest numbers:** No new eval. EXP-001 (`results/EXP-001/`, train commit `f54f396`), all 12 test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. EXP-002 task build printed `leakage check passed`. sft counts: train fix/gen/fim/conv 503/688/1804/727 (3722 rows), val 21/34/91/33 (179), test 27/25/106/38 (196). Compile pass rate remains `66.0% (23038/34890)`. Smoke pass rate remains 58.4% (2732/4678). 30-step `train_loss` 0.4748 was EXP-001. GPU Tesla T4.
- **Next step:** Stop until the existing Helium tab's runtime runs code again. Do not open a second tab and do not kill the bridge on port 50531. After a cell executes, read `outputs/EXP-002/04_train.log` before starting an eval.
- **Blockers:** Drive is still unmounted. Code execution has failed four times (180s, 90s, 60s, then 25s at 08:09).
- **Questions for the user:** Reconnect the runtime on the existing Helium tab for port 50531.
