# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 05:05 UTC
- **Phase:** A smoke is done (Gate A). Next corpus step is running: 1,500 arXiv papers into `data/arxiv-1500`, not overwriting the 200-paper smoke set.
- **Branch / commit:** `grok/train`. VM has `7cbe41d` unpacked; later docs commits may not be on the VM yet. This status update is the next commit.
- **Running now:** Colab pid 40018, `python3 -u scripts/02_build_snippets.py --max_papers 1500 --workers 2 --out data/arxiv-1500`, started on the existing session (MCP port 50531, websocket connected). Log `/content/latex-slm/outputs/EXP-002/02_build_snippets.log` was still 0 bytes a few seconds after start. No second notebook tab was opened.
- **Latest numbers:** Smoke, 200 papers: compile pass rate 58.4% (2732/4678). Leakage check passed. 30-step train `train_loss` 0.4748, runtime 263.9 s. Eval `--n 20` (fix 3, gen 1, fim 5, conv 3): tuned vs base compile rate fix 0.667 vs 0.667, gen 1.000 vs 0.000, conv 1.000 vs 0.000. fim similarity 0.134 vs 0.185. GPU cell after reconnect: `python 3.13.16`, `torch 2.14.1+cu130 cuda True`, `gpu Tesla T4`. The 1,500-paper run has no pass rate yet.
- **Next step:** When pid 40018 prints a compile pass rate, build tasks from `data/arxiv-1500` only, require `leakage check passed`, then train. Do not open another Colab tab.
- **Blockers:** Drive is still unmounted. `/content/latex-slm/{data,outputs}` disappears if this runtime disconnects.
- **Questions for the user:** none.
