# Notes for coding agents

- Goal: train a small LaTeX model (see README.md). Pipeline lives in scripts/, numbered in run order.
- Compile checks always go through `scripts/common.py: compile_one`. Do not add a second definition of "compiles".
- Splits are by paper (hash of arXiv id). Never create splits at snippet level.
- Do not commit data/, outputs/ or secrets. Keys come from Colab secrets or env vars.
- GPU order: free Colab T4 first. If that session has no free GPU, use `aside-cua` on the existing Helium window and the logged-in kaggle.com account. Procedure: `docs/RUNBOOK.md` section "Kaggle".
- Report real measured numbers only.
