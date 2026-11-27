# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-27 12:23 UTC
- **Phase:** A smoke is done. EXP-008 is running on Kaggle: TeX install, then a 1500-paper rebuild, then training only if the leakage check passes.
- **Branch / commit:** `grok/train`. The notebook is unpacked at `cb59fe3`. This status update is the next commit.
- **Running now:** Kaggle draft session, `https://www.kaggle.com/code/techparamveer/latex-slm/edit`, account `techparamveer`. Accelerator `GPU T4 x2`, persistence `Files only`, internet on. The second cell's help text is `Cell execution started at 12:22pm`. GPU quota last read `00:09 / 30 hrs`. The cell installs TeX if `pdflatex` is missing, then `02_build_snippets.py --max_papers 1500 --workers 2 --out data/arxiv-1500`, then `03_build_tasks.py` with the same counts as the lost 1500-paper task build, then `04_train.py --model /kaggle/working/models/Qwen2.5-Coder-0.5B-Instruct --data data/arxiv-1500/sft --out outputs/EXP-008/train --epochs 2` only if the log contains `leakage check passed`. No stdout line from that cell is in the accessibility tree yet. `apt-get -qq` prints nothing until it finishes. Colab is still on the GPU usage-limit dialog. The 10-minute loop stays paused so it does not drive this Helium window.
- **Latest numbers:** No new eval. Latest finished eval is EXP-007, stored in `results/EXP-001/`, train commit `f54f396`, all 12 synthetic test rows. Base vs tuned: fix n=3 compile 0.667 vs 0.667, exact 0.000 vs 0.333, similarity 0.931 vs 0.996; gen n=1 compile 0.000 vs 1.000, exact 0.000 vs 0.000, similarity 0.071 vs 0.193; fim n=5 exact 0.000 vs 0.000, similarity 0.185 vs 0.134; conv n=3 compile 0.000 vs 1.000, exact 0.000 vs 0.333, similarity 0.676 vs 0.985. FIM similarity is still below the base. No real-test JSON is in `results/`.
- **Next step:** Leave this Kaggle cell running. Read `outputs/EXP-008/run.log` for the compile pass rate, then `leakage check passed`, then the train bar. Do not start a second build. Do not click Pay As You Go.
- **Blockers:** Colab still has no free GPU. EXP-008 has not printed a pass rate or a loss yet. TeX Live was not installed before this cell.
- **Questions for the user:** None. The loop is still paused.
