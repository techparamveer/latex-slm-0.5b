"""Evaluate a model (base or fine-tuned) on the held-out TEST papers.

  python scripts/05_eval.py --model Qwen/Qwen2.5-Coder-0.5B-Instruct --tag base
  python scripts/05_eval.py --model outputs/run1/merged --tag tuned

Metrics per task: compile rate (fix/gen/conv), normalized exact match, similarity (difflib ratio).
fim has no compile metric (a middle span alone is not a document).
"""
import argparse
import difflib
import json
import os
import re
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, os.path.dirname(__file__))
from common import compile_many, tqdm


def norm(s):
    return re.sub(r"\s+", "", s)


def clean(out):
    out = out.strip()
    m = re.match(r"^```(?:latex|tex)?\n(.*?)\n?```$", out, re.S)
    return (m.group(1) if m else out).strip()


def generate(model, tok, prompts, bs, max_new):
    outs = []
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    res = [None] * len(prompts)
    for b in tqdm(range(0, len(order), bs), desc="generate"):
        idx = order[b:b + bs]
        # enable_thinking=False turns off Qwen3-style reasoning; templates without it ignore the flag
        texts = [tok.apply_chat_template(prompts[i], tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False) for i in idx]
        enc = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=3000).to(model.device)
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        dec = tok.batch_decode(g[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
        for i, d in zip(idx, dec):
            res[i] = d
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", default="model")
    ap.add_argument("--data", default="data/sft")
    ap.add_argument("--n", type=int, default=200, help="examples per task")
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--max_new", type=int, default=512)
    ap.add_argument("--out", default="outputs/eval")
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir to apply on top of --model")
    ap.add_argument("--load_4bit", action="store_true", help="load base in 4-bit (3B-8B models on a T4)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(a.model, padding_side="left")
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    bf16 = (
        torch.cuda.is_available()
        and torch.cuda.get_device_capability()[0] >= 8
        and torch.cuda.is_bf16_supported()
    )
    dtype = torch.bfloat16 if bf16 else torch.float16
    quant = None
    if a.load_4bit:
        from transformers import BitsAndBytesConfig
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=dtype, device_map="auto",
                                                 quantization_config=quant)
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
    model = model.eval()

    test = [json.loads(l) for l in open(os.path.join(a.data, "test.jsonl"))]
    results, samples = {}, []
    for task in ("fix", "gen", "fim", "conv"):
        rows = [r for r in test if r["task"] == task][:a.n]
        if not rows:
            continue
        preds = [clean(p) for p in generate(model, tok, [r["prompt"] for r in rows], a.bs, a.max_new)]
        gold = [r["completion"][0]["content"] for r in rows]
        res = {"n": len(rows),
               "exact_norm": sum(norm(p) == norm(g) for p, g in zip(preds, gold)) / len(rows),
               "similarity": sum(difflib.SequenceMatcher(None, p, g).ratio() for p, g in zip(preds, gold)) / len(rows)}
        if task != "fim":
            res["compile_rate"] = sum(compile_many(preds)) / len(rows)
        results[task] = res
        samples += [{"task": task, "pred": p, "gold": g} for p, g in list(zip(preds, gold))[:10]]
        print(task, res, flush=True)

    json.dump(results, open(os.path.join(a.out, f"{a.tag}.json"), "w"), indent=2)
    json.dump(samples, open(os.path.join(a.out, f"{a.tag}_samples.json"), "w"), indent=2)

    # markdown table comparing every tag found in the out dir
    tags = sorted(f[:-5] for f in os.listdir(a.out) if f.endswith(".json") and not f.endswith("_samples.json"))
    lines = ["| task | metric | " + " | ".join(tags) + " |", "|---|---|" + "---|" * len(tags)]
    for task in ("fix", "gen", "fim", "conv"):
        for m in ("compile_rate", "exact_norm", "similarity"):
            vals = []
            for t in tags:
                r = json.load(open(os.path.join(a.out, f"{t}.json"))).get(task, {})
                vals.append(f"{r[m]:.3f}" if m in r else "-")
            if any(v != "-" for v in vals):
                lines.append(f"| {task} | {m} | " + " | ".join(vals) + " |")
    open(os.path.join(a.out, "results.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
