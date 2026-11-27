"""Post a measured training update to Discord as an embed with a chart.

The webhook URL comes from DISCORD_WEBHOOK_URL or ~/.config/latex-slm/discord_webhook.
It is never printed. If neither is set, the script exits 0 and says the notify was skipped.

The embed has a plain-English summary, the base-vs-tuned chart, then the numeric detail.
"""
import argparse
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

METRICS = (
    ("compile_rate", "compile", "Does it build?"),
    ("exact_norm", "exact", "Exact match"),
    ("similarity", "similarity", "How close?"),
)
TASKS = ("fix", "gen", "fim", "conv")
PLAIN = {
    "fix": "repairing broken LaTeX",
    "gen": "writing LaTeX from a plain request",
    "fim": "filling a missing middle",
    "conv": "turning Markdown into LaTeX",
}
WEBHOOK_FILE = Path.home() / ".config" / "latex-slm" / "discord_webhook"
BASE_COLOR = (37, 99, 235)
TUNED_COLOR = (13, 148, 136)
INK = (23, 23, 23)
MUTED = (90, 90, 90)
LINE = (220, 220, 220)


def webhook_url():
    env = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if env:
        return env
    if WEBHOOK_FILE.is_file():
        return WEBHOOK_FILE.read_text().strip()
    return ""


def load_pair(results_dir):
    root = Path(results_dir)
    return (
        json.loads((root / "base.json").read_text()),
        json.loads((root / "tuned.json").read_text()),
    )


def fmt(value):
    return f"{value:.3f}"


def font(size, bold=False):
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def compare(base, tuned):
    rows = []
    improved, worse, same = [], [], []
    for task in TASKS:
        if task not in base or task not in tuned:
            continue
        b, t = base[task], tuned[task]
        metrics = []
        for key, label, _hint in METRICS:
            if key not in b or key not in t:
                continue
            metrics.append((label, b[key], t[key]))
            name = f"{PLAIN[task]} ({label})"
            if t[key] > b[key] + 1e-9:
                improved.append(name)
            elif t[key] < b[key] - 1e-9:
                worse.append(name)
            else:
                same.append(name)
        rows.append((task, t.get("n", b.get("n")), metrics))
    return rows, improved, worse, same


def plain_summary(improved, worse, same, note):
    bits = []
    if improved:
        bits.append("Better: " + "; ".join(improved) + ".")
    if worse:
        bits.append("Worse: " + "; ".join(worse) + ".")
    if same:
        bits.append("No change: " + "; ".join(same) + ".")
    text = " ".join(bits)
    text += " Compile means the result builds. Exact means it matches the original. Similarity means how close the text is."
    if note:
        text += " " + note
    return text


def technical_summary(rows, provider, exp, commit):
    lines = [f"{exp}" + (f" {commit}" if commit else ""), f"Provider: {provider}"]
    for task, n, metrics in rows:
        bits = [f"{label} {fmt(b)}→{fmt(t)}" for label, b, t in metrics]
        lines.append(f"{task} n={n} " + ", ".join(bits))
    return "\n".join(lines)


def render_chart(rows, path):
    width, height = 960, 420
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(16, bold=True)
    label_font = font(14, bold=True)
    small = font(12)
    tiny = font(11)
    draw.text((24, 16), "base", font=small, fill=BASE_COLOR)
    draw.rectangle((70, 18, 86, 32), fill=BASE_COLOR)
    draw.text((104, 16), "tuned", font=small, fill=TUNED_COLOR)
    draw.rectangle((158, 18, 174, 32), fill=TUNED_COLOR)
    plot_top, plot_bottom = 56, 300
    plot_h = plot_bottom - plot_top
    n_tasks = max(1, len(rows))
    col_w = (width - 48) // n_tasks
    for i, (task, n, metrics) in enumerate(rows):
        x0 = 24 + i * col_w
        draw.text((x0, 332), f"{task}  n={n}", font=label_font, fill=INK)
        if not metrics:
            continue
        slot = (col_w - 16) // len(metrics)
        for j, (label, b, t) in enumerate(metrics):
            bx = x0 + 8 + j * slot
            bw = 14
            def bar(value, color, x):
                h = int(max(0.0, min(1.0, value)) * plot_h)
                y1 = plot_bottom
                y0 = y1 - h
                if h > 0:
                    draw.rectangle((x, y0, x + bw, y1), fill=color)
                else:
                    draw.line((x, y1, x + bw, y1), fill=color, width=2)
            bar(b, BASE_COLOR, bx)
            bar(t, TUNED_COLOR, bx + bw + 3)
            draw.text((bx, 306), label, font=tiny, fill=MUTED)
        draw.line((x0, plot_bottom, x0 + col_w - 20, plot_bottom), fill=LINE, width=1)
    image.save(path, "PNG")


def payload(provider, exp, commit, plain, technical):
    title = f"latex-slm {exp}"
    if commit:
        title += f" {commit}"
    return {
        "username": "latex-slm",
        "embeds": [{
            "title": title,
            "color": 0x0969DA,
            "description": plain[:4000],
            "fields": [{"name": "Numbers", "value": f"```\n{technical[:1000]}\n```"}],
            "image": {"url": "attachment://chart.png"},
            "footer": {"text": provider[:200]},
        }],
    }


def status_payload(provider, exp, note):
    text = "One model is under training."
    if note:
        text += " " + note
    return {
        "username": "latex-slm",
        "embeds": [{
            "title": f"latex-slm {exp} training",
            "color": 0x1F883D,
            "description": text[:4000],
            "footer": {"text": provider[:200]},
        }],
    }


def send_json(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", "User-Agent": "latex-slm"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"discord notify sent: http {resp.status}")
    except urllib.error.HTTPError as exc:
        print(f"discord notify failed: http {exc.code}", file=sys.stderr)
        return 1
    except Exception:
        print("discord notify failed: request error", file=sys.stderr)
        return 1
    return 0


def send(url, data, chart_path):
    boundary = uuid.uuid4().hex
    chart = Path(chart_path).read_bytes()
    chunks = []
    def add(name, body, filename=None, content_type=None):
        disp = f'form-data; name="{name}"'
        if filename:
            disp += f'; filename="{filename}"'
        chunks.append(f"--{boundary}\r\nContent-Disposition: {disp}\r\n".encode())
        if content_type:
            chunks.append(f"Content-Type: {content_type}\r\n".encode())
        chunks.append(b"\r\n")
        chunks.append(body if isinstance(body, bytes) else body.encode())
        chunks.append(b"\r\n")
    add("payload_json", json.dumps(data), content_type="application/json")
    add("files[0]", chart, filename="chart.png", content_type="image/png")
    chunks.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        url,
        data=b"".join(chunks),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "latex-slm",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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
    ap.add_argument("--provider", required=True)
    ap.add_argument("--results", default="", help="directory with base.json and tuned.json; omit with --status")
    ap.add_argument("--exp", default="eval")
    ap.add_argument("--commit", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--status", action="store_true",
                    help="a train is in progress; do not attach an older score chart")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.status:
        data = status_payload(args.provider, args.exp, args.note)
        if args.dry_run:
            print(data["embeds"][0]["description"])
            print(data["embeds"][0]["footer"]["text"])
            return 0
        url = webhook_url()
        if not url:
            print("discord notify skipped: no webhook configured", file=sys.stderr)
            return 0
        return send_json(url, data)
    if not args.results:
        ap.error("--results is required unless --status is set")
    base, tuned = load_pair(args.results)
    rows, improved, worse, same = compare(base, tuned)
    plain = plain_summary(improved, worse, same, args.note)
    technical = technical_summary(rows, args.provider, args.exp, args.commit)
    chart = Path(tempfile.gettempdir()) / "latex-slm-chart.png"
    render_chart(rows, chart)
    if args.dry_run:
        print(plain)
        print("---")
        print(technical)
        print(chart)
        return 0
    url = webhook_url()
    if not url:
        print("discord notify skipped: no webhook configured", file=sys.stderr)
        return 0
    return send(url, payload(args.provider, args.exp, args.commit, plain, technical), chart)


if __name__ == "__main__":
    sys.exit(main())
