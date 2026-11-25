# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 05:00 UTC
- **Phase:** A complete for the smoke pipeline (Gate A). Drive is still unmounted. A larger arXiv pull has not started.
- **Branch / commit:** `grok/train` at `f54f396` on the VM. Docs for this eval are the next commit.
- **Running now:** nothing. Pid 9334 finished on its own. Train pid 31733 finished 30/30. Eval pid 34792 finished.
- **Latest numbers:** compile pass rate 58.4% (2732/4678) on 200 papers. Leakage check passed. 30-step train: `bf16=False`, `train_loss` 0.4748, runtime 263.9 s. Eval `--n 20` used every test row (fix 3, gen 1, fim 5, conv 3). Tuned vs base compile rate: fix 0.667 vs 0.667, gen 1.000 vs 0.000, conv 1.000 vs 0.000. fim similarity 0.134 vs 0.185.
- **Next step:** After this smoke, a later run can raise `--max_papers` and add arXiv parquet parts outside 44-48, still 2018+, paper-level splits, `compile_one`, MinHash. tex.stackexchange stays on `grok/real-test`.
- **Blockers:** Drive is unmounted. VM files under `/content/latex-slm/{data,outputs}` go away if the runtime disconnects. The metric files are copied into `results/EXP-001/`.
- **Questions for the user:** none.
