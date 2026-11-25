"""LoRA SFT of a small causal LM on the LaTeX task mix (completion-only loss)."""
import argparse
import json
import os

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer


def load(path, limit=None):
    rows = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            rows.append({"prompt": r["prompt"], "completion": r["completion"]})
            if limit and len(rows) >= limit:
                break
    return Dataset.from_list(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument("--data", default="data/sft")
    ap.add_argument("--out", default="outputs/run1")
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--bs", type=int, default=4)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max_len", type=int, default=2048)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--max_steps", type=int, default=-1, help="use ~200 for a smoke test")
    ap.add_argument("--limit", type=int, default=None, help="cap examples (smoke test)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--qlora", action="store_true", help="4-bit base weights, for 3B-8B models on small GPUs")
    a = ap.parse_args()

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    tok = AutoTokenizer.from_pretrained(a.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    # T4 has no bf16: keep weights fp32 and use fp16 autocast (stable LoRA training)
    quant = None
    if a.qlora:
        from transformers import BitsAndBytesConfig
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                                   bnb_4bit_compute_dtype=torch.bfloat16 if bf16 else torch.float16)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16 if bf16 else torch.float32,
                                                 quantization_config=quant)
    if a.qlora:
        from peft import prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    train, val = load(os.path.join(a.data, "train.jsonl"), a.limit), load(os.path.join(a.data, "val.jsonl"), 500)
    print(f"train={len(train)} val={len(val)} bf16={bf16}")

    cfg = SFTConfig(
        output_dir=a.out, num_train_epochs=a.epochs, max_steps=a.max_steps,
        per_device_train_batch_size=a.bs, per_device_eval_batch_size=a.bs,
        gradient_accumulation_steps=a.accum, learning_rate=a.lr, lr_scheduler_type="cosine",
        warmup_ratio=0.03, logging_steps=20, eval_strategy="steps", eval_steps=250,
        save_strategy="steps", save_steps=250, save_total_limit=2,
        bf16=bf16, fp16=not bf16, gradient_checkpointing=True, max_length=a.max_len,
        report_to="none", seed=0,
    )
    lora = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=train, eval_dataset=val,
                         processing_class=tok, peft_config=lora)
    last = None
    if a.resume and os.path.isdir(a.out):
        ck = [d for d in os.listdir(a.out) if d.startswith("checkpoint-")]
        if ck:
            last = os.path.join(a.out, max(ck, key=lambda d: int(d.split("-")[1])))
    trainer.train(resume_from_checkpoint=last)

    adapter = os.path.join(a.out, "adapter")
    trainer.save_model(adapter)
    tok.save_pretrained(adapter)
    if a.qlora:
        # merging into 4-bit weights is lossy; evaluate with: 05_eval.py --model BASE --adapter OUT/adapter --load_4bit
        print("saved adapter to", adapter)
        return
    merged = trainer.model.merge_and_unload()
    merged.save_pretrained(os.path.join(a.out, "merged"))
    tok.save_pretrained(os.path.join(a.out, "merged"))
    print("saved adapter and merged model to", a.out)


if __name__ == "__main__":
    main()
