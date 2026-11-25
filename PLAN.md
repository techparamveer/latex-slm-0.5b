# Plan: train the best LaTeX model we can

**North star:** the highest score on our own frozen LaTeX benchmark, for a budget of roughly $50-100 of GPU
time and ~$20 of API calls (estimates). Model size is NOT fixed: we pick it with a bake-off. Expect a 3B-8B
model trained with QLoRA. A smaller distilled version can come later if speed matters.

**Core idea:** LaTeX has a free, exact verifier: the compiler. Every stage uses it: to filter data, to grade
outputs, to pick the best of several samples, and as the reward for reinforcement learning. That is our edge
over generic models.

---

## What the model must do (task suite)

| Task | Input -> output | Data source |
|---|---|---|
| `fix` | broken LaTeX + compiler log -> working LaTeX | injected faults (snippet + full document) + real tex.stackexchange errors |
| `gen` | English request -> LaTeX | real arXiv snippets + teacher-written requests |
| `edit` (new) | LaTeX selection + instruction -> edited LaTeX | programmatic transforms + teacher edits, compile-verified |
| `fim` | prefix + suffix -> missing middle | arXiv documents (free labels) |
| `conv` | Markdown / plain text -> LaTeX | pandoc of real LaTeX, flipped |

Coverage targets inside `gen`/`edit`: math (align, cases, matrices), tables (tabular, booktabs, multirow),
lists, theorem environments, figures/captions/labels, `\newcommand`, BibTeX entries. TikZ is v2.

---

## Phase 0: Build the benchmark first (days 1-2)
Nothing gets trained until we can measure it.
- [ ] **Synthetic test:** 200 per task from TEST papers only (already produced by `03_build_tasks.py`).
- [ ] **Real test (most important):** 100+ real broken documents from tex.stackexchange with accepted
      answers, plus 50 prompts written by us. Stored in `eval/real/`. Never used for training.
- [ ] **Metrics** (extend `05_eval.py`):
  - `compile@1`, and `compile@8` (any of 8 samples compiles)
  - **render match:** compile output and reference, rasterize, compare pixels (catches "compiles but wrong")
  - **minimal edit** for `fix`/`edit`: edit distance to the reference, so the model does not rewrite everything
  - exact match / similarity for `fim`
  - **LLM judge** (Claude) pairwise vs reference on 100 `gen`/`edit` items
- [ ] **Floor and ceiling:** base models (floor) and Claude on the same benchmark (ceiling).
- Gate: one command produces `results.md` with all metrics.

## Phase 1: Base-model bake-off (days 2-3)
- [ ] `N=100 bash scripts/bakeoff.sh`: Qwen2.5-Coder 1.5B/3B/7B, Qwen3 1.7B/4B/8B, plus anything newer.
      Loaded in 4-bit so it runs on a free T4.
- [ ] Pick the winner on **real-test score per GPU-hour**. Keep the best small (~1.5B) model as a fast track
      for ablations.
- Gate: a chosen base model, with the reasons written in `results/bakeoff.md`.

## Phase 2: Data v2, quality over quantity (days 3-6)
- [ ] **Scale the corpus:** 20-30k arXiv papers (2018+), MinHash dedupe, paper-level split, plus a dedupe
      check of training data against the real test set.
- [ ] **fix:** keep the 8 snippet fault types, add **document-level** faults compiled with a full preamble
      (missing `\usepackage`, broken `\newcommand`, unclosed environments across lines, stray `}` in the
      preamble, wrong `\documentclass` options). Mine tex.stackexchange (Stack Exchange data dump) for real
      error -> fix pairs; keep pairs where the fix compiles.
- [ ] **gen:** Claude Haiku writes requests for real snippets; the snippet is the answer.
- [ ] **edit:** programmatic transforms with exact answers (equation->align, itemize->enumerate,
      tabular->booktabs, add row/column, inline->display, `\frac`->`\tfrac`, add label/caption) plus a
      Claude-written set for free-form edits, kept only if they compile and the render check passes.
- [ ] **Teacher distillation:** for hard real-world inputs, Claude (Sonnet/Opus) writes the answer; keep it
      only if it compiles, and record the teacher in `meta` so we can ablate it.
- [ ] Mix target v1: ~60k examples (fix 20k, edit 12k, gen 12k, fim 10k, conv 6k). Read 30 per task by hand.
- Gate: leakage check passes, samples pass human review, counts within 30% of target.

## Phase 3: Supervised fine-tuning (week 2)
- [ ] Ablations on the small fast-track model first (cheap): task mix, data v1 vs v2, teacher data on/off.
- [ ] Full run on the bake-off winner: `04_train.py --qlora`, LoRA r=64 on all linear layers, lr 1e-4,
      2 epochs, max_len 4096, completion-only loss, `--resume`.
- [ ] Hardware: free T4 only for smoke tests. Real runs on an A100/H100 (Colab Pro or RunPod).
- [ ] Push adapters to a **private** Hugging Face repo after every run.
- Gate: beats the base model on every task; `fix` compile@1 at least +20 points on the real test.

## Phase 4: Rejection sampling (weeks 2-3)
- [ ] For every training prompt in fix/gen/edit, sample 8 outputs from the SFT model.
- [ ] Keep the outputs that compile, pass the render check and are minimal edits. Add them to the data and
      retrain 1 epoch. Repeat once if it helps.
- Gate: real-test score improves over SFT.

## Phase 5: Reinforcement learning with the compiler as reward (week 3)
- [ ] TRL `GRPOTrainer` on fix/gen/edit. Reward = compiles (+1) + render match to reference (0-1)
      - edit-size penalty - length penalty.
- [ ] Run on the fast-track model first; port to the big model only if it beats Phase 4.
- Gate: improves the real test without hurting the synthetic test. Watch for reward hacking (e.g. deleting
  content until it compiles); the render-match term is there to stop that.

## Phase 6 (optional): Continued pretraining on LaTeX
Only if the bake-off winner is weak at raw LaTeX (low `fim`): ~200M tokens of clean arXiv LaTeX before SFT,
tested on the small model first.

## Phase 7: Final eval and release
- [ ] Final benchmark table: base vs SFT vs rejection sampling vs RL vs Claude.
- [ ] Inference with **best-of-N + compile check** (sample 4-8, return the first that compiles).
- [ ] Merge, export (safetensors + GGUF), private HF model card: data sources and licences, eval table,
      known failure modes.

---

## Agents (each on its own T3 worktree branch, merged only with before/after numbers)
| Agent | Workstream |
|---|---|
| Claude Code + colab-mcp | drives Colab: data builds, bake-off, training, eval runs |
| Codex | `edit` task: programmatic transforms + document-level fault types |
| Cursor | tex.stackexchange miner -> real test set + real fix pairs |
| Grok | metrics: render match, minimal edit, compile@k, LLM judge |

Only one agent drives the Colab notebook at a time.

## Budget (estimates)
- API: Haiku for ~20k request descriptions, plus Sonnet teacher answers for ~5k hard items: roughly $15-30.
- GPU: bake-off and smoke tests on the free T4; SFT + rejection sampling + GRPO on an A100/H100 for roughly
  20-40 hours total: about $40-100 on RunPod, or Colab Pro compute units.

## Rules
- Real numbers only. If something failed, report the error.
- Test papers and the real test set never enter training.
- Don't commit `data/`, `outputs/`, or secrets.
