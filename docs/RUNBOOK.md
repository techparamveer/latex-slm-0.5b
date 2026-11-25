# Runbook

Exact commands to reproduce every artifact from scratch. Keep this runnable: only add steps that worked.

## Environment (fill in with exact versions)
| Thing | Version |
|---|---|
| Colab runtime / GPU | |
| Python | |
| torch | |
| transformers | |
| trl | |
| peft | |
| bitsandbytes | |
| TeX Live | |
| pandoc | |

## 1. Get the code onto Colab
```
# on the Mac, in the repo, after committing:
python3 scripts/make_colab_sync_cell.py > /tmp/sync_cell.py
# paste/run /tmp/sync_cell.py as a Colab cell (agents: add it with colab-mcp)
```

## 2. Install
```
!apt-get -qq update && apt-get -qq install -y texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-science pandoc
!pip -q install -r requirements.txt
```

## 3. Data
(to be filled with the exact commands that built each data version)

## 4. Bake-off, training, eval
(to be filled)
