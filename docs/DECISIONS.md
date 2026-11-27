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

## D-002: Colab first, then a free Kaggle T4 in Helium
- **Date:** 2026-11-27
- **Context:** Colab has shown `Cannot connect to GPU backend` because of usage limits since 2026-11-25. The user is logged into Kaggle as `techparamveer` in the existing Helium window and asked for that fallback. There is no Kaggle API token on this machine.
- **Options:** wait for the Colab quota; pay for Colab compute units; drive the logged-in Kaggle session with `aside-cua`.
- **Evidence:** the dialog text was read again at 2026-11-27 12:04 UTC. `colab_status` was `connected: false`. `~/.kaggle/kaggle.json` is absent.
- **Decision:** try the existing Colab session first. When it has no free GPU, set up and train on kaggle.com in that same Helium window. Accelerator stays a free T4. The 10-minute loop stays paused until the user turns it on.
- **Consequences:** the Colab VM disk is not visible on Kaggle, so EXP-002 (`data/arxiv-1500` and the 51/234 train) has to be rebuilt there after the leakage check passes. No token goes into git. The notebook source is the committed repo, packed by `scripts/make_colab_sync_cell.py --dest /kaggle/working/latex-slm --no-drive`.
