#!/usr/bin/env python3
"""Verify the S3 copy of the app-screens dataset against Hugging Face's own checksums.

Reads each object back out of S3 and hashes it, so a size match cannot hide corrupted or
truncated content. Non-LFS files carry no published hash and are checked on size alone.

The hash is streamed in fixed-size chunks: these objects run to 5.37 GB each and buffering
one whole would exhaust a small machine's memory, which is exactly what happened the first
time this was written.
"""

import hashlib
import json
import os
import subprocess
import sys

DEST = os.environ["APP_SCREENS_S3"]
CHUNK = 8 << 20


def check(entry: dict) -> tuple[bool, str, int]:
    proc = subprocess.Popen(
        ["rclone", "cat", f"{DEST}/{entry['path']}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    digest = hashlib.sha256()
    size = 0
    while chunk := proc.stdout.read(CHUNK):
        digest.update(chunk)
        size += len(chunk)
    proc.stdout.close()
    if proc.wait() != 0:
        return False, "unreadable", size
    if size != entry["size"]:
        return False, f"size {size} != {entry['size']}", size
    if not entry["sha256"]:
        return True, "n/a", size
    if digest.hexdigest() != entry["sha256"]:
        return False, "MISMATCH", size
    return True, "match", size


def main():
    with open("/tmp/hf_manifest.json") as handle:
        files = json.load(handle)
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        lfs = [f for f in files if f["sha256"]]
        files = [f for f in files if not f["sha256"]] + lfs[-2:]

    print(f"verifying {len(files)} files ({sum(f['size'] for f in files) / 1e9:.1f} GB)\n", flush=True)
    bad = []
    for i, entry in enumerate(files, 1):
        ok, state, size = check(entry)
        if not ok:
            bad.append((entry["path"], state))
        print(f"  [{i}/{len(files)}] {'OK  ' if ok else 'FAIL'} {entry['path']:42} {size:>13,}  sha256={state}", flush=True)

    print(f"\nfailures: {len(bad)}")
    for path, why in bad:
        print(f"  {path}: {why}")
    sys.exit(1 if bad else 0)


main()
