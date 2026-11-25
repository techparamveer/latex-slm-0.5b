# Experiments

One row per run (data build, eval or training). Add the row when the run starts (status `running`) and
complete it when it ends. Failed runs stay in the table with status `failed` and the error in Notes.

| ID | Date | Commit | Type | Base model | Data | Key settings | Hardware | Wall time | Status | Result | Details |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP-001 | 2026-11-25 | 7cbe41d | data build | n/a | smoke, arXiv parts 44-48 | `02_build_snippets.py --max_papers 200 --workers 2` | Colab VM, Tesla T4 attached (compile is CPU) | log mtime 04:33:44 UTC; compile tqdm 21:42 for 147 batches | done | 200 papers, minhash 4688→4678, compile pass rate 58.4% (2732/4678) | `results/EXP-001/` |
| EXP-002 | 2026-11-25 | 7cbe41d | data build | n/a | smoke sft from EXP-001 | `03_build_tasks.py --n1 60 --n2 60 --n3_per_doc 1 --n3_max 40 --n4 40 --describer context` | same VM | finished before 04:38 UTC | done | leakage check passed. train 124, val 8, test 12 | `results/EXP-001/` |
| EXP-003 | 2026-11-25 | 7cbe41d | train | Qwen/Qwen2.5-Coder-0.5B-Instruct | smoke sft | `--max_steps 30` | Tesla T4, `bf16=True` printed | seconds | failed | `TypeError: SFTConfig.__init__() got an unexpected keyword argument 'warmup_ratio'` (trl 1.18.2) | `results/EXP-001/` |
