# Prompt for Claude (with Colab MCP connected)

```
You control a Google Colab GPU runtime through the colab-mcp tools. The repo
techparamveer/latex-slm (private) contains a full pipeline to train a small
LaTeX model. Your job: run it end to end on Colab and report real results.
Work autonomously. Make reasonable assumptions, note them, keep going.

1. In Colab, mount Drive, clone the repo (token is in the Colab secret
   GITHUB_TOKEN), install TeX Live + pandoc and requirements.txt. Follow
   notebooks/colab_pipeline.ipynb cell by cell. Keep data/outputs on Drive.
2. Run scripts/02_build_snippets.py. Report the compile pass rate and counts
   from data/stats.json. If the pass rate is under 30%, investigate with 20
   failing snippets and fix extraction in scripts/common.py (do not loosen the
   compile check).
3. Run scripts/03_build_tasks.py. Inspect 5 random samples per task and check
   they are sensible. Confirm the leakage check passed.
4. Smoke-test training (30 steps), then run the full training with --resume.
   If a session disconnects, reconnect and resume. If an API/arg error comes
   from a TRL/transformers version mismatch, fix the script minimally.
5. Run scripts/05_eval.py for the base model and the tuned model. Report
   outputs/eval/results.md. Show 3 good and 3 bad examples per task.
6. Summarise: dataset sizes, wall time, GPU used, results table, failure
   modes, and the top 3 next improvements. Never fabricate numbers. If
   something failed, say so and show the error.

Rules: never let test papers into training; do not print secrets; commit
script fixes back to a branch named colab-fixes.
```
