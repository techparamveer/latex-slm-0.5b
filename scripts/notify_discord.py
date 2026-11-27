"""Post a measured training update to Discord.

The webhook URL comes from DISCORD_WEBHOOK_URL or ~/.config/latex-slm/discord_webhook.
It is never printed. If neither is set, the script exits 0 and says the notify was skipped.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

METRICS = (
    ("compile_rate", "compile"),
    ("exact_norm", "exact"),
    ("similarity", "similarity"),
)
TASKS = ("fix", "gen", "fim", "conv")
WEBHOOK_FILE = Path.home() / ".config" / "latex-slm" / "discord_webhook"


def webhook_url():
    env = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if env:
        return env
    if WEBHOOK_FILE.is_file():
        return WEBHOOK_FILE.read_text().strip()
    return ""


def load_pair(results_dir):
    base = json.loads((Path(results_dir) / "base.json").read_text())
    tuned = json.loads((Path(results_dir) / "tuned.json").read_text())
    return base, tuned


def fmt(value):
    return f"{value:.3f}"


def build_message(provider, results_dir, exp, commit, note):
    base, tuned = load_pair(results_dir)
    lines = [f"latex-slm {exp}" + (f" ({commit})" if commit else "")]
    lines.append(f"Provider: {provider}")
    improved, worse, same = [], [], []
    for task in TASKS:
        if task not in base or task not in tuned:
            continue
        b, t = base[task], tuned[task]
        n = t.get("n", b.get("n"))
        bits = []
        for key, label in METRICS:
            if key not in b or key not in t:
                continue
            bits.append(f"{label} {fmt(b[key])}→{fmt(t[key])}")
            name = f"{task} {label}"
            if t[key] > b[key] + 1e-9:
                improved.append(name)
            elif t[key] < b[key] - 1e-9:
                worse.append(name)
            else:
                same.append(name)
        lines.append(f"{task} n={n} " + ", ".join(bits))
    if improved:
        lines.append("Improved: " + ", ".join(improved) + ".")
    if worse:
        lines.append("Worse: " + ", ".join(worse) + ".")
    if same:
        lines.append("Unchanged: " + ", ".join(same) + ".")
    if note:
        lines.append(note)
    return "\n".join(lines)[:1900]


def send(url, text):
    body = json.dumps({"content": text}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", "User-Agent": "latex-slm"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"discord notify sent: http {resp.status}")
    except urllib.error.HTTPError as exc:
        print(f"discord notify failed: http {exc.code}", file=sys.stderr)
        return 1
    except Exception:
        print("discord notify failed: request error", file=sys.stderr)
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, help="where the GPU work ran, for example 'Kaggle, two Tesla T4s'")
    ap.add_argument("--results", required=True, help="directory with base.json and tuned.json")
    ap.add_argument("--exp", default="eval")
    ap.add_argument("--commit", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true", help="print the message and do not post")
    args = ap.parse_args()
    text = build_message(args.provider, args.results, args.exp, args.commit, args.note)
    if args.dry_run:
        print(text)
        return 0
    url = webhook_url()
    if not url:
        print("discord notify skipped: no webhook configured", file=sys.stderr)
        return 0
    return send(url, text)


if __name__ == "__main__":
    sys.exit(main())
