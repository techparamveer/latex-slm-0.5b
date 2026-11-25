# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 06:29 UTC
- **Phase:** A smoke is done. EXP-002 is still compile-filtering.
- **Branch / commit:** `grok/train`. This status update is the next commit.
- **Running now:** Colab pid 40018, elapsed 01:30:11, `python3 -u scripts/02_build_snippets.py --max_papers 1500 --workers 2 --out data/arxiv-1500`. Session on MCP port 50531 is connected. No new tab. Compile bar: 598/1091 at 1:24:38, tqdm remaining 1:01:39. `stats.json` does not exist yet.
- **Latest numbers:** No new eval. EXP-001 (`results/EXP-001/`, train commit `f54f396`), all 12 test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. Extract: 34987 snippets from 1500 papers, MinHash 34987 → 34890. Pass rate not printed. Smoke pass rate remains 58.4% (2732/4678). 30-step `train_loss` 0.4748. GPU Tesla T4.
- **Next step:** Leave pid 40018 running. When the log prints a compile pass rate, build tasks from `data/arxiv-1500` only and require `leakage check passed` before training.
- **Blockers:** Drive is still unmounted.
- **Questions for the user:** none.
