# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 07:40 UTC
- **Phase:** A smoke is done. EXP-002 leakage check passed. A two-epoch train is running.
- **Branch / commit:** `grok/train`. This status update is the next commit.
- **Running now:** Colab pid 163716, elapsed 01:14, `python3 -u scripts/04_train.py --data data/arxiv-1500/sft --out outputs/EXP-002/train --epochs 2`. Session on MCP port 50531 is connected. No new tab. Log printed `train=3722 val=179 bf16=False warmup_steps=7`. Bar `3/234` at 00:29, 9.56 s/it, tqdm remaining 36:48. GPU Tesla T4.
- **Latest numbers:** No new eval. EXP-001 (`results/EXP-001/`, train commit `f54f396`), all 12 test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. EXP-002 task build printed `leakage check passed`. sft counts: train fix/gen/fim/conv 503/688/1804/727 (3722 rows), val 21/34/91/33 (179), test 27/25/106/38 (196). Compile pass rate remains `66.0% (23038/34890)`. Smoke pass rate remains 58.4% (2732/4678). 30-step `train_loss` 0.4748 was EXP-001. GPU Tesla T4.
- **Next step:** Leave pid 163716 running. When the train log finishes, eval the base and the new merged model on `data/arxiv-1500/sft`. Do not start a second GPU job.
- **Blockers:** Drive is still unmounted.
- **Questions for the user:** none.
