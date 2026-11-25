#!/usr/bin/env bash
# Phase 1 bake-off: score candidate base models on the frozen test set, no training.
# Usage: N=100 bash scripts/bakeoff.sh            (default candidate list)
#        MODELS="org/a org/b" bash scripts/bakeoff.sh
# Add any newer small model you want to try to MODELS. Results: outputs/eval/results.md
set -euo pipefail
N=${N:-100}
MODELS=${MODELS:-"Qwen/Qwen2.5-Coder-1.5B-Instruct Qwen/Qwen3-1.7B Qwen/Qwen2.5-Coder-3B-Instruct Qwen/Qwen3-4B Qwen/Qwen2.5-Coder-7B-Instruct Qwen/Qwen3-8B"}
for m in $MODELS; do
  tag=$(echo "$m" | tr '/' '_')
  if [ -f "outputs/eval/$tag.json" ]; then echo "skip $m (done)"; continue; fi
  echo "=== $m ==="
  python scripts/05_eval.py --model "$m" --tag "$tag" --n "$N" --bs 4 --load_4bit || echo "FAILED $m"
done
cat outputs/eval/results.md
