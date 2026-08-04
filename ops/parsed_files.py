#!/usr/bin/env python3
"""List the raw files whose page has been parsed, for `rclone move --files-from`.

The offload loop previously moved on age alone, which races the parser: a parse pass over
the whole archive runs longer than any sane age threshold, so pages captured while it works
age past the threshold and are moved before the next pass can read them. Selecting on parse
state instead removes the race entirely.
"""

import sqlite3
from pathlib import Path

from bayaz import config, rawstore

manifest = sqlite3.connect(f"file:{config.DATABASE_PATH}?mode=ro", uri=True)
corpus = sqlite3.connect(f"file:{config.DATA_DIR / 'corpus.db'}?mode=ro", uri=True)

parsed = {row[0] for row in corpus.execute("SELECT url FROM parsed")}
root = Path(config.RAW_DIR)

for url, site, kind in manifest.execute("SELECT url, site, kind FROM pages WHERE status = 'fetched'"):
    if url not in parsed:
        continue
    path = rawstore.path_for(site, url, kind)
    if path.exists():
        print(path.relative_to(root))
