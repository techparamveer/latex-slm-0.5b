# Decisions

One entry per decision, newest at the bottom.

## D-000: Template
- **Date:**
- **Context:** what problem forced a choice
- **Options:** what was considered
- **Evidence:** numbers, links to `results/EXP-###/`
- **Decision:**
- **Consequences:** what this changes, what we give up

## D-001: Pick the model by bake-off instead of fixing 0.5B
- **Date:** 2026-11-25
- **Context:** the goal changed from "lightweight model" to "best LaTeX model we can train".
- **Options:** fixed 0.5B; fixed 7B; bake-off across 1.5B-8B.
- **Evidence:** none yet (bake-off is Phase C).
- **Decision:** bake-off on the frozen benchmark, then train the winner (QLoRA for 3B+).
- **Consequences:** needs a working benchmark before any training.

## D-002: Render match and minimal-edit definitions
- **Date:** 2026-11-25
- **Context:** Phase B needs compile@k, a pixel comparison, and a minimal-edit score. The pass/fail bit stays `scripts/common.py:compile_one`. That function deletes its work directory and returns only `(ok, log)`. This branch does not add a second TeX run and does not change `PREAMBLE`.
- **Options:** Raster: run `pdflatex` and rasterize the PDF; run `latex` again outside `compile_one`; copy the DVI `compile_one` already wrote and rasterize that with `dvipng`. Edit score: difflib only; raw Levenshtein; `1 - Levenshtein / max(len(pred), len(gold), 1)` on the cleaned source.
- **Evidence:** No model eval was run, so there is no measured model score. Unit tests cover the edit-distance arithmetic, the compile@k aggregation, and the PNG pixel math. `latex` and `dvipng` are not on this Mac, so the test that calls the real compiler was skipped.
- **Decision:** Copy `doc.dvi` out of `compile_one`'s work directory only when `compile_one` returns true, then run `dvipng -D 100 -T tight` with background `rgb 1.0 1.0 1.0` and foreground `rgb 0.0 0.0 0.0`. Pages are stacked. The score is `1 - mean(|p-q|)/255` on grayscale pixels, with missing pixels treated as white. A side `compile_one` rejects scores 0 and is not rasterized. If `dvipng` is absent, `render_match` is omitted. `minimal_edit` is the normalized Levenshtein score above, on the cleaned source (whitespace still counts). difflib `similarity` and whitespace-stripped `exact_norm` stay. `compile@1` is the greedy sample passed alone to `compile_one`. `compile@k` (default 8) is the fraction of examples where `compile_one` accepts the greedy sample or any of the other `k-1` draws at temperature 0.7.
- **Consequences:** Render match needs `dvipng` plus the DVI from the same `compile_one` call. `compile@1` is per snippet, not `compile_many`'s batched document. No model numbers exist yet.
