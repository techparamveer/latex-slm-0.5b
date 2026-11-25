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
