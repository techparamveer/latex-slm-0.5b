# Notes for coding agents

- Goal: train a small LaTeX model (see README.md). Pipeline lives in scripts/, numbered in run order.
- Compile checks always go through `scripts/common.py: compile_one`. Do not add a second definition of "compiles".
- Splits are by paper (hash of arXiv id). Never create splits at snippet level.
- Do not commit data/, outputs/ or secrets. Keys come from Colab secrets or env vars.
- Automation GPU order: check the existing Colab session first. If it has no free GPU, use `aside-cua` on the existing Helium window and run training on the logged-in kaggle.com notebook. Procedure: `docs/RUNBOOK.md` section "Kaggle".
- Report real measured numbers only.
- Every reply that reports scores shows one comparison chart of the latest measured eval: bars for base vs tuned, n labeled on each task. Pass the page through `html_preview`, then `html_render`. No title banner and no page background.
- After measured work, post a Discord embed with `scripts/notify_discord.py` when a webhook is configured. Plain English, then the chart, then the numbers. Name the provider. Never commit or print the webhook URL.
