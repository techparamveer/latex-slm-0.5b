# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 04:04 UTC
- **Phase:** B (real test set). Parser and fixture dry-run are on `grok/real-test`. Compile filtering has not been run.
- **Branch:** `grok/real-test` (parent `ef13118`)
- **Running now:** nothing
- **Latest numbers:** `python3 scripts/01_mine_texse.py --dry-run` parsed 18 fixture rows and 4 candidate pairs (question ids 101, 501, 601, 801). Exit 0. `compile_one` was not called. No compile pass rate.
- **Next step:** where TeX Live and `7z` exist, run the command in `docs/RUNBOOK.md` section 3a. That run writes `eval/real/fix_pairs.jsonl` and records its SHA-256 in `docs/DATA_CARD.md` only after `compile_one` rejects every question body and accepts every answer body, and at least 100 pairs are kept.
- **Blockers:** this Mac has no `latex` binary. The archive.org 7z is 777,802,350 bytes and was not downloaded. `eval/real/` is not frozen. Hand-written prompts are 0 of 50.
- **Questions for the user:** none. This branch does not drive Colab.
