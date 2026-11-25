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

`04_train.py --model Qwen/Qwen2.5-Coder-0.5B-Instruct --max_steps 30 --out outputs/EXP-001/train`

The run that finished printed `train=124 val=8 bf16=False warmup_steps=1`. Trainer summary: `train_runtime` 263.9, `train_loss` 0.4748, `train_steps_per_second` 0.114, epoch 7.516. The progress bar reached 30/30 in 4:23 (8.80 s/it). Logged at the step-20 point: loss 0.5544, grad_norm 0.4475, learning_rate 6.299e-05, mean_token_accuracy 0.861. Eval on the 8 val rows: eval_loss 1.322, eval_mean_token_accuracy 0.7459. Saved `outputs/EXP-001/train/adapter` and `merged`.

Earlier attempts on the same data exited before a finished run: `warmup_ratio` rejected by trl 1.18.2; peft rejected torchao 0.10.0; a bf16 backward step failed on this T4 (compute capability 7.5).

## Eval

`05_eval.py --n 20` on the base model, then on `outputs/EXP-001/train/merged`. The test split has 12 rows, so `--n 20` used every test row: fix 3, gen 1, fim 5, conv 3.

| task | metric | base | tuned |
|---|---|---|---|
| fix | compile_rate | 0.667 | 0.667 |
| fix | exact_norm | 0.000 | 0.333 |
| fix | similarity | 0.931 | 0.996 |
| gen | compile_rate | 0.000 | 1.000 |
| gen | exact_norm | 0.000 | 0.000 |
| gen | similarity | 0.071 | 0.193 |
| fim | exact_norm | 0.000 | 0.000 |
| fim | similarity | 0.185 | 0.134 |
| conv | compile_rate | 0.000 | 1.000 |
| conv | exact_norm | 0.000 | 0.333 |
| conv | similarity | 0.676 | 0.985 |
