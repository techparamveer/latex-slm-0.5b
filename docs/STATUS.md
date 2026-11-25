# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 07:35 UTC
- **Phase:** A smoke is done. EXP-002 snippets are compile-filtered. Task build is running.
- **Branch / commit:** `grok/train`. This status update is the next commit.
- **Running now:** Colab pid 156848, `python3 -u scripts/03_build_tasks.py --data data/arxiv-1500 --describer context --workers 2 --n1 800 --n2 1500 --n3_per_doc 2 --n3_max 2000 --n4 800`. Session on MCP port 50531 is connected. No new tab. At 3 seconds the log showed `T1 fix: 1/800` at 1.84 s/it, tqdm remaining 24:29. `leakage check passed` has not printed. Pid 40018 is gone.
- **Latest numbers:** No new eval. EXP-001 (`results/EXP-001/`, train commit `f54f396`), all 12 test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. EXP-002 log printed `compile pass rate: 66.0% (23038/34890)`. stats.json: papers 1500, extracted 34890, compiled_ok 23038, pass_rate 0.6603038119805101. MinHash `34987 -> 34890`. Smoke pass rate remains 58.4% (2732/4678). 30-step `train_loss` 0.4748. GPU Tesla T4.
- **Next step:** Leave pid 156848 running. Do not train until the log prints `leakage check passed`.
- **Blockers:** Drive is still unmounted.
- **Questions for the user:** none.
