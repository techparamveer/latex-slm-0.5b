# Hand-written prompts

Place for 50 hand-written prompts across `gen`, `edit`, and `conv`. None are written yet (0 of 50). They are not mined from Posts.xml, not frozen, and not included in the fix-pair SHA-256.

Create these files in this directory when the prompts exist:

- `gen.jsonl`
- `edit.jsonl`
- `conv.jsonl`

One JSON object per line:

```json
{"id": "hand-gen-001", "task": "gen", "prompt": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}], "reference": ""}
```

`task` is `gen`, `edit`, or `conv`. `reference` is the LaTeX the prompt should produce, or an empty string when the reference is still open. Keep the 50 lines in this directory so they stay out of `data/` and out of `scripts/02_build_snippets.py` and `scripts/03_build_tasks.py`.
