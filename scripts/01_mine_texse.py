"""Mine tex.stackexchange Posts.xml into the held-out real fix set.

A question is kept only when it has an accepted answer, both posts contain a
complete document inside one ``<code>`` block, and ``compile_one`` rejects the
question body and accepts the answer body. The body is the text between
``\\begin{document}`` and ``\\end{document}``. ``compile_one`` already wraps
that text in the shared preamble, so the full document is stored beside it
and is not what the harness compiles.

Nothing under ``eval/real/`` is training data. This script does not import
``scripts/02_build_snippets.py`` or ``scripts/03_build_tasks.py``, and those
scripts must not read ``eval/real/``.

The archive.org dump checked on 2026-11-25 is one 7z of 777,802,350 bytes
(md5 ``cb8345bb543c818ea110442847c6cf42``). Its file list is packed inside
the archive, so the whole 7z has to be downloaded. Extract only ``Posts.xml``.
This script then streams that XML and stops once ``--limit`` pairs are kept.

  python3 scripts/01_mine_texse.py --dry-run
  python3 scripts/01_mine_texse.py --verify-dump data/texse/tex.stackexchange.com.7z
  7z e -so data/texse/tex.stackexchange.com.7z Posts.xml | python3 scripts/01_mine_texse.py --posts - --limit 100

``--dry-run`` parses ``scripts/fixtures/texse_posts_min.xml`` and does not call
``compile_one``. It does not write ``eval/real`` and does not record a hash.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import compile_one, parse_errors

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
FIXTURE = os.path.join(SCRIPT_DIR, "fixtures", "texse_posts_min.xml")
CHECKPOINT_NAME = ".compile_checkpoint.jsonl"
PAIRS_NAME = "fix_pairs.jsonl"
MIN_LIMIT = 100
MAX_DOC = 20000
MAX_BODY = 12000
# compile_one returns this log on subprocess.TimeoutExpired.
TIMED_OUT = "! Compilation timed out."

DUMP_URL = "https://archive.org/download/stackexchange/tex.stackexchange.com.7z"
DUMP_BYTES = 777802350
DUMP_MD5 = "cb8345bb543c818ea110442847c6cf42"
DUMP_SHA1 = "3e41b52737d3675ce8432c4a1b806423b0828d4f"
DUMP_UPDATED = "2024-04-06"

_CODE = re.compile(r"<code[^>]*>(.*?)</code>", re.I | re.S)
_BR = re.compile(r"<br\s*/?>", re.I)
_TAGS = re.compile(r"<([^<>]+)>")
_ROW_RE = re.compile(r"^\| `eval/real(?:/[^`]*)?` \|.*\|$", re.M)
_BLOCK_RE = re.compile(
    r"<!-- BEGIN eval-real-status -->.*?<!-- END eval-real-status -->",
    re.S,
)


class ScanCount:
    def __init__(self):
        self.rows = 0


def repo_root():
    return REPO_ROOT


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_tags(raw):
    return _TAGS.findall(raw or "")


def code_texts(body):
    out = []
    for match in _CODE.finditer(body or ""):
        text = _BR.sub("\n", match.group(1))
        out.append(html.unescape(text))
    return out


def slice_document(text):
    start = text.find("\\documentclass")
    if start < 0:
        return None
    begin = text.find("\\begin{document}", start)
    if begin < 0:
        return None
    end = text.find("\\end{document}", begin)
    if end < 0:
        return None
    return text[start:end + len("\\end{document}")]


def body_of(document):
    begin = document.find("\\begin{document}")
    end = document.find("\\end{document}", begin)
    if begin < 0 or end < 0:
        return None
    inner = document[begin + len("\\begin{document}"):end]
    if not inner.strip():
        return None
    inner = inner.strip("\n")
    if ("\\documentclass" in inner or "\\begin{document}" in inner
            or "\\end{document}" in inner):
        return None
    if len(document) > MAX_DOC or len(inner) > MAX_BODY:
        return None
    return inner


def first_document(body):
    """First complete document that sits inside a single code block."""
    for text in code_texts(body):
        document = slice_document(text)
        if document is None:
            continue
        inner = body_of(document)
        if inner is None:
            continue
        return document, inner
    return None


def local_tag(tag):
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag


def iter_rows(path, count=None):
    context = ET.iterparse(path, events=("start", "end"))
    _, root = next(context)
    for event, elem in context:
        if event != "end" or local_tag(elem.tag) != "row":
            continue
        attrs = dict(elem.attrib)
        root.clear()
        if count is not None:
            count.rows += 1
            if count.rows % 100000 == 0:
                print(f"scanned_rows={count.rows}", flush=True)
        yield attrs


def question_record(row):
    qid = as_int(row.get("Id"))
    aid = as_int(row.get("AcceptedAnswerId"))
    if qid is None or aid is None:
        return None
    extracted = first_document(row.get("Body", ""))
    if extracted is None:
        return None
    document, inner = extracted
    return {
        "question_id": qid,
        "accepted_answer_id": aid,
        "title": html.unescape(row.get("Title", "")),
        "tags": parse_tags(row.get("Tags", "")),
        "owner_user_id": row.get("OwnerUserId"),
        "document": document,
        "body": inner,
    }


def answer_record(row):
    aid = as_int(row.get("Id"))
    parent = as_int(row.get("ParentId"))
    if aid is None or parent is None:
        return None
    extracted = first_document(row.get("Body", ""))
    if extracted is None:
        return None
    document, inner = extracted
    return {
        "answer_id": aid,
        "parent_id": parent,
        "owner_user_id": row.get("OwnerUserId"),
        "document": document,
        "body": inner,
    }


def make_pair(question, answer):
    qid = question["question_id"]
    aid = answer["answer_id"]
    return {
        "task": "fix",
        "id": f"texse-{qid}-{aid}",
        "question_id": qid,
        "answer_id": aid,
        "title": question["title"],
        "tags": question["tags"],
        "url": f"https://tex.stackexchange.com/questions/{qid}",
        "license": "CC BY-SA",
        "attribution": (
            f"https://tex.stackexchange.com/questions/{qid} "
            "(tex.stackexchange.com user content, CC BY-SA)"
        ),
        "owner_user_id": question.get("owner_user_id"),
        "answer_owner_user_id": answer.get("owner_user_id"),
        "source_dump": DUMP_URL,
        "source_dump_bytes": DUMP_BYTES,
        "source_dump_md5": DUMP_MD5,
        "source_dump_sha1": DUMP_SHA1,
        "source_dump_updated": DUMP_UPDATED,
        "source_file": "Posts.xml",
        "question_document": question["document"],
        "answer_document": answer["document"],
        "question_body": question["body"],
        "answer_body": answer["body"],
    }


def iter_candidates(path, count=None):
    """Questions whose accepted answer also contains a complete document.

    Posts.xml from the public dump is ordered by Id, so the answer row usually
    follows the question. The fixture also places one answer first.
    """
    pending = {}
    early = {}
    for row in iter_rows(path, count):
        kind = row.get("PostTypeId")
        if kind == "1":
            question = question_record(row)
            if question is None:
                continue
            aid = question["accepted_answer_id"]
            if aid in early:
                answer = early.pop(aid)
                if answer["parent_id"] == question["question_id"]:
                    yield make_pair(question, answer)
            else:
                pending[aid] = question
        elif kind == "2":
            answer = answer_record(row)
            if answer is None:
                continue
            aid = answer["answer_id"]
            if aid in pending:
                question = pending.pop(aid)
                if answer["parent_id"] == question["question_id"]:
                    yield make_pair(question, answer)
            else:
                early[aid] = answer


def compile_filter_pair(pair, timeout):
    """Return the pair only when compile_one rejects the question and accepts the answer."""
    question_body = pair["question_body"]
    answer_body = pair["answer_body"]
    if question_body == answer_body:
        return None
    try:
        answer_ok, answer_log = compile_one(answer_body, timeout=timeout, halt=True)
        if answer_log.startswith(TIMED_OUT) or not answer_ok:
            return None
        question_ok, question_log = compile_one(question_body, timeout=timeout, halt=False)
    except FileNotFoundError:
        raise SystemExit(
            "latex is not on PATH. No pairs written. eval/real is not frozen. "
            "No SHA-256 recorded."
        )
    if question_log.startswith(TIMED_OUT) or question_ok:
        return None
    errors = parse_errors(question_log)[:700]
    if not errors:
        errors = "\n".join(question_log.splitlines()[:8])[:700]
    out = dict(pair)
    out["compiler_log"] = errors
    out["question_compiles"] = False
    out["answer_compiles"] = True
    out["harness"] = "scripts/common.py:compile_one"
    return out


def assert_held_out(path):
    root = os.path.realpath(repo_root())
    real = os.path.realpath(path)
    if real != root and not real.startswith(root + os.sep):
        raise SystemExit(f"refusing to write outside the repo: {path}")
    rel = os.path.relpath(real, root)
    top = rel.split(os.sep)[0]
    if top in ("data", "outputs", "scripts"):
        raise SystemExit(f"refusing to write the real test set under {top}/")
    if rel != os.path.join("eval", "real"):
        raise SystemExit("the real test set only writes to eval/real/")
    return real


def dump_line(record):
    return json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_digests(path):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    size = 0
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            size += len(chunk)
            md5.update(chunk)
            sha1.update(chunk)
    return size, md5.hexdigest(), sha1.hexdigest()


def apply_data_card(text, count, digest, when):
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise SystemExit("refusing to record a SHA-256 that is not 64 hex characters")
    if len(_ROW_RE.findall(text)) != 1 or len(_BLOCK_RE.findall(text)) != 1:
        raise SystemExit("docs/DATA_CARD.md is missing the eval/real row or status block")
    row = f"| `eval/real/fix_pairs.jsonl` | {count} | `{digest}` | {when} |"
    text = _ROW_RE.sub(row, text, count=1)
    block = (
        "<!-- BEGIN eval-real-status -->\n"
        f"`eval/real/fix_pairs.jsonl` is frozen ({count} pairs, SHA-256 `{digest}`, {when}). "
        "compile_one rejected every question body and accepted every answer body. "
        "The hand-written prompts under `eval/real/prompts/` are not part of this hash.\n"
        "<!-- END eval-real-status -->"
    )
    return _BLOCK_RE.sub(block, text, count=1)


def update_data_card(count, digest, when):
    path = os.path.join(repo_root(), "docs", "DATA_CARD.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    updated = apply_data_card(text, count, digest, when)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(updated)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def append_checkpoint(path, record):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(dump_line(record))
        handle.flush()
        os.fsync(handle.fileno())


def write_checkpoint(path, records):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(dump_line(record))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_checkpoint(path, timeout):
    kept = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                raise SystemExit(f"bad checkpoint line in {path}. Not frozen.")
            if "question_body" not in record or "answer_body" not in record:
                raise SystemExit("checkpoint pair is missing bodies. Not frozen.")
            checked = compile_filter_pair(record, timeout)
            if checked is None:
                print(f"dropped checkpoint pair {record.get('id')}", flush=True)
                continue
            kept.append(checked)
    return kept


def confirm_pairs(kept, timeout):
    confirmed = []
    print(f"confirming {len(kept)} pairs with compile_one", flush=True)
    for record in kept:
        again = compile_filter_pair(record, timeout)
        if again is None:
            raise SystemExit(
                f"confirmation failed for {record.get('id')}. "
                "Not frozen. No SHA-256 recorded."
            )
        if again.get("question_compiles") is not False or again.get("answer_compiles") is not True:
            raise SystemExit(
                f"confirmation flags failed for {record.get('id')}. "
                "Not frozen. No SHA-256 recorded."
            )
        confirmed.append(again)
    return confirmed


def write_frozen(kept, out_dir):
    final = os.path.join(out_dir, PAIRS_NAME)
    temporary = final + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        for record in kept:
            handle.write(dump_line(record))
        handle.flush()
        os.fsync(handle.fileno())
    digest = sha256_file(temporary)
    os.replace(temporary, final)
    if sha256_file(final) != digest:
        os.remove(final)
        raise SystemExit("hash changed while writing the pairs. Not frozen.")
    when = time.strftime("%Y-%m-%d", time.gmtime())
    try:
        update_data_card(len(kept), digest, when)
    except SystemExit:
        if os.path.exists(final):
            os.remove(final)
        raise
    checkpoint = os.path.join(out_dir, CHECKPOINT_NAME)
    if os.path.exists(checkpoint):
        os.remove(checkpoint)
    print(f"wrote {final}", flush=True)
    print(f"sha256 {digest}", flush=True)
    print("frozen=true", flush=True)


def open_posts(posts_path):
    if posts_path == "-":
        return sys.stdin.buffer
    if not os.path.isfile(posts_path):
        raise SystemExit(f"Posts.xml not found: {posts_path}")
    if os.path.realpath(posts_path) == os.path.realpath(FIXTURE):
        raise SystemExit("refusing to mine the fixture into eval/real")
    return posts_path


def mine(posts_path, out_dir, limit, timeout, resume):
    source = open_posts(posts_path)
    out_dir = assert_held_out(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    checkpoint = os.path.join(out_dir, CHECKPOINT_NAME)
    if os.path.exists(checkpoint) and not resume:
        raise SystemExit(
            f"{checkpoint} exists. Pass --resume to continue it, or delete it. "
            "It is not the frozen set."
        )
    kept = []
    if resume and os.path.exists(checkpoint):
        kept = load_checkpoint(checkpoint, timeout)
        write_checkpoint(checkpoint, kept)
        print(f"resumed {len(kept)} re-checked pairs", flush=True)
    seen = {record["question_id"] for record in kept}
    if len(kept) >= limit:
        write_frozen(confirm_pairs(kept[:limit], timeout), out_dir)
        return 0
    count = ScanCount()
    candidates = 0
    print(f"latex={shutil.which('latex')}", flush=True)
    print(f"posts={posts_path}", flush=True)
    print(f"limit={limit}", flush=True)
    for pair in iter_candidates(source, count):
        candidates += 1
        if pair["question_id"] in seen:
            continue
        if pair["question_body"] == pair["answer_body"]:
            continue
        kept_one = compile_filter_pair(pair, timeout)
        if kept_one is None:
            continue
        kept.append(kept_one)
        seen.add(kept_one["question_id"])
        append_checkpoint(checkpoint, kept_one)
        print(
            f"kept {len(kept)}/{limit} {kept_one['id']}",
            flush=True,
        )
        if len(kept) >= limit:
            break
    print(f"scanned_rows={count.rows} candidates_seen={candidates} kept={len(kept)}", flush=True)
    if len(kept) < limit:
        print(
            f"kept {len(kept)} compile-filtered pairs, fewer than --limit {limit}. "
            "Not frozen. No SHA-256 recorded.",
            flush=True,
        )
        print("frozen=false", flush=True)
        return 1
    write_frozen(confirm_pairs(kept[:limit], timeout), out_dir)
    return 0


def verify_dump(path):
    if not os.path.isfile(path):
        raise SystemExit(f"dump not found: {path}")
    size, md5, sha1 = file_digests(path)
    print(f"bytes={size}", flush=True)
    print(f"md5={md5}", flush=True)
    print(f"sha1={sha1}", flush=True)
    if size != DUMP_BYTES or md5 != DUMP_MD5 or sha1 != DUMP_SHA1:
        print("dump does not match the 2026-11-25 archive.org file", flush=True)
        return 1
    print("dump_match=true", flush=True)
    return 0


def check_fixture(pairs):
    by_question = {pair["question_id"]: pair for pair in pairs}
    expected = {101, 501, 601, 801}
    if set(by_question) != expected:
        raise SystemExit(
            f"fixture question ids {sorted(by_question)} != {sorted(expected)}"
        )
    first = by_question[101]
    if first["answer_id"] != 102 or first["question_body"] != "Hello $x":
        raise SystemExit("fixture pair 101 body mismatch")
    if first["answer_body"] != "Hello $x$" or first["tags"] != ["math-mode", "errors"]:
        raise SystemExit("fixture pair 101 answer or tags mismatch")
    if first["owner_user_id"] != "7" or first["answer_owner_user_id"] != "8":
        raise SystemExit("fixture pair 101 owner mismatch")
    if "MWE" in first["question_document"] or "<" in first["question_body"]:
        raise SystemExit("fixture pair 101 kept prose or html")
    second = by_question[501]
    if second["answer_id"] != 502 or second["answer_body"] != "OK":
        raise SystemExit("fixture pair 501 answer mismatch")
    if "a & b" not in second["question_body"] or "&amp;" in second["question_body"]:
        raise SystemExit("fixture pair 501 did not unescape the tabular")
    if "not a document" in second["question_document"]:
        raise SystemExit("fixture pair 501 stitched code blocks")
    if "\\documentclass[11pt]{article}" not in second["question_document"]:
        raise SystemExit("fixture pair 501 missed the documentclass options")
    third = by_question[601]
    if third["answer_id"] != 603 or third["answer_body"] != "Accepted fix":
        raise SystemExit("fixture pair 601 did not use the accepted answer")
    if "Not accepted" in third["answer_body"] or "Not accepted" in third["answer_document"]:
        raise SystemExit("fixture pair 601 used the non-accepted answer")
    fourth = by_question[801]
    if fourth["answer_id"] != 802 or fourth["question_body"] != "Broken {":
        raise SystemExit("fixture pair 801 was not joined from an earlier answer row")
    if fourth["answer_body"] != "Fixed":
        raise SystemExit("fixture pair 801 answer mismatch")
    for pair in pairs:
        for key in ("question_body", "answer_body"):
            text = pair[key]
            if ("\\documentclass" in text or "\\begin{document}" in text
                    or "\\end{document}" in text):
                raise SystemExit(f"document wrapper leaked into {pair['id']} {key}")
            if "<" in text:
                raise SystemExit(f"html leaked into {pair['id']} {key}")
        if "question_compiles" in pair or "answer_compiles" in pair:
            raise SystemExit("parser attached compile flags")


def check_held_out_guard():
    root = repo_root()
    for relative in ("data/texse", "outputs/eval", "scripts/fixtures", "eval/prompts", "eval/real/prompts"):
        try:
            assert_held_out(os.path.join(root, relative))
        except SystemExit:
            continue
        raise SystemExit(f"failed to refuse {relative}")
    assert_held_out(os.path.join(root, "eval", "real"))


def check_data_card_untouched():
    path = os.path.join(repo_root(), "docs", "DATA_CARD.md")
    with open(path, encoding="utf-8") as handle:
        original = handle.read()
    digest = "ab" * 32
    updated = apply_data_card(original, 100, digest, "2099-01-01")
    if digest not in updated or "is frozen" not in updated:
        raise SystemExit("data card updater did not fill the frozen row")
    if "not built" in updated:
        raise SystemExit("data card updater left the unfrozen row in place")
    with open(path, encoding="utf-8") as handle:
        after = handle.read()
    if after != original:
        raise SystemExit("dry-run modified docs/DATA_CARD.md")
    if digest in after:
        raise SystemExit("dry-run recorded a SHA-256 in docs/DATA_CARD.md")


def check_hash_helper():
    first = sha256_file(FIXTURE)
    second = sha256_file(FIXTURE)
    if first != second or not re.fullmatch(r"[0-9a-f]{64}", first):
        raise SystemExit("sha256 helper failed")


def dry_run():
    import common
    original = compile_one
    def forbidden(*_args, **_kwargs):
        raise SystemExit("compile_one must not be called during --dry-run")
    globals()["compile_one"] = forbidden
    common.compile_one = forbidden
    try:
        if not os.path.isfile(FIXTURE):
            raise SystemExit(f"fixture not found: {FIXTURE}")
        pairs_path = os.path.join(repo_root(), "eval", "real", PAIRS_NAME)
        existed = os.path.exists(pairs_path)
        before = os.stat(pairs_path).st_mtime if existed else None
        count = ScanCount()
        pairs = list(iter_candidates(FIXTURE, count))
        check_fixture(pairs)
        with open(FIXTURE, "rb") as handle:
            streamed = list(iter_candidates(handle, ScanCount()))
        check_fixture(streamed)
        check_held_out_guard()
        check_data_card_untouched()
        check_hash_helper()
        after_exists = os.path.exists(pairs_path)
        if existed != after_exists or (existed and os.stat(pairs_path).st_mtime != before):
            raise SystemExit("dry-run wrote eval/real/fix_pairs.jsonl")
        print(f"fixture={FIXTURE}", flush=True)
        print(f"scanned_rows={count.rows}", flush=True)
        print(f"candidate_pairs={len(pairs)}", flush=True)
        print("question_ids=" + ",".join(str(pair["question_id"]) for pair in pairs), flush=True)
        latex = shutil.which("latex")
        print(f"latex={latex if latex else 'missing'}", flush=True)
        print("compile_filtering=not_run", flush=True)
        print("compile_one_called=false", flush=True)
        print("frozen=false", flush=True)
        print("sha256_recorded=false", flush=True)
        return 0
    finally:
        globals()["compile_one"] = original
        common.compile_one = original


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mine tex.stackexchange Posts.xml into held-out eval/real fix pairs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 scripts/01_mine_texse.py --dry-run\n"
            "  python3 scripts/01_mine_texse.py --verify-dump data/texse/tex.stackexchange.com.7z\n"
            "  7z e -so data/texse/tex.stackexchange.com.7z Posts.xml \\\n"
            "    | python3 scripts/01_mine_texse.py --posts - --limit 100\n"
        ),
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="parse the tiny fixture and do not call compile_one")
    parser.add_argument("--posts", help="path to Posts.xml from the Stack Exchange dump")
    parser.add_argument("--out", default=None, help="output directory (only eval/real is allowed)")
    parser.add_argument("--limit", type=int, default=MIN_LIMIT,
                        help="pairs to keep after the compile filter (minimum 100)")
    parser.add_argument("--timeout", type=int, default=20, help="seconds passed to compile_one")
    parser.add_argument("--resume", action="store_true",
                        help="continue eval/real/.compile_checkpoint.jsonl")
    parser.add_argument("--verify-dump", metavar="PATH",
                        help="check a downloaded 7z against the recorded size and hashes")
    args = parser.parse_args(argv)
    if args.verify_dump:
        return verify_dump(args.verify_dump)
    if args.dry_run:
        return dry_run()
    if shutil.which("latex") is None:
        print(
            "compile filtering has not been run: latex is not on PATH. "
            "Run this where TeX Live exists. No pairs written. "
            "eval/real is not frozen. No SHA-256 recorded.",
            flush=True,
        )
        print("frozen=false", flush=True)
        print("sha256_recorded=false", flush=True)
        return 2
    if not args.posts:
        print("pass --posts path/to/Posts.xml", flush=True)
        return 2
    if args.limit < MIN_LIMIT:
        print(f"--limit must be at least {MIN_LIMIT} so a short run cannot be frozen", flush=True)
        return 2
    out = args.out or os.path.join(repo_root(), "eval", "real")
    return mine(args.posts, out, args.limit, args.timeout, args.resume)


if __name__ == "__main__":
    sys.exit(main())
