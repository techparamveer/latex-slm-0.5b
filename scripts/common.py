"""Shared helpers: LaTeX compile checks, snippet extraction, splits, prompts."""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor

try:
    from tqdm import tqdm
except ImportError:  # tqdm is optional
    def tqdm(x, **kw):
        return x

# --------------------------------------------------------------------------
# Compile harness. Every snippet is wrapped in the same minimal document so
# "does it compile" means the same thing for data filtering and evaluation.
# --------------------------------------------------------------------------
PREAMBLE = r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsthm,mathtools,bm,booktabs,multirow,array,xcolor}
\usepackage[draft]{graphicx}
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}{Lemma}
\newtheorem{proposition}{Proposition}
\newtheorem{corollary}{Corollary}
\theoremstyle{definition}
\newtheorem{definition}{Definition}
\newtheorem{remark}{Remark}
\begin{document}
"""
POSTAMBLE = "\n\\end{document}\n"
PRE_LINES = PREAMBLE.count("\n")

SYSTEM = "You are an expert LaTeX assistant. Reply with LaTeX only, no explanations, no code fences."


def split_of(paper_id: str) -> str:
    """Deterministic split BY PAPER so no paper is in two splits."""
    h = int(hashlib.md5(paper_id.encode()).hexdigest(), 16) % 100
    return "train" if h < 90 else ("val" if h < 95 else "test")


def norm_hash(text: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", "", text).encode()).hexdigest()


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


# --------------------------------------------------------------------------
# Compiling
# --------------------------------------------------------------------------
def compile_one(snippet: str, timeout: int = 20, halt: bool = True):
    """Compile a snippet inside the standard wrapper. Returns (ok, log)."""
    d = tempfile.mkdtemp(prefix="tex_")
    try:
        with open(os.path.join(d, "doc.tex"), "w", encoding="utf-8") as f:
            f.write(PREAMBLE + snippet + POSTAMBLE)
        cmd = ["latex", "-interaction=nonstopmode", "-no-shell-escape"]
        if halt:
            cmd.append("-halt-on-error")
        cmd.append("doc.tex")
        try:
            p = subprocess.run(cmd, cwd=d, stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, "! Compilation timed out."
        log = ""
        lp = os.path.join(d, "doc.log")
        if os.path.exists(lp):
            with open(lp, encoding="utf-8", errors="replace") as f:
                log = f.read()
        return p.returncode == 0, log
    finally:
        shutil.rmtree(d, ignore_errors=True)


def parse_errors(log: str, maxn: int = 3) -> str:
    """Pull the first few TeX errors out of a log, with snippet-relative line numbers."""
    lines = log.splitlines()
    out = []
    for i, line in enumerate(lines):
        if len(out) >= maxn:
            break
        if line.startswith("!"):
            ctx = ""
            for j in range(i + 1, min(i + 8, len(lines))):
                m = re.match(r"l\.(\d+)\s?(.*)", lines[j])
                if m:
                    n = max(int(m.group(1)) - PRE_LINES, 1)
                    ctx = f"line {n}: {m.group(2)}"
                    break
            out.append(line + ("\n" + ctx if ctx else ""))
    return "\n".join(out)


def _batch_doc(snips):
    return "\n".join("\\begingroup\n" + s + "\n\\endgroup\n\\clearpage" for s in snips)


def _bisect(snips):
    if not snips:
        return []
    ok, _ = compile_one(_batch_doc(snips) if len(snips) > 1 else snips[0])
    if ok:
        return [True] * len(snips)
    if len(snips) == 1:
        return [False]
    mid = len(snips) // 2
    return _bisect(snips[:mid]) + _bisect(snips[mid:])


def compile_many(snips, workers=None, batch=32):
    """Fast bulk check: compile batches, bisect failures. Returns list[bool]."""
    workers = workers or os.cpu_count() or 2
    chunks = [snips[i:i + batch] for i in range(0, len(snips), batch)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(tqdm(ex.map(_bisect, chunks), total=len(chunks), desc="compile"))
    return [x for r in res for x in r]


# --------------------------------------------------------------------------
# Reading the arXiv LaTeX parquet rows (concatenated files with FILE: headers)
# --------------------------------------------------------------------------
HDR = re.compile(r"^={10,}\nFILE: (.+?)\n={10,}\n", re.M)


def split_files(s: str) -> dict:
    parts = HDR.split(s)
    if len(parts) == 1:
        return {"main.tex": s}
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def flatten(name: str, files: dict, depth: int = 0) -> str:
    text = files[name]
    if depth > 5:
        return text

    def repl(m):
        target = m.group(2).strip()
        base = os.path.basename(target)
        for cand in (target, target + ".tex", base, base + ".tex"):
            for fname in files:
                if fname == cand or os.path.basename(fname) == cand:
                    if fname != name:
                        return flatten(fname, files, depth + 1)
        return ""

    return re.sub(r"\\(input|include)\s*\{([^}]*)\}", repl, text)


def paper_body(latex_field: str):
    """Return the flattened, comment-free document body or None."""
    files = split_files(latex_field)
    mains = [n for n, t in files.items() if "\\documentclass" in t and "\\begin{document}" in t]
    if not mains:
        return None
    main = max(mains, key=lambda n: len(files[n]))
    full = strip_comments(flatten(main, files))
    if "\\begin{document}" not in full:
        return None
    body = full.split("\\begin{document}", 1)[1].split("\\end{document}", 1)[0]
    return body


# --------------------------------------------------------------------------
# Snippet extraction
# --------------------------------------------------------------------------
KIND_OF = {}
for _e in ["equation", "equation*", "align", "align*", "gather", "gather*", "multline",
           "multline*", "eqnarray", "eqnarray*"]:
    KIND_OF[_e] = "math"
for _e in ["tabular", "table", "table*"]:
    KIND_OF[_e] = "table"
for _e in ["itemize", "enumerate"]:
    KIND_OF[_e] = "list"
for _e in ["theorem", "lemma", "proposition", "corollary", "definition", "remark"]:
    KIND_OF[_e] = "theorem"
KIND_OF["proof"] = "proof"

ENV_RE = re.compile(r"\\begin\{(" + "|".join(re.escape(e) for e in KIND_OF) + r")\}.*?\\end\{\1\}", re.S)
DISPLAY_RE = re.compile(r"\\\[.*?\\\]|\$\$.*?\$\$", re.S)
BAD_PARA = re.compile(r"\\(cite\w*|ref|eqref|label|input|include|footnote|url|href|begin|end|item|"
                      r"section|subsection|paragraph|caption|bibitem|newcommand|def)\b")


def extract_snippets(body: str, min_len=20, max_len=2500, cap_per_kind=12):
    """Yield dicts {kind, text, context} from a document body."""
    found = []
    for m in ENV_RE.finditer(body):
        found.append((m.start(), KIND_OF[m.group(1)], m.group(0)))
    for m in DISPLAY_RE.finditer(body):
        found.append((m.start(), "math", m.group(0)))
    pos = 0
    for p in re.split(r"\n\s*\n", body):
        start = body.find(p, pos)
        pos = max(pos, start + len(p)) if start >= 0 else pos
        p = p.strip()
        if 150 <= len(p) <= 1200 and "$" in p and not p.startswith("\\") and not BAD_PARA.search(p):
            found.append((max(start, 0), "paragraph", p))
    counts, out = {}, []
    for start, kind, text in sorted(found, key=lambda x: x[0]):
        text = text.strip()
        if not (min_len <= len(text) <= max_len):
            continue
        if counts.get(kind, 0) >= cap_per_kind:
            continue
        counts[kind] = counts.get(kind, 0) + 1
        ctx = body[max(0, start - 700):start].split("\n\n")[-1].strip()[-500:]
        out.append({"kind": kind, "text": text, "context": ctx})
    return out
