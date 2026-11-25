# Data card

Fill one section per data version. Never edit a frozen test set after Phase B.

## Sources and licences
| Source | What we use | Licence / terms | Notes |
|---|---|---|---|
| `scholarweave/arxiv-latex` (Hugging Face) | arXiv LaTeX sources, 2018+ | dataset licence "other"; per-paper arXiv licences vary | keep derived data private |
| tex.stackexchange data dump | real errors and fixes | CC BY-SA | attribution required; Posts.xml inside the archive.org 7z; compile filter not run yet |

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
| `eval/real/` | not built | not recorded | not frozen |

<!-- BEGIN eval-real-status -->
`eval/real/` is not frozen. No SHA-256 is recorded. `latex` is not on this Mac (`which latex` found nothing on 2026-11-25), so `compile_one` has not accepted or rejected any pair. `scripts/01_mine_texse.py --dry-run` only parses `scripts/fixtures/texse_posts_min.xml`. That fixture is not this set. Compile filtering runs where TeX Live exists. Training must not read `eval/real/`. The hand-written prompt slot is `eval/real/prompts/` (0 of 50 written) and is not part of a fix-pair hash.
<!-- END eval-real-status -->
