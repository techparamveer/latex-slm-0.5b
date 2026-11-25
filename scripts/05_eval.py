"""Evaluate a model (base or fine-tuned) on the held-out TEST papers.

  python scripts/05_eval.py --model Qwen/Qwen2.5-Coder-0.5B-Instruct --tag base
  python scripts/05_eval.py --model outputs/run1/merged --tag tuned

Metrics
  exact_norm, similarity   every task. exact_norm strips whitespace. similarity is difflib.
  compile@1                fix, gen, conv. Greedy sample, compile_one on that string alone.
  compile@k                fix, gen, conv. True if compile_one accepts any of the k candidates
                           (the greedy sample plus k-1 draws at --temperature). Default k=8.
  render_match             fix, gen, conv. dvipng of the DVI compile_one already wrote, then
                           1 - mean absolute pixel error / 255. Omitted when dvipng is absent.
                           A string compile_one rejects scores 0 and is not rasterized.
  minimal_edit             fix, edit. 1 - Levenshtein / max(len(pred), len(gold), 1)
                           on the cleaned source, not whitespace-stripped.

fim is not compiled: a middle span is not a document. Compile checks go through
common.compile_one only. This file does not run the TeX engine itself.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import zlib

sys.path.insert(0, os.path.dirname(__file__))
from common import compile_one, tqdm


COMPILE_TASKS = ("fix", "gen", "conv")
EDIT_TASKS = ("fix", "edit")
TASKS = ("fix", "gen", "fim", "conv", "edit")
_CAPTURE = threading.Lock()


def norm(s):
    return re.sub(r"\s+", "", s)


def clean(out):
    out = out.strip()
    m = re.match(r"^```(?:latex|tex)?\n(.*?)\n?```$", out, re.S)
    return (m.group(1) if m else out).strip()


def levenshtein(a, b):
    """Edit distance in Unicode code points."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for ca in a:
        cur = [prev[0] + 1]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def minimal_edit_score(pred, gold):
    """1 when pred is gold, 0 when every character must change or be inserted."""
    return 1.0 - levenshtein(pred, gold) / max(len(pred), len(gold), 1)


def rates_from_flags(flag_rows, k):
    """flag_rows[i][0] is compile_one(primary). Later entries are the other candidates."""
    if k < 1:
        raise ValueError("k must be >= 1")
    if not flag_rows:
        raise ValueError("no examples")
    n = len(flag_rows)
    out = {"compile@1": sum(1 for row in flag_rows if row and row[0]) / n}
    if k != 1:
        out["compile@%d" % k] = sum(1 for row in flag_rows if any(row[:k])) / n
    return out


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unpack_samples(scan, n, bit_depth):
    if bit_depth == 8:
        if len(scan) < n:
            raise RuntimeError("short PNG row")
        return [scan[i] for i in range(n)]
    if bit_depth not in (1, 2, 4):
        raise RuntimeError("PNG bit depth %s is not supported" % bit_depth)
    vals = []
    acc = 0
    acc_n = 0
    mask = (1 << bit_depth) - 1
    for byte in scan:
        acc = (acc << 8) | byte
        acc_n += 8
        while acc_n >= bit_depth and len(vals) < n:
            acc_n -= bit_depth
            vals.append((acc >> acc_n) & mask)
        acc &= (1 << acc_n) - 1 if acc_n else 0
    if len(vals) < n:
        raise RuntimeError("short PNG row")
    return vals


def _luma(r, g, b):
    return (299 * r + 587 * g + 114 * b) // 1000


def _over_white(gray, alpha):
    return (alpha * gray + (255 - alpha) * 255 + 127) // 255


def decode_png_gray(data):
    """Grayscale 0-255 rows. Transparent pixels are composited onto white."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("dvipng output is not a PNG")
    pos = 8
    ihdr = plte = trns = None
    idat = []
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            ihdr = chunk
        elif tag == b"PLTE":
            plte = chunk
        elif tag == b"tRNS":
            trns = chunk
        elif tag == b"IDAT":
            idat.append(chunk)
        elif tag == b"IEND":
            break
    if ihdr is None or len(ihdr) < 13:
        raise RuntimeError("PNG missing IHDR")
    width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", ihdr[:13])
    if comp != 0 or filt != 0:
        raise RuntimeError("unsupported PNG compression")
    if interlace != 0:
        raise RuntimeError("interlaced PNG is not supported")
    if width <= 0 or height <= 0:
        raise RuntimeError("PNG has no pixels")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    allowed = {0: (1, 2, 4, 8), 2: (8,), 3: (1, 2, 4, 8), 4: (8,), 6: (8,)}
    if channels is None or bit_depth not in allowed.get(color_type, ()):
        raise RuntimeError("unsupported PNG color type %s bit depth %s" % (color_type, bit_depth))
    if color_type == 3 and (not plte or len(plte) % 3 != 0):
        raise RuntimeError("indexed PNG has no palette")
    raw = zlib.decompress(b"".join(idat))
    stride = (width * channels * bit_depth + 7) // 8
    filter_bpp = max(1, (channels * bit_depth + 7) // 8)
    need = height * (1 + stride)
    if len(raw) < need:
        raise RuntimeError("truncated PNG rows")
    prev = bytearray(stride)
    rows = []
    i = 0
    for _y in range(height):
        ftype = raw[i]
        i += 1
        scan = bytearray(raw[i:i + stride])
        i += stride
        if ftype == 0:
            pass
        elif ftype == 1:
            for x in range(stride):
                left = scan[x - filter_bpp] if x >= filter_bpp else 0
                scan[x] = (scan[x] + left) & 255
        elif ftype == 2:
            for x in range(stride):
                scan[x] = (scan[x] + prev[x]) & 255
        elif ftype == 3:
            for x in range(stride):
                left = scan[x - filter_bpp] if x >= filter_bpp else 0
                scan[x] = (scan[x] + ((left + prev[x]) // 2)) & 255
        elif ftype == 4:
            for x in range(stride):
                left = scan[x - filter_bpp] if x >= filter_bpp else 0
                up = prev[x]
                up_left = prev[x - filter_bpp] if x >= filter_bpp else 0
                scan[x] = (scan[x] + _paeth(left, up, up_left)) & 255
        else:
            raise RuntimeError("bad PNG filter %s" % ftype)
        prev = scan
        raw_samples = _unpack_samples(scan, width * channels, bit_depth)
        samples = raw_samples
        if bit_depth < 8 and color_type != 3:
            factor = 255 // ((1 << bit_depth) - 1)
            samples = [v * factor for v in samples]
        row = []
        for x in range(width):
            px = samples[x * channels:(x + 1) * channels]
            pix = raw_samples[x * channels:(x + 1) * channels]
            if color_type == 0:
                gray = px[0]
                alpha = 255
                if trns is not None and len(trns) >= 2 and pix[0] == struct.unpack(">H", trns[:2])[0]:
                    alpha = 0
            elif color_type == 2:
                gray = _luma(px[0], px[1], px[2])
                alpha = 255
                if trns is not None and len(trns) >= 6:
                    tr, tg, tb = struct.unpack(">HHH", trns[:6])
                    if pix == [tr, tg, tb]:
                        alpha = 0
            elif color_type == 3:
                idx = pix[0]
                if idx * 3 + 2 >= len(plte):
                    raise RuntimeError("PNG palette index out of range")
                gray = _luma(plte[idx * 3], plte[idx * 3 + 1], plte[idx * 3 + 2])
                alpha = trns[idx] if trns is not None and idx < len(trns) else 255
            elif color_type == 4:
                gray, alpha = px[0], px[1]
            else:
                gray, alpha = _luma(px[0], px[1], px[2]), px[3]
            row.append(_over_white(gray, alpha))
        rows.append(row)
    return rows


def raster_similarity(a, b):
    """1 when every pixel matches. Missing pixels are white (255)."""
    if not a or not b or not a[0] or not b[0]:
        raise RuntimeError("empty raster")
    height = max(len(a), len(b))
    width = max(max(len(row) for row in a), max(len(row) for row in b))
    total = 0
    for y in range(height):
        ra = a[y] if y < len(a) else None
        rb = b[y] if y < len(b) else None
        for x in range(width):
            pa = ra[x] if ra is not None and x < len(ra) else 255
            pb = rb[x] if rb is not None and x < len(rb) else 255
            total += abs(pa - pb)
    return 1.0 - (total / (height * width)) / 255.0


def _stack_pages(pages):
    if not pages:
        raise RuntimeError("dvipng wrote no pages")
    width = max(len(row) for page in pages for row in page)
    stacked = []
    for page in pages:
        for row in page:
            stacked.append(list(row) + [255] * (width - len(row)))
    return stacked


def rasterize_dvi(dvi_bytes):
    """Rasterize a DVI that compile_one already wrote. Does not run TeX."""
    if shutil.which("dvipng") is None:
        raise RuntimeError("dvipng not on PATH")
    if not dvi_bytes:
        raise RuntimeError("compile_one accepted the snippet but doc.dvi was missing")
    d = tempfile.mkdtemp(prefix="dvi_")
    try:
        with open(os.path.join(d, "doc.dvi"), "wb") as f:
            f.write(dvi_bytes)
        cmd = [
            "dvipng", "-q", "-D", "100", "-T", "tight", "--png",
            "-bg", "rgb 1.0 1.0 1.0", "-fg", "rgb 0.0 0.0 0.0",
            "-o", os.path.join(d, "page%d.png"), "doc.dvi",
        ]
        try:
            p = subprocess.run(cmd, cwd=d, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise RuntimeError("dvipng timed out")
        if p.returncode != 0:
            err = p.stderr.decode("utf-8", "replace")[-2000:]
            raise RuntimeError("dvipng failed (%s): %s" % (p.returncode, err))
        paths = [os.path.join(d, name) for name in os.listdir(d) if name.endswith(".png")]
        if not paths:
            raise RuntimeError("dvipng wrote no PNG")
        paths.sort(key=lambda path: int(re.findall(r"\d+", os.path.basename(path))[-1]))
        pages = []
        for path in paths:
            with open(path, "rb") as f:
                pages.append(decode_png_gray(f.read()))
        return _stack_pages(pages)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def render_score(pred_ok, pred_dvi, gold_ok, gold_dvi):
    """Pixel score for one pair. Rejected text scores 0 and is not rasterized.

    Returns None when both sides were accepted and dvipng is not installed.
    """
    if not pred_ok or not gold_ok:
        return 0.0
    if shutil.which("dvipng") is None:
        return None
    if not pred_dvi or not gold_dvi:
        raise RuntimeError("compile_one accepted the snippet but doc.dvi was missing")
    return raster_similarity(rasterize_dvi(pred_dvi), rasterize_dvi(gold_dvi))


def _capture_dvi(snippet):
    """Run compile_one and, only if it accepts, keep the DVI it wrote.

    compile_one deletes the work directory before returning. The copy happens
    in that window. The tempfile hooks are process-global and restored before
    this function returns.
    """
    import common
    held = {}
    orig_mkdtemp = common.tempfile.mkdtemp
    orig_rmtree = common.shutil.rmtree

    def mkdtemp(*args, **kwargs):
        path = orig_mkdtemp(*args, **kwargs)
        held["dir"] = path
        return path

    def rmtree(path, *args, **kwargs):
        try:
            if held.get("dir") and os.path.abspath(path) == os.path.abspath(held["dir"]):
                dvi_path = os.path.join(path, "doc.dvi")
                if os.path.isfile(dvi_path):
                    with open(dvi_path, "rb") as f:
                        held["dvi"] = f.read()
        finally:
            orig_rmtree(path, *args, **kwargs)

    common.tempfile.mkdtemp = mkdtemp
    common.shutil.rmtree = rmtree
    try:
        ok, _log = compile_one(snippet)
    finally:
        common.tempfile.mkdtemp = orig_mkdtemp
        common.shutil.rmtree = orig_rmtree
    if not ok:
        return False, None
    dvi = held.get("dvi")
    if not dvi:
        raise RuntimeError("compile_one accepted the snippet but doc.dvi was missing")
    return True, dvi


def accepted_dvi(snippet):
    if not _CAPTURE.acquire(blocking=False):
        raise RuntimeError("accepted_dvi cannot overlap another compile capture")
    try:
        return _capture_dvi(snippet)
    finally:
        _CAPTURE.release()


def compile_oks(snippets):
    """Boolean from compile_one for each snippet."""
    out = []
    for snippet in snippets:
        ok, _log = compile_one(snippet)
        out.append(ok)
    return out


def score_task(task, primary, gold, samples=None, k=8):
    """Score one task. `primary` is the greedy decode. samples[i][0] is primary.

    When `samples` is omitted, compile@k uses that single candidate.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    if len(primary) != len(gold):
        raise ValueError("primary and gold length differ")
    if samples is None:
        samples = [[p] for p in primary]
    elif len(samples) != len(primary):
        raise ValueError("samples and primary length differ")
    else:
        for i, cands in enumerate(samples):
            if not cands or cands[0] != primary[i]:
                raise ValueError("samples[%d] must start with the primary prediction" % i)
    n = len(gold)
    if n == 0:
        return {"n": 0}
    res = {
        "n": n,
        "exact_norm": sum(norm(p) == norm(g) for p, g in zip(primary, gold)) / n,
        "similarity": sum(difflib.SequenceMatcher(None, p, g).ratio() for p, g in zip(primary, gold)) / n,
    }
    if task in EDIT_TASKS:
        res["minimal_edit"] = sum(minimal_edit_score(p, g) for p, g in zip(primary, gold)) / n
    if task not in COMPILE_TASKS:
        return res
    prim_ok = []
    prim_dvi = []
    for pred in primary:
        ok, dvi = accepted_dvi(pred)
        prim_ok.append(ok)
        prim_dvi.append(dvi)
    flag_rows = []
    extras = []
    extra_rows = []
    for i, cands in enumerate(samples):
        flag_rows.append([prim_ok[i]])
        for cand in cands[1:k]:
            extras.append(cand)
            extra_rows.append(i)
    for row_i, ok in zip(extra_rows, compile_oks(extras)):
        flag_rows[row_i].append(ok)
    res.update(rates_from_flags(flag_rows, k))
    if shutil.which("dvipng") is None:
        return res
    scores = []
    for ok, dvi, ref in zip(prim_ok, prim_dvi, gold):
        if not ok:
            scores.append(0.0)
            continue
        ok_g, dvi_g = accepted_dvi(ref)
        scores.append(render_score(ok, dvi, ok_g, dvi_g))
    if any(s is None for s in scores):
        raise RuntimeError("render score missing despite dvipng being on PATH")
    res["render_match"] = sum(scores) / n
    return res


def _metric_names(tag_to_results):
    keys = set()
    for data in tag_to_results.values():
        for task_res in data.values():
            if isinstance(task_res, dict):
                keys.update(task_res)
    keys.discard("n")
    compile_keys = []
    other = []
    for key in keys:
        m = re.fullmatch(r"compile@(\d+)", key)
        if m:
            compile_keys.append((int(m.group(1)), key))
        else:
            other.append(key)
    compile_keys.sort()
    ordered = [key for _n, key in compile_keys]
    for name in ("render_match", "minimal_edit", "exact_norm", "similarity"):
        if name in other:
            ordered.append(name)
            other.remove(name)
    ordered.extend(sorted(other))
    return ordered


def results_markdown(tag_to_results):
    tags = sorted(tag_to_results)
    metrics = _metric_names(tag_to_results)
    lines = ["| task | metric | " + " | ".join(tags) + " |",
             "|---|---|" + "---|" * len(tags)]
    for task in TASKS:
        for metric in metrics:
            vals = []
            for tag in tags:
                row = tag_to_results[tag].get(task, {})
                if isinstance(row, dict) and metric in row and row[metric] is not None:
                    vals.append("%.3f" % row[metric])
                else:
                    vals.append("-")
            if any(v != "-" for v in vals):
                lines.append("| %s | %s | %s |" % (task, metric, " | ".join(vals)))
    return "\n".join(lines) + "\n"


def write_results(out_dir):
    tags = sorted(
        name[:-5] for name in os.listdir(out_dir)
        if name.endswith(".json") and not name.endswith("_samples.json")
    )
    data = {}
    for tag in tags:
        with open(os.path.join(out_dir, tag + ".json"), encoding="utf-8") as f:
            data[tag] = json.load(f)
    text = results_markdown(data)
    with open(os.path.join(out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


def generate(model, tok, prompts, bs, max_new, k=1, temperature=0.0):
    """Return k strings per prompt. k=1 is greedy, matching the previous eval decode."""
    import torch
    if k < 1:
        raise ValueError("k must be >= 1")
    if k > 1 and temperature <= 0:
        raise ValueError("temperature must be > 0 when drawing more than one sample")
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    res = [None] * len(prompts)
    step = bs if k == 1 else max(1, bs // k)
    for b in tqdm(range(0, len(order), step), desc="generate"):
        idx = order[b:b + step]
        texts = [tok.apply_chat_template(
            prompts[i], tokenize=False, add_generation_prompt=True, enable_thinking=False,
        ) for i in idx]
        enc = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=3000).to(model.device)
        with torch.no_grad():
            if k == 1:
                g = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                                   pad_token_id=tok.pad_token_id)
            else:
                # repeat_interleave groups the k draws of one prompt together
                g = model.generate(**enc, max_new_tokens=max_new, do_sample=True,
                                   temperature=temperature, num_return_sequences=k,
                                   pad_token_id=tok.pad_token_id)
        dec = tok.batch_decode(g[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
        if len(dec) != len(idx) * k:
            raise RuntimeError("expected %d sequences, got %d" % (len(idx) * k, len(dec)))
        for n, i in enumerate(idx):
            res[i] = dec[n * k:(n + 1) * k]
    return res


def load_model(a):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model, padding_side="left")
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    quant = None
    if a.load_4bit:
        from transformers import BitsAndBytesConfig
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                   bnb_4bit_compute_dtype=dtype)
    model = AutoModelForCausalLM.from_pretrained(
        a.model, torch_dtype=dtype, device_map="auto", quantization_config=quant)
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
    return model.eval(), tok


def main():
    ap = argparse.ArgumentParser(description="Score a LaTeX model on held-out test papers.")
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", default="model")
    ap.add_argument("--data", default="data/sft")
    ap.add_argument("--n", type=int, default=200, help="examples per task")
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--max_new", type=int, default=512)
    ap.add_argument("--k", type=int, default=8, help="candidates for compile@k, including the greedy sample")
    ap.add_argument("--temperature", type=float, default=0.7,
                    help="temperature for the non-greedy candidates used by compile@k")
    ap.add_argument("--out", default="outputs/eval")
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir to apply on top of --model")
    ap.add_argument("--load_4bit", action="store_true", help="load base in 4-bit (3B-8B models on a T4)")
    a = ap.parse_args()
    if a.k < 1:
        ap.error("--k must be >= 1")
    if a.k > 1 and not (a.temperature > 0):
        ap.error("--temperature must be > 0 when --k > 1")
    os.makedirs(a.out, exist_ok=True)
    if shutil.which("dvipng") is None:
        print("render_match omitted: dvipng not on PATH", flush=True)

    model, tok = load_model(a)
    with open(os.path.join(a.data, "test.jsonl"), encoding="utf-8") as f:
        test = [json.loads(line) for line in f]
    results, samples_out = {}, []
    for task in TASKS:
        rows = [r for r in test if r["task"] == task][:a.n]
        if not rows:
            continue
        prompts = [r["prompt"] for r in rows]
        greedy = generate(model, tok, prompts, a.bs, a.max_new, k=1)
        primary = [clean(group[0]) for group in greedy]
        sampled = None
        use_k = 1
        if task in COMPILE_TASKS and a.k > 1:
            extra = generate(model, tok, prompts, a.bs, a.max_new, k=a.k - 1, temperature=a.temperature)
            sampled = [[p] + [clean(s) for s in group] for p, group in zip(primary, extra)]
            use_k = a.k
        gold = [r["completion"][0]["content"] for r in rows]
        res = score_task(task, primary, gold, samples=sampled, k=use_k)
        results[task] = res
        samples_out += [{"task": task, "pred": p, "gold": g} for p, g in list(zip(primary, gold))[:10]]
        print(task, res, flush=True)

    with open(os.path.join(a.out, "%s.json" % a.tag), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        f.write("\n")
    with open(os.path.join(a.out, "%s_samples.json" % a.tag), "w", encoding="utf-8") as f:
        json.dump(samples_out, f, indent=2)
        f.write("\n")
    text = write_results(a.out)
    print(text, end="")


if __name__ == "__main__":
    main()
