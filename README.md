# latex-slm

Train a small (0.5B) LaTeX-specialised language model with LoRA. One model, four tasks:

| Task | Input | Output |
|---|---|---|
| `fix` | broken LaTeX + real compiler log | corrected LaTeX |
| `gen` | plain-English request | LaTeX snippet |
| `fim` | prefix + suffix | missing middle |
| `conv` | Markdown (pandoc of real LaTeX) | original LaTeX |

All data is built from arXiv LaTeX sources. Everything is verified by actually compiling with TeX Live.

## Quick start (Google Colab)

1. Open `notebooks/colab_pipeline.ipynb` in Colab (GPU runtime).
2. Add Colab secrets: `GITHUB_TOKEN` (repo is private), optional `ANTHROPIC_API_KEY`, `HF_TOKEN`.
3. Run all cells. Data and checkpoints are stored on Google Drive under `latex-slm/`.

To drive Colab from Claude Code, see [docs/COLAB_MCP.md](docs/COLAB_MCP.md).
To have an agent run the whole thing, see [docs/CLAUDE_PROMPT.md](docs/CLAUDE_PROMPT.md).

## Pipeline

```
scripts/01_mine_texse.py      tex.stackexchange Posts.xml -> held-out eval/real fix pairs
scripts/02_build_snippets.py   stream arXiv rows -> flatten -> extract -> dedupe -> compile-filter
scripts/03_build_tasks.py      fix / gen / fim / conv datasets + leakage check
scripts/04_train.py            LoRA SFT, completion-only loss (TRL)
scripts/05_eval.py             held-out test papers, base vs tuned, compile rates
scripts/06_infer.py            CLI for the trained model
scripts/common.py              compile harness, snippet extraction, splits
```

### Design decisions
- **Data source:** `scholarweave/arxiv-latex` on Hugging Face, streamed by row group so nothing multi-GB is downloaded. Only 2018+ papers (`--min_yymm 1801`). Check the per-paper licence before redistributing any derived data.
- **Compile-checks are per snippet, not per paper.** Whole papers rarely compile in isolation (custom styles, missing figures). Snippets (equations, tables, lists, theorems, paragraphs) are wrapped in one fixed preamble (`common.PREAMBLE`), so "compiles" means the same thing in data filtering and evaluation. Snippets that depend on a paper's custom macros are dropped.
- **Fast filtering:** snippets are compiled in batches of 32 with bisection on failure, using `latex` (DVI) rather than `pdflatex`.
- **No leakage:** the split is a hash of the paper ID. `03_build_tasks.py` asserts no paper appears in two splits. Near-duplicates are removed with MinHash before splitting. `eval/real/` is a separate held-out set. `02_build_snippets.py` and `03_build_tasks.py` do not read it.
- **Fix-task labels are free:** faults are injected into compiling snippets, the compiler log is recorded, and only examples that really fail are kept.
- **Model:** chosen by bake-off (`scripts/bakeoff.sh`), trained with LoRA or QLoRA (`--qlora`). See PLAN.md.

## Evaluation
`05_eval.py` reports, per task on test papers only: compile rate (fix, gen, conv), normalized exact match, and difflib similarity. Run it on the base model and the tuned model with the same prompts. The table is written to `outputs/eval/results.md`.

## Known limits
- Snippet-level compile pass rate depends on how many snippets use custom macros. The real number is printed by step 2 and saved in `data/stats.json`.
- TRL and Transformers APIs change between versions. If `04_train.py` errors on an argument name, check the installed TRL version.
- No results have been produced yet. Run the notebook and read `results.md` for real numbers.
