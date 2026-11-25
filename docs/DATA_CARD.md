# Data card

Fill one section per data version. Never edit a frozen test set after Phase B.

## Sources and licences
| Source | What we use | Licence / terms | Notes |
|---|---|---|---|
| `scholarweave/arxiv-latex` (Hugging Face) | arXiv LaTeX sources, 2018+ | dataset licence "other"; per-paper arXiv licences vary | keep derived data private |
| tex.stackexchange data dump | real errors and fixes | CC BY-SA | attribution required |

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
