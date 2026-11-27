"""Install deps on a Kaggle notebook and download the smoke-test base model.

Run from the unpacked repo after the sync cell. Does not start training.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
DEST = "/kaggle/working/models/Qwen2.5-Coder-0.5B-Instruct"

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"])
print(subprocess.check_output(["nvidia-smi", "-L"], text=True))

import torch
from huggingface_hub import snapshot_download

print("cuda", torch.cuda.is_available(), "count", torch.cuda.device_count())
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print("gpu", i, torch.cuda.get_device_name(i))
path = snapshot_download(MODEL, local_dir=DEST)
print("model", path)
