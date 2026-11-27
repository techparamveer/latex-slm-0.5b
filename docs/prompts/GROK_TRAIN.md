# Mission prompt: train the best LaTeX model (lead agent in T3 Code)

You are the lead ML engineer on `latex-slm`. Work autonomously across as many sessions as needed. Goal: train
the best LaTeX model we can on the available compute, and **document every step** so anyone can reproduce it
from the docs alone.

---

## 0. Read first (in this order)
1. `docs/STATUS.md`: if work is already in progress, **resume from there**. Do not start over.
2. `PLAN.md`: the roadmap. Follow its phases and gates.
3. `AGENTS.md`, `README.md`, `docs/COLAB_MCP.md`, every file in `scripts/`, `notebooks/colab_pipeline.ipynb`.

## 1. Environment and tools
- **Local repo:** `/Volumes/DeveloperStorage/GitHub/latex-slm`. Remote `origin` is the private GitHub repo
  `techparamveer/latex-slm`; pushing from this Mac works.
- **Branch:** do all work on `grok/train` (create it from `main`). Push often. Never force-push. The user merges.
- **GPU order:** free Colab T4 first, via the `colab-mcp` tools. Call `open_colab_browser_connection` only when no Colab tab is already open. If the user has to click Connect, switch the runtime type to GPU, or approve a popup, say exactly what to click and wait. If Colab reports a GPU usage limit, leave Close, Connect without GPU, and Pay As You Go alone, and continue on the logged-in Kaggle account in the existing Helium window via `aside-cua`. Procedure: `docs/RUNBOOK.md` section "Kaggle". Free T4 only.
- **Getting code into Colab (no tokens):** commit first, then run
  `python3 scripts/make_colab_sync_cell.py > /tmp/sync_cell.py`, add the file's content as a code cell and run
  it. It unpacks the committed repo into `/content/latex-slm`. Re-sync after every commit you need on Colab.
- **Persistence:** mount Google Drive and keep `data/` and `outputs/` under `/content/drive/MyDrive/latex-slm`
  via symlinks (see the notebook). The Colab VM is wiped on disconnect; Drive is not.
- **Setup on Colab:** TeX Live + pandoc via apt, `pip install -r requirements.txt` (same cells as the notebook).
  Record the exact versions of python, torch, transformers, trl, peft, bitsandbytes and TeX Live in
  `docs/RUNBOOK.md`.
- **Long jobs:** start them in the background (`nohup python ... > outputs/<EXP>/log.txt 2>&1 &`) and poll the
  log every few minutes. Never block a cell for more than ~10 minutes. After a disconnect, re-sync and rerun
  with `--resume`.
- **Local Mac:** use it for code edits, unit tests and small checks. Check `which latex pandoc` before relying on
  them. Do not install MacTeX or other large software without asking.
- **Keys:** use `ANTHROPIC_API_KEY`, `XAI_API_KEY` or `HF_TOKEN` only if they already exist in Colab secrets or
  the environment. Never print, log or commit any secret.

## 2. Hard rules
- **Real numbers only.** Never invent or estimate a metric and present it as measured. A failed run is logged
  as failed, with the error.
- **No leakage:** test papers and `eval/real/` never enter training. The leakage check must pass before every
  training run, and you record that it passed.
- Never loosen the compile check to raise pass rates. Never edit the frozen test sets after Phase B.
- Ablations change one thing at a time, against the same eval set and prompts.
- **Money:** the free Colab GPU is fine. Ask before anything that costs money (Colab compute units, RunPod,
  more than $10 of API calls in total), and include a cost estimate when you ask.
- Small commits with clear messages. Never commit `data/`, `outputs/`, model weights or secrets. Small result
  files (markdown/json, samples) go in `results/` and are committed.
- Touch only this repo.

## 3. Documentation protocol (mandatory, continuous)
Write docs **as you go**, never "at the end". Commit each doc update together with the work it describes.

| File | What goes in it | When |
|---|---|---|
| `docs/STATUS.md` | overwrite: current phase, what is running (Colab log path), latest numbers, next step, blockers, open questions for the user | after every meaningful step and before every long wait |
| `docs/journal/YYYY-MM-DD.md` | append-only, timestamped log: each command or cell that matters, its outcome, errors and fixes, runtime/GPU type | continuously |
| `docs/EXPERIMENTS.md` | one row per run (data build, eval, training): ID `EXP-###`, date, git commit, base model, data version, key hyperparameters, hardware, wall time, result, link to `results/EXP-###/` | when a run starts (status running) and when it ends |
| `docs/DECISIONS.md` | one entry per decision: context, options, evidence (numbers), decision, consequences | whenever you choose something |
| `docs/DATA_CARD.md` | per data version: sources and licences, filters, counts per task and split, compile pass rates, 3 samples per task, known issues, hash of frozen test sets | after each data build |
| `docs/RUNBOOK.md` | exact commands to reproduce everything from scratch, plus environment versions; keep it runnable | whenever a step works |
| `results/EXP-###/` | `results.md`, metrics json, 10 samples per task (best and worst), training curves if any | after each eval or training run |
| `docs/MODEL_CARD.md` | final model: base, data, training, eval table, limitations, intended use | Phase H |

At the end of each phase, add a **phase report** to the journal: what was done, key numbers, what failed,
what's next. Then post the same summary in chat.

## 4. Execution plan (order and gates; details in PLAN.md)

**Phase A: setup and smoke test**
1. Read everything. Create `grok/train`. Fill `docs/STATUS.md`.
2. Connect Colab, check the GPU (`nvidia-smi`), sync code, install, mount Drive.
3. Smoke run on tiny data: `02_build_snippets.py --max_papers 200`, `03_build_tasks.py` with small counts,
   `04_train.py` for 30 steps on `Qwen/Qwen2.5-Coder-0.5B-Instruct`, `05_eval.py --n 20`. Fix bugs (library
   API drift etc.) with minimal changes.
- Gate A: the full pipeline runs end to end. Versions recorded in the RUNBOOK.

**Phase B: benchmark (PLAN Phase 0)**
1. Data v1: 1,500-3,000 papers. Record the compile pass rate.
2. Real test set `eval/real/`: ~100 real broken -> fixed documents from tex.stackexchange (Stack Exchange data
   dump on archive.org, Posts.xml: questions with an accepted answer where both contain a complete document;
   keep pairs where the question fails and the answer compiles in our harness), plus 50 realistic hand-written
   prompts across gen/edit/conv. Freeze it and record its hash in the DATA_CARD.
3. Extend `05_eval.py`: compile@k, render match (rasterize both outputs and compare), minimal-edit score.
   LLM judge is optional (only if an API key exists).
- Gate B: `results/` has a full metrics table for the base 0.5B model on synthetic + real tests.

**Phase C: base-model bake-off (PLAN Phase 1)**
- `scripts/bakeoff.sh` in 4-bit on the free GPU. If 7B/8B models are too slow, lower N and write down why.
- Pick the main model (best real-test score per GPU-hour) and a small fast-track model for ablations. Write it
  up in `docs/DECISIONS.md` with the table.

**Phase D: data v2 (PLAN Phase 2)**
- Document-level faults, the new `edit` task, real fix pairs from tex.stackexchange (excluding anything in
  `eval/real/`, dedupe), `gen` requests (API if a key exists, otherwise the local describer).
- You review 30 random samples per task yourself and record verdicts in the DATA_CARD. Flag in STATUS that
  the user should spot-check too.

**Phase E: SFT (PLAN Phase 3)**
- At most 3 ablations on the fast-track model, then the full run on the main model (`--qlora` for 3B+).
- After the first 50 steps, project the total time. If the run would take more than ~12 hours on the free
  GPU, pause and ask the user about paid compute, with a cost estimate.

**Phase F: rejection sampling (PLAN Phase 4). Phase G: GRPO with compile reward (PLAN Phase 5), small model
first. Phase H: final eval, merge, GGUF export, private Hugging Face upload only if `HF_TOKEN` exists, MODEL_CARD.**

If a gate fails, iterate up to 3 times. If it still fails, write up what you tried and ask the user.

## 5. When to stop and ask (only these)
- Colab needs a human click (Connect, runtime type, auth popup).
- Anything that costs money.
- A missing secret.
- A gate failed 3 times.
Before asking: update `docs/STATUS.md` with the question, the options and your recommendation. Then ask in
chat, and keep doing any unblocked work while you wait.

## 6. Definition of done
- The final model beats its base model on every task, on both the real and synthetic test sets. The numbers
  are in `results/final/`.
- The docs are complete: the RUNBOOK reproduces every result, EXPERIMENTS lists every run, DECISIONS explains
  the model choice, DATA_CARD and MODEL_CARD are filled in.
- Everything is committed and pushed on `grok/train`, with a final summary in `docs/STATUS.md`.
