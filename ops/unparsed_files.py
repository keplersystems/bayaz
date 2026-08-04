#!/usr/bin/env python3
"""List raw files that are fetched but neither parsed nor present locally.

These were moved to S3 before the parser reached them, back when the offload selected on
file age. They exist in the archive but contribute nothing to the corpus until restored,
so this drives an `rclone copy --files-from` to bring exactly those back.
"""

import sqlite3
from pathlib import Path

from bayaz import config, rawstore

manifest = sqlite3.connect(f"file:{config.DATABASE_PATH}?mode=ro", uri=True)
corpus = sqlite3.connect(f"file:{config.DATA_DIR / 'corpus.db'}?mode=ro", uri=True)

parsed = {row[0] for row in corpus.execute("SELECT url FROM parsed")}
root = Path(config.RAW_DIR)

for url, site, kind in manifest.execute("SELECT url, site, kind FROM pages WHERE status = 'fetched'"):
    if url in parsed:
        continue
    path = rawstore.path_for(site, url, kind)
    if not path.exists():
        print(path.relative_to(root))
