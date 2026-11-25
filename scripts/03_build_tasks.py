"""Turn compiled snippets + documents into SFT datasets for 4 tasks.

  fix   (T1) broken source + compiler log      -> original source
  gen   (T2) natural-language description      -> LaTeX
  fim   (T3) prefix + suffix                   -> missing middle
  conv  (T4) Markdown (pandoc of real LaTeX)   -> original LaTeX

Output: data/sft/{train,val,test}.jsonl, each line
  {"task", "prompt": [chat msgs], "completion": [assistant msg], "meta": {...}}
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from common import SYSTEM, compile_one, parse_errors, tqdm


def rec(task, user, assistant, meta):
    return {"task": task,
            "prompt": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            "completion": [{"role": "assistant", "content": assistant}],
            "meta": meta}


# ---------------------------------------------------------------- T1: fix
def f_drop_brace(s, r):
    idx = [i for i, c in enumerate(s) if c in "{}" and (i == 0 or s[i - 1] != "\\")]
    if not idx:
        return None
    i = r.choice(idx)
    return s[:i] + s[i + 1:]


def f_drop_end(s, r):
    ms = list(re.finditer(r"\\end\{[^}]+\}", s))
    if not ms:
        return None
    m = r.choice(ms)
    return s[:m.start()] + s[m.end():]


def f_typo_cmd(s, r):
    ms = [m for m in re.finditer(r"\\([A-Za-z]{4,})", s)]
    if not ms:
        return None
    m = r.choice(ms)
    name = m.group(1)
    i = r.randrange(0, len(name) - 1)
    if name[i] == name[i + 1]:
        return None
    new = name[:i] + name[i + 1] + name[i] + name[i + 2:]
    return s[:m.start(1)] + new + s[m.end(1):]


def f_env_typo(s, r):
    m = re.search(r"\\begin\{([A-Za-z]{4,})\*?\}", s)
    if not m:
        return None
    name = m.group(1)
    new = name[:1] + name[2] + name[1] + name[3:]
    if new == name:
        return None
    return s[:m.start(1)] + new + s[m.end(1):]


def f_drop_dollar(s, r):
    idx = [i for i, c in enumerate(s) if c == "$" and (i == 0 or s[i - 1] != "\\")]
    if not idx:
        return None
    i = r.choice(idx)
    return s[:i] + s[i + 1:]


def f_extra_amp(s, r):
    ms = list(re.finditer(r"\\\\", s))
    if "tabular" not in s or not ms:
        return None
    m = r.choice(ms)
    return s[:m.start()] + " & x & x & x & x & x & x " + s[m.start():]


def f_double_script(s, r):
    ms = list(re.finditer(r"[\^_]\{?[A-Za-z0-9]", s))
    if not ms:
        return None
    m = r.choice(ms)
    ch = s[m.start()]
    return s[:m.start()] + ch + "{a}" + s[m.start():]


def f_text_underscore(s, r):
    ms = list(re.finditer(r"(?<=[a-z]) (?=[a-z])", s))
    if not ms:
        return None
    m = r.choice(ms)
    return s[:m.start()] + "_" + s[m.end():]


FAULTS = [f_drop_brace, f_drop_end, f_typo_cmd, f_env_typo, f_drop_dollar,
          f_extra_amp, f_double_script, f_text_underscore]


def _t1_job(args):
    sid, paper, text, seed = args
    r = random.Random(seed)
    broken = text
    for fn in r.sample(FAULTS, k=r.choice([1, 1, 1, 2])):
        out = fn(broken, r)
        if out is not None:
            broken = out
    if broken == text:
        return None
    ok, log = compile_one(broken, halt=False)
    if ok:
        return None
    errs = parse_errors(log)[:700]
    if not errs:
        return None
    user = ("Fix the LaTeX so it compiles. Return only the corrected LaTeX.\n\n"
            f"[SOURCE]\n{broken}\n\n[COMPILER LOG]\n{errs}")
    return sid, paper, user, text


# ---------------------------------------------------------------- T2: gen
DESC_PROMPT = ("Write the request a user might type to get the LaTeX below produced. 1-2 sentences, "
               "plain English. Describe what it shows (structure, symbols, layout) precisely enough to "
               "reproduce it, but do not quote LaTeX commands or backslashes. Output only the request.\n\nLaTeX:\n")


def describe_anthropic(texts, model, workers=8):
    import urllib.request
    key = os.environ["ANTHROPIC_API_KEY"]

    def one(t):
        body = json.dumps({"model": model, "max_tokens": 150,
                           "messages": [{"role": "user", "content": DESC_PROMPT + t}]}).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.load(r)["content"][0]["text"].strip()
            except Exception:
                time.sleep(2 ** attempt)
        return None

    with ThreadPoolExecutor(workers) as ex:
        return list(tqdm(ex.map(one, texts), total=len(texts), desc="describe(anthropic)"))


def describe_hf(texts, model="Qwen/Qwen2.5-1.5B-Instruct", bs=16):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model, padding_side="left")
    m = AutoModelForCausalLM.from_pretrained(model, torch_dtype=torch.float16, device_map="auto")
    out = []
    for i in tqdm(range(0, len(texts), bs), desc="describe(hf)"):
        prompts = [tok.apply_chat_template([{"role": "user", "content": DESC_PROMPT + t[:1500]}],
                                           tokenize=False, add_generation_prompt=True)
                   for t in texts[i:i + bs]]
        enc = tok(prompts, return_tensors="pt", padding=True).to(m.device)
        with torch.no_grad():
            g = m.generate(**enc, max_new_tokens=90, do_sample=False)
        out += [x.strip() for x in tok.batch_decode(g[:, enc.input_ids.shape[1]:], skip_special_tokens=True)]
    return out


def describe_context(items):
    out = []
    for s in items:
        c = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", s["context"])
        c = re.sub(r"[$\\{}]", "", c).strip()
        out.append(c if len(c) >= 40 else None)
    return out


# ---------------------------------------------------------------- T3: fim
def make_fim(doc, rng, n_windows):
    lines = doc["body"].split("\n")
    out = []
    for _ in range(n_windows):
        if len(lines) < 30:
            break
        i = rng.randrange(0, len(lines) - 20)
        j, tot = i, 0
        while j < len(lines) and tot < 2200:
            tot += len(lines[j]) + 1
            j += 1
        win = lines[i:j]
        if len(win) < 8:
            continue
        ms = rng.randrange(max(len(win) // 4, 1), max(len(win) // 2, 2))
        me, tot = ms, 0
        target = rng.randint(40, 400)
        while me < len(win) - 3 and tot < target:
            tot += len(win[me]) + 1
            me += 1
        mid = "\n".join(win[ms:me])
        pre, suf = "\n".join(win[:ms]), "\n".join(win[me:])
        if len(mid.strip()) < 30 or len(pre) < 200 or len(suf) < 100:
            continue
        out.append((pre, suf, mid))
    return out


# ---------------------------------------------------------------- T4: conv
def pandoc_md(text):
    try:
        p = subprocess.run(["pandoc", "-f", "latex", "-t", "gfm", "--wrap=none"], input=text.encode(),
                           capture_output=True, timeout=20)
        md = p.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return None
    if p.returncode != 0 or len(md) < 15 or "{=latex}" in md or "```" in md or "\\begin" in md:
        return None
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--n1", type=int, default=8000, help="attempts for fix task")
    ap.add_argument("--n2", type=int, default=6000)
    ap.add_argument("--n3_per_doc", type=int, default=4)
    ap.add_argument("--n3_max", type=int, default=12000)
    ap.add_argument("--n4", type=int, default=5000)
    ap.add_argument("--describer", default="auto", choices=["auto", "anthropic", "hf", "context"])
    ap.add_argument("--describe_model", default=os.environ.get("DESCRIBE_MODEL", "claude-haiku-4-5"))
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    snips = [json.loads(l) for l in open(os.path.join(a.data, "snippets_ok.jsonl"))]
    docs = [json.loads(l) for l in open(os.path.join(a.data, "docs.jsonl"))]
    rng.shuffle(snips)
    rng.shuffle(docs)
    records = {"train": [], "val": [], "test": []}

    # T1
    jobs = [(s["sid"], s["paper"], s["text"], rng.randrange(10 ** 9))
            for s in snips if len(s["text"]) <= 1800][:a.n1]
    paper_split = {s["paper"]: s["split"] for s in snips}
    with ProcessPoolExecutor(a.workers or os.cpu_count() or 2) as ex:
        for res in tqdm(ex.map(_t1_job, jobs, chunksize=8), total=len(jobs), desc="T1 fix"):
            if res:
                sid, paper, user, target = res
                records[paper_split[paper]].append(rec("fix", user, target, {"sid": sid, "paper": paper}))

    # T2
    pool = [s for s in snips if s["kind"] in ("math", "table", "list", "theorem", "paragraph") and len(s["text"]) <= 1500][:a.n2]
    mode = a.describer
    if mode == "auto":
        mode = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "hf"
    print("describer:", mode)
    if mode == "anthropic":
        descs = describe_anthropic([s["text"] for s in pool], a.describe_model)
    elif mode == "hf":
        descs = describe_hf([s["text"] for s in pool])
    else:
        descs = describe_context(pool)
    for s, d in zip(pool, descs):
        if not d or "\\" in d or not (15 <= len(d) <= 500):
            continue
        records[s["split"]].append(rec("gen", f"Write LaTeX for the following request.\n\n{d}", s["text"],
                                       {"sid": s["sid"], "paper": s["paper"], "kind": s["kind"]}))

    # T3
    n3 = 0
    for d in docs:
        for pre, suf, mid in make_fim(d, rng, a.n3_per_doc):
            user = ("Fill in the missing LaTeX between <PRE> and <SUF>. Return only the missing middle.\n\n"
                    f"<PRE>\n{pre}\n</PRE>\n<SUF>\n{suf}\n</SUF>")
            records[d["split"]].append(rec("fim", user, mid, {"paper": d["paper"]}))
            n3 += 1
        if n3 >= a.n3_max:
            break

    # T4
    cand = [s for s in snips if s["kind"] in ("list", "paragraph") or s["text"].startswith("\\begin{tabular}")][:a.n4]
    with ThreadPoolExecutor(a.workers or os.cpu_count() or 2) as ex:
        mds = list(tqdm(ex.map(pandoc_md, [s["text"] for s in cand]), total=len(cand), desc="T4 pandoc"))
    for s, md in zip(cand, mds):
        if md:
            records[s["split"]].append(rec("conv", f"Convert this Markdown to LaTeX.\n\n{md}", s["text"],
                                           {"sid": s["sid"], "paper": s["paper"], "kind": s["kind"]}))

    out = os.path.join(a.data, "sft")
    os.makedirs(out, exist_ok=True)
    stats = {}
    for sp, rs in records.items():
        rng.shuffle(rs)
        with open(os.path.join(out, f"{sp}.jsonl"), "w") as f:
            for r in rs:
                f.write(json.dumps(r) + "\n")
        for r in rs:
            stats.setdefault(sp, {}).setdefault(r["task"], 0)
            stats[sp][r["task"]] += 1

    # leakage check: no paper in more than one split
    seen = {}
    for sp, rs in records.items():
        for r in rs:
            p = r["meta"]["paper"]
            assert seen.setdefault(p, sp) == sp, f"paper {p} leaked across splits"
    print("leakage check passed")
    json.dump(stats, open(os.path.join(out, "stats.json"), "w"), indent=2)
    print(json.dumps(stats, indent=2))
    for t in ("fix", "gen", "fim", "conv"):
        ex_ = next((r for r in records["train"] if r["task"] == t), None)
        if ex_:
            print(f"\n--- sample {t} ---\n{ex_['prompt'][1]['content'][:500]}\n=>\n{ex_['completion'][0]['content'][:300]}")


if __name__ == "__main__":
    main()
