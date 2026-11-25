# EXP-001

Phase A smoke on the Colab VM. Tesla T4 was attached. Drive was not mounted, so these files stayed on the VM disk.

## Snippets

`python -u scripts/02_build_snippets.py --max_papers 200 --workers 2`

Log mtime 2026-11-25 04:33:44 UTC. The compile progress bar reached 147/147 in 21:42.

- papers: 200
- minhash: 4688 → 4678
- compile pass rate: 58.4% (2732/4678)

| split/kind | count |
|---|---|
| test/list | 10 |
| test/math | 52 |
| test/paragraph | 49 |
| test/proof | 4 |
| test/table | 11 |
| test/theorem | 7 |
| train/list | 163 |
| train/math | 1110 |
| train/paragraph | 689 |
| train/proof | 70 |
| train/table | 326 |
| train/theorem | 147 |
| val/list | 12 |
| val/math | 39 |
| val/paragraph | 29 |
| val/proof | 1 |
| val/table | 10 |
| val/theorem | 3 |

## Tasks

`python -u scripts/03_build_tasks.py --n1 60 --n2 60 --n3_per_doc 1 --n3_max 40 --n4 40 --describer context`

The log printed `describer: context` and `leakage check passed`.

| task | train | val | test |
|---|---|---|---|
| fix | 29 | 1 | 3 |
| gen | 29 | 1 | 1 |
| fim | 32 | 3 | 5 |
| conv | 34 | 3 | 3 |

Row counts: train 124, val 8, test 12.

## Train

First `04_train.py --max_steps 30` attempt exited before a step. The log printed `train=124 val=8 bf16=True`, then `TypeError: SFTConfig.__init__() got an unexpected keyword argument 'warmup_ratio'` on trl 1.18.2.
