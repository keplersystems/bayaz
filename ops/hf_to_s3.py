#!/usr/bin/env python3
"""One-off: mirror the HF dataset Cossale/app-screens into s3 datasets/app-screens/.

Per file: download, verify sha256 against HF's LFS oid, upload via rclone, delete the
local copy. Resumable: files already in S3 at the right size are skipped."""

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

DATASET = "Cossale/app-screens"
DEST = os.environ["APP_SCREENS_S3"]
TMP = Path(os.environ.get("HF_TMP", "/tmp/hf-mirror"))


def api(url):
    request = urllib.request.Request(url, headers={"User-Agent": "afterweb-mirror"})
    with urllib.request.urlopen(request) as response:
        return json.load(response), response.headers.get("Link") or ""


def files():
    url = f"https://huggingface.co/api/datasets/{DATASET}/tree/main?recursive=true"
    out = []
    while url:
        entries, link = api(url)
        out += [e for e in entries if e["type"] == "file"]
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part[part.find("<") + 1 : part.find(">")]
    return out


def existing():
    p = subprocess.run(["rclone", "lsjson", "-R", "--files-only", DEST], capture_output=True, text=True, check=False)
    if p.returncode:
        return {}
    return {e["Path"]: e["Size"] for e in json.loads(p.stdout)}


def main():
    TMP.mkdir(exist_ok=True)
    have = existing()
    todo = files()
    for i, entry in enumerate(todo, 1):
        path = entry["path"]
        lfs = entry.get("lfs") or {}
        size = lfs.get("size", entry["size"])
        sha = lfs.get("oid")
        if have.get(path) == size:
            print(f"[{i}/{len(todo)}] {path}: already in s3", flush=True)
            continue

        print(f"[{i}/{len(todo)}] {path}: downloading {size / 1e9:.2f} GB", flush=True)
        local = TMP / Path(path).name
        url = f"https://huggingface.co/datasets/{DATASET}/resolve/main/{path}"
        subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(local), url], check=True)

        if sha:
            digest = hashlib.sha256()
            with local.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
            if digest.hexdigest() != sha:
                local.unlink()
                sys.exit(f"{path}: sha256 mismatch, aborting")

        subprocess.run(["rclone", "moveto", str(local), f"{DEST}/{path}", "--log-level", "ERROR"], check=True)
        print(f"[{i}/{len(todo)}] {path}: verified and uploaded", flush=True)
    print("all files mirrored", flush=True)


main()
