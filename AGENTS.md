# Notes for coding agents (Codex, Cursor, Grok, Claude)

- Goal and roadmap: see PLAN.md. Pipeline lives in scripts/, numbered in run order.
- Compile checks always go through `scripts/common.py: compile_one`. Do not add a second definition of "compiles".
- Splits are by paper (hash of arXiv id). Never create splits at snippet level.
- Do not commit data/, outputs/ or secrets. Keys come from Colab secrets or env vars.
- Only one agent should drive the Colab notebook (colab-mcp) at a time.
- Automation GPU order: check the existing Colab session first. If it has no free GPU, use `aside-cua` on the existing Helium window and run training on the logged-in kaggle.com notebook `https://www.kaggle.com/code/techparamveer/latex-slm/edit`. On the Colab usage-limit dialog, leave Close, Connect without GPU, and Pay As You Go unclicked. Free T4 only. One Helium window. Procedure: `docs/RUNBOOK.md` section "Kaggle".
- Report real measured numbers only. Any data or training change needs before/after eval numbers.
- Document everything as you go (section 3 of `docs/prompts/GROK_TRAIN.md`): `docs/STATUS.md`, `docs/journal/`,
  `docs/EXPERIMENTS.md`, `docs/DECISIONS.md`, `docs/DATA_CARD.md`, `docs/RUNBOOK.md`, `results/EXP-###/`.
- Code reaches Colab via `scripts/make_colab_sync_cell.py` (no tokens in notebooks).
