# Held-out real test

This directory is the tex.stackexchange fix set and the slot for hand-written prompts. Training does not read it. `scripts/02_build_snippets.py`, `scripts/03_build_tasks.py`, and `scripts/04_train.py` do not import it, and new training code should leave it alone.

`eval/real/fix_pairs.jsonl` is written only by `scripts/01_mine_texse.py` after `scripts/common.py:compile_one` has rejected every question body and accepted every answer body. Until that file exists and `docs/DATA_CARD.md` records its SHA-256, this set is not frozen.

What the harness compiles is the document body (the text between `\begin{document}` and `\end{document}`), stored as `question_body` and `answer_body`. The full extracted documents are `question_document` and `answer_document`. `compile_one` wraps a body in the shared preamble, so a full document passed to `compile_one` is not the filtered object. The extractor stops at the first `\end{document}` in that code block.

A compile-filter checkpoint may appear as `eval/real/.compile_checkpoint.jsonl`. That file is gitignored. It is not the frozen set.

The parser fixture lives at `scripts/fixtures/texse_posts_min.xml`. It is not part of this directory.

Hand-written prompts live under `prompts/`. None are written yet. They are not covered by the fix-pair hash.
