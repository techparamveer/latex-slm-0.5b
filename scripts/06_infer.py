"""Tiny CLI for the trained model.

  python scripts/06_infer.py --model outputs/run1/merged --task fix --file broken.tex --log log.txt
  python scripts/06_infer.py --model outputs/run1/merged --task gen --text "a 3x3 matrix with ones on the diagonal"
  python scripts/06_infer.py --model outputs/run1/merged --task conv --file notes.md
"""
import argparse
import os
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, os.path.dirname(__file__))
from common import SYSTEM

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--task", choices=["fix", "gen", "conv"], required=True)
ap.add_argument("--file")
ap.add_argument("--text")
ap.add_argument("--log", help="compiler log text file (fix task)")
ap.add_argument("--max_new", type=int, default=512)
a = ap.parse_args()

src = a.text if a.text is not None else open(a.file).read()
if a.task == "fix":
    log = open(a.log).read() if a.log else ""
    user = f"Fix the LaTeX so it compiles. Return only the corrected LaTeX.\n\n[SOURCE]\n{src}\n\n[COMPILER LOG]\n{log}"
elif a.task == "gen":
    user = f"Write LaTeX for the following request.\n\n{src}"
else:
    user = f"Convert this Markdown to LaTeX.\n\n{src}"

tok = AutoTokenizer.from_pretrained(a.model)
model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype="auto", device_map="auto")
msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
enc = tok(tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True), return_tensors="pt").to(model.device)
with torch.no_grad():
    out = model.generate(**enc, max_new_tokens=a.max_new, do_sample=False)
print(tok.decode(out[0][enc.input_ids.shape[1]:], skip_special_tokens=True))
