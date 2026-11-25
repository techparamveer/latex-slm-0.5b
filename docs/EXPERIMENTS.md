# Experiments

One row per run (data build, eval or training). Add the row when the run starts (status `running`) and
complete it when it ends. Failed runs stay in the table with status `failed` and the error in Notes.

| ID | Date | Commit | Type | Base model | Data | Key settings | Hardware | Wall time | Status | Result | Details |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP-001 | 2026-11-25 | 7cbe41d | data build | n/a | smoke, arXiv parts 44-48 | `02_build_snippets.py --max_papers 200 --workers 2` | Colab VM, Tesla T4 attached (compile is CPU) | running | running | not finished | `results/EXP-001/` |
