# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 05:32 UTC
- **Phase:** A smoke is done. Corpus step EXP-002 is still compiling.
- **Branch / commit:** `grok/train`. This status update is the next commit.
- **Running now:** Colab pid 40018, elapsed 31:01, `python3 -u scripts/02_build_snippets.py --max_papers 1500 --workers 2 --out data/arxiv-1500`. Existing session, MCP port 50531, websocket connected. No new tab. Compile bar in `outputs/EXP-002/02_build_snippets.log`: 179/1091 (16%) at 25:18, tqdm ETA about 57:55. Log was 8798 bytes, 144 lines.
- **Latest numbers:** No new eval. Last finished eval is EXP-001 (`results/EXP-001/`), all 12 test rows. Base vs tuned: fix compile 0.667 vs 0.667 (n=3), exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen compile 0.000 vs 1.000 (n=1), exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim exact 0.000 vs 0.000, similarity 0.185 vs 0.134 (n=5); conv compile 0.000 vs 1.000 (n=3), exact 0.000 vs 0.333, similarity 0.676 vs 0.985. Smoke snippet pass rate 58.4% (2732/4678) on 200 papers. 30-step `train_loss` 0.4748. GPU: Tesla T4, torch 2.14.1+cu130, python 3.13.16. EXP-002 has no pass rate yet.
- **Next step:** Leave pid 40018 running. When it prints a compile pass rate, build tasks from `data/arxiv-1500` only, require `leakage check passed`, then train. Do not open another Colab tab.
- **Blockers:** Drive is still unmounted. VM files disappear if the runtime disconnects.
- **Questions for the user:** none.
