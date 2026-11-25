"""Print a self-contained Colab cell that unpacks the committed repo into /content/latex-slm.

Usage (from the repo root, after committing):
    python3 scripts/make_colab_sync_cell.py > /tmp/sync_cell.py
Then add the file's content as a Colab code cell and run it. No GitHub token is involved: the cell carries a
base64 tarball of `git archive HEAD` (data/ and outputs/ are not in git, so they stay on Drive).
"""
import base64
import subprocess
import sys

dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                       capture_output=True, text=True).stdout.strip()
if dirty:
    sys.stderr.write("warning: uncommitted changes are NOT included (only HEAD is packed)\n")
commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
blob = subprocess.run(["git", "archive", "--format=tar.gz", "HEAD"], capture_output=True, check=True).stdout
b64 = base64.b64encode(blob).decode()

print(f'''# latex-slm sync cell: commit {commit}
import base64, io, os, tarfile
DST = "/content/latex-slm"
os.makedirs(DST, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode("{b64}")), mode="r:gz") as tf:
    tf.extractall(DST)
WORK = "/content/drive/MyDrive/latex-slm"
if os.path.isdir("/content/drive/MyDrive"):
    for d in ("data", "outputs"):
        os.makedirs(f"{{WORK}}/{{d}}", exist_ok=True)
        link = f"{{DST}}/{{d}}"
        if not os.path.islink(link):
            os.symlink(f"{{WORK}}/{{d}}", link)
os.chdir(DST)
print("synced commit {commit} to", DST)''')
