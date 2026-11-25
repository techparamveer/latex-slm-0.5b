# Data card

Fill one section per data version. Never edit a frozen test set after Phase B.

## Sources and licences
| Source | What we use | Licence / terms | Notes |
|---|---|---|---|
| `scholarweave/arxiv-latex` (Hugging Face) | arXiv LaTeX sources, 2018+ | dataset licence "other"; per-paper arXiv licences vary | keep derived data private |
| tex.stackexchange data dump | real errors and fixes | CC BY-SA | attribution required |

## smoke-200 (EXP-001 / EXP-002)

Not a frozen test set. Built 2026-11-25 from `scholarweave/arxiv-latex` parts 44-48, `min_yymm` 1801, `--max_papers 200`, MinHash, `compile_one`.

- Papers: 200. MinHash 4688 to 4678. Compile pass rate 58.4% (2732/4678).
- Task build: `--n1 60 --n2 60 --n3_per_doc 1 --n3_max 40 --n4 40 --describer context`. Leakage check passed.
- Rows: train 124, val 8, test 12. Per task, train/val/test: fix 29/1/3, gen 29/1/1, fim 32/3/5, conv 34/3/3.
- Lives on the Colab VM disk, not Drive.

## data-v1
- Built: (date, commit, EXP id)
- Papers read / used:
- Snippets extracted / after dedupe / compiled OK (pass rate):
- Examples per task and split:

| Task | train | val | test |
|---|---|---|---|
| fix | | | |
| gen | | | |
| fim | | | |
| conv | | | |

- Samples (3 per task):
- Review verdicts (30 per task):
- Known issues:

## Frozen test sets
| Set | Items | SHA-256 | Frozen on |
|---|---|---|---|
| synthetic test (`data/sft/test.jsonl`) | | | |
| `eval/real/` | | | |
