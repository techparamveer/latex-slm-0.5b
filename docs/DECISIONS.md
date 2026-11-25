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

## D-002: Real fix pairs are document bodies passed to compile_one
- **Date:** 2026-11-25
- **Context:** Phase B needs about 100 tex.stackexchange pairs in `eval/real/`. `compile_one` wraps its input in `PREAMBLE`, which already contains `\documentclass` and `\begin{document}`. A full document passed through that wrapper starts a second document inside the first.
- **Options:** pass the full document to `compile_one`; pass the inner body; copy preamble macros onto the body; compile with a second latex entry point.
- **Evidence:** no compile pass rate. `which latex` on this Mac returned nothing, so `compile_one` was not run. The archive.org file `tex.stackexchange.com.7z` was measured the same day: 777,802,350 bytes, md5 `cb8345bb543c818ea110442847c6cf42`, sha1 `3e41b52737d3675ce8432c4a1b806423b0828d4f`, last-modified 2024-04-06, 6 files inside. The file list is packed in the 7z, so the whole archive has to be downloaded before `Posts.xml` can be streamed.
- **Decision:** a post contains a complete document when one `<code>` block contains `\documentclass`, then `\begin{document}`, then `\end{document}`. The string passed to `compile_one` is the inner body. A pair is kept only when that call rejects the question body and accepts the answer body. The first 100 such pairs in Posts.xml order are the set. The set stays unfrozen, and no SHA-256 is written to `docs/DATA_CARD.md`, until that filter has actually run. Documents longer than 20,000 characters, or bodies longer than 12,000, are skipped before the compiler. Timeouts are not counted as a failed question.
- **Consequences:** preamble-only faults are outside this harness and will not enter the real test. The slice stops at the first `\end{document}` in the code block. `scripts/02_build_snippets.py` and `scripts/03_build_tasks.py` are unchanged and do not read `eval/real/`. Posts.xml is streamed, including from `7z e -so`, so the uncompressed XML does not have to be stored. The Mac commit is the parser, the fixture dry-run, and the prompt slot. Compile filtering waits for a machine with TeX Live.
