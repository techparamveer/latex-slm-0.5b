"""Stream arXiv LaTeX rows from Hugging Face, extract snippets, dedupe, compile-filter.

Outputs (in --out, default data/):
  snippets_ok.jsonl  compiled-OK snippets {sid, paper, split, kind, text, context}
  docs.jsonl         document bodies for fill-in-the-middle {paper, split, body}
  stats.json         counts and compile pass rate
"""
import argparse
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import (compile_many, extract_snippets, norm_hash, paper_body, split_of)


def iter_rows(repo, parts, min_yymm, seed):
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    rng = random.Random(seed)
    for part in parts:
        path = f"datasets/{repo}/arxiv_part_{int(part):04d}.parquet"
        with fs.open(path, "rb") as fh:
            pf = pq.ParquetFile(fh)
            groups = list(range(pf.num_row_groups))
            rng.shuffle(groups)
            for g in groups:
                tbl = pf.read_row_group(g, columns=["id", "categories", "latex"])
                for row in tbl.to_pylist():
                    pid = row["id"] or ""
                    m = re.match(r"^(\d{2})(\d{2})\.\d{4,5}$", pid)  # new-style ids only
                    if not m or int(m.group(1) + m.group(2)) < min_yymm:
                        continue
                    if row["latex"] and len(row["latex"]) > 2000:
                        yield pid, row["categories"], row["latex"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="scholarweave/arxiv-latex")
    ap.add_argument("--parts", default="44,45,46,47,48", help="comma list of parquet part numbers")
    ap.add_argument("--max_papers", type=int, default=3000)
    ap.add_argument("--min_yymm", type=int, default=1801)
    ap.add_argument("--out", default="data")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no_minhash", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    snippets, docs, seen, papers = [], [], set(), 0
    for pid, cats, latex in iter_rows(a.repo, a.parts.split(","), a.min_yymm, a.seed):
        body = paper_body(latex)
        if not body or len(body) < 2000:
            continue
        papers += 1
        split = split_of(pid)
        docs.append({"paper": pid, "split": split, "body": body[:60000]})
        for i, s in enumerate(extract_snippets(body)):
            h = norm_hash(s["text"])
            if h in seen:
                continue
            seen.add(h)
            snippets.append({"sid": f"{pid}:{i}", "paper": pid, "split": split, **s})
        if papers % 200 == 0:
            print(f"papers={papers} snippets={len(snippets)}", flush=True)
        if papers >= a.max_papers:
            break
    print(f"extracted {len(snippets)} snippets from {papers} papers")

    # near-duplicate removal (MinHash) inside the training split only matters most,
    # but we apply it globally so test cannot be a near-copy of train.
    if not a.no_minhash:
        try:
            from datasketch import MinHash, MinHashLSH
            lsh = MinHashLSH(threshold=0.85, num_perm=64)
            keep = []
            for s in snippets:
                t = re.sub(r"\s+", " ", s["text"])
                mh = MinHash(num_perm=64)
                for k in range(max(len(t) - 4, 1)):
                    mh.update(t[k:k + 5].encode())
                if lsh.query(mh):
                    continue
                lsh.insert(s["sid"], mh)
                keep.append(s)
            print(f"minhash dedupe: {len(snippets)} -> {len(keep)}")
            snippets = keep
        except ImportError:
            print("datasketch missing, skipping near-dup removal")

    ok = compile_many([s["text"] for s in snippets], workers=a.workers)
    good = [s for s, k in zip(snippets, ok) if k]
    rate = len(good) / max(len(snippets), 1)
    print(f"compile pass rate: {rate:.1%} ({len(good)}/{len(snippets)})")

    with open(os.path.join(a.out, "snippets_ok.jsonl"), "w") as f:
        for s in good:
            f.write(json.dumps(s) + "\n")
    with open(os.path.join(a.out, "docs.jsonl"), "w") as f:
        for d in docs:
            f.write(json.dumps(d) + "\n")
    by = {}
    for s in good:
        by[(s["split"], s["kind"])] = by.get((s["split"], s["kind"]), 0) + 1
    stats = {"papers": papers, "extracted": len(snippets), "compiled_ok": len(good),
             "pass_rate": rate, "by_split_kind": {f"{k[0]}/{k[1]}": v for k, v in sorted(by.items())}}
    with open(os.path.join(a.out, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
