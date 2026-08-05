#!/usr/bin/env python3
"""List the raw files safe to offload, for `rclone move --files-from`.

The offload loop previously moved on age alone, which races the parser: a parse pass over
the whole archive runs longer than any sane age threshold, so pages captured while it works
age past the threshold and are moved before the next pass can read them. Selecting on parse
state instead removes the race entirely.

Safe means parse is done with the file, which is true in two ways. Either its page has been
parsed, or its kind has no parser at all: tags, collections, blog and static pages are
archived deliberately but nothing extracts them, so waiting for a parse that will never come
would strand them on local disk forever.
"""

import sqlite3
from pathlib import Path

from bayaz.parse import parsed_kinds

from bayaz import config, rawstore

manifest = sqlite3.connect(f"file:{config.DATABASE_PATH}?mode=ro", uri=True)
corpus = sqlite3.connect(f"file:{config.DATA_DIR / 'corpus.db'}?mode=ro", uri=True)

parsed = {row[0] for row in corpus.execute("SELECT url FROM parsed")}
extracted = parsed_kinds()
root = Path(config.RAW_DIR)

for url, site, kind in manifest.execute("SELECT url, site, kind FROM pages WHERE status = 'fetched'"):
    if url not in parsed and (site, kind) in extracted:
        continue
    path = rawstore.path_for(site, url, kind)
    if path.exists():
        print(path.relative_to(root))
