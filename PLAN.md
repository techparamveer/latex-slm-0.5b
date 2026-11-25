# Plan: building the LaTeX model

Goal: a ~0.5B model that beats its base model on four LaTeX tasks and is small enough to run locally
(llama.cpp / Ollama), e.g. inside a LaTeX editor.

| Task | What it learns | Why it matters |
|---|---|---|
| `fix` | broken LaTeX + compiler log -> fixed LaTeX | most useful in an editor, labels are free |
| `fim` | prefix + suffix -> middle | inline autocomplete, labels are free |
| `gen` | English request -> LaTeX | "write me a table / align block" |
| `conv` | Markdown -> LaTeX | paste-from-notes |

Priority if time runs short: `fix` > `fim` > `gen` > `conv`.

---

## Phase 0: Lock the yardstick (before training anything)
- [ ] Freeze the test set: 200 examples per task from TEST papers only (`05_eval.py` already does this).
- [ ] Write 50 hand-made "real user" prompts in `eval/real_prompts.jsonl` (actual errors you have hit, real
      requests). Synthetic tests alone can flatter the model.
- [ ] Baseline numbers: run `05_eval.py` on `Qwen/Qwen2.5-Coder-0.5B-Instruct` (and 1.5B for reference).
- Gate: `outputs/eval/results.md` has a base column.

## Phase 1: Smoke run on Colab (day 1)
- [ ] Colab: GPU runtime, `GITHUB_TOKEN` secret, run the notebook with `--max_papers 200`.
- [ ] Fix whatever breaks (TRL/transformers arg names, TeX packages missing). Commit fixes.
- [ ] Record the snippet compile pass rate from `data/stats.json`.
- Gate: all 6 steps run end to end on tiny data, numbers are produced (quality irrelevant).

## Phase 2: Data v1 (days 2-3)
- [ ] Scale to ~3,000 papers. Targets: fix 10k, fim 10k, gen 8k, conv 5k.
- [ ] If compile pass rate < 30%: inspect 20 failures, improve extraction (macro expansion, missing packages).
      Never loosen the compile check itself.
- [ ] Descriptions for `gen` with Claude Haiku (set `ANTHROPIC_API_KEY`), fallback local Qwen 1.5B.
- [ ] Manually read 30 random samples per task. Delete fault types that produce unrealistic errors.
- [ ] Leakage check passes (automatic in `03_build_tasks.py`).
- Gate: counts within 30% of targets, samples look right to a human.

## Phase 3: Train v1 (day 4)
- [ ] 30-step smoke train, then full run: LoRA r=32, lr 2e-4, 2 epochs, max_len 2048, `--resume`.
- [ ] Estimated a few hours on a T4 (unmeasured); checkpoints on Drive survive disconnects.
- [ ] Eval tuned vs base on the frozen test set + real prompts.
- Gate (v1 success): `fix` compile rate +20 points over base, `fim` similarity up, no task worse than base.

## Phase 4: Error analysis and iterate (days 5-7)
- [ ] Bucket 50 failures per task (wrong fix, hallucinated packages, truncated output, over-editing).
- [ ] Data fixes, in order of expected payoff:
  1. Real-world errors: mine tex.stackexchange "doesn't compile" Q&A into extra `fix` examples.
  2. Multi-error and whole-document `fix` examples (not just snippets).
  3. Rebalance the task mix toward whichever task lags.
- [ ] Ablations (one change at a time): task mix, LoRA rank 16/64, 0.5B vs 1.5B, 1 vs 3 epochs.
- Gate: each change kept only if it improves the frozen eval.

## Phase 5: Ship (week 2)
- [ ] Merge the best adapter, export GGUF (Q8_0 and Q4_K_M), test with llama.cpp / Ollama.
- [ ] Measure latency on the Mac (tokens/s, time to first token) for autocomplete use.
- [ ] Optional: wire it into a LaTeX editor as local fix/autocomplete, with a frontier model as fallback.
- [ ] Model card: data sources + licences, eval table, known failure modes.

---

## Who does what (agents)
All four clients have `colab-mcp` configured. The Colab MCP attaches to one Colab notebook in the browser,
so let **one agent drive Colab at a time**:
- Colab driver (Claude Code): runs notebook cells, training, eval, reports numbers.
- Code agents (Codex / Cursor / Grok in T3 worktrees): data-quality fixes, new fault types, eval scripts.
  Each change on its own branch, merged only with before/after eval numbers.

## Rules
- Real numbers only. If something failed, report the error.
- Test papers never enter training. Split is by paper hash.
- Don't commit `data/`, `outputs/`, or secrets.
