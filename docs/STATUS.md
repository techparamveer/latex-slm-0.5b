# Status

_Overwrite this file after every meaningful step._

- **Last updated:** 2026-11-25 04:12 UTC
- **Phase:** A (setup and smoke test). Gate A not passed. GPU probe passed. Snippet build is running.
- **Branch / commit:** `grok/train`. Colab has commit `7cbe41d` unpacked at `/content/latex-slm`.
- **Running now:** `python -u scripts/02_build_snippets.py --max_papers 200 --workers 2` on the Colab VM, pid 9334, log `/content/latex-slm/outputs/EXP-001/02_build_snippets.log`. `nvidia-smi -L` at start: `GPU 0: Tesla T4`.
- **Latest numbers:** none yet (build just started). Environment measured on this runtime: Python 3.13.16, torch 2.14.1+cu130, transformers 5.22.1, trl 1.18.2, peft 0.21.2, bitsandbytes 0.50.2, TeX Live 2023/Debian (`pdfTeX 3.141592653-2.6-1.40.25`), pandoc 3.1.3.
- **Next step:** When `02` prints the compile pass rate, run `03_build_tasks.py` with small counts and `--describer context`. Start `04_train.py` only after that script prints `leakage check passed`. Then `05_eval.py --n 20`.
- **Blockers:** Google Drive is not mounted. `drive.mount` (ephemeral auth) returns `MessageError: credential propagation was unsuccessful` after the notebook Drive prompt and the OAuth window. A non-ephemeral `_mount` returned `ValueError: mount failed`. Smoke files are on the VM disk under `/content/latex-slm/{data,outputs}` and disappear if this runtime disconnects.
- **Questions for the user:** Drive auth in Helium does not hand the credential back to the notebook. Options: (1) leave the smoke on the VM disk and accept that a disconnect loses it, (2) when a Drive cell is running, complete the OAuth window yourself so the credential can propagate. Recommendation: (1) for this smoke test, because the T4 is already building snippets. Say if you want another mount attempt paused for you to click through.
