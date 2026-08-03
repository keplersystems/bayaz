"""Captured pages on disk: one gzip per page, named by the URL's hash.

The URL is the identity, so the filename derives from it rather than from its path, which
carries query strings (?lang=ur) and unicode that filesystems handle badly. Two hex levels
of sharding keep every directory to a few thousand files at full scale.

Writes go straight to the final name. The manifest is the source of truth: a row is marked
fetched only after the write returns, so a crash can only ever leave a file whose row is
still pending, and the re-fetch overwrites it.
"""

import gzip
import hashlib
from pathlib import Path

from bayaz import config


def suffix_for(kind: str) -> str:
    """API responses are JSON; everything else is a rendered page."""
    return ".json.gz" if kind.endswith("-api") else ".html.gz"


def path_for(site: str, url: str, kind: str = "") -> Path:
    digest = hashlib.sha1(url.encode()).hexdigest()
    return config.RAW_DIR / site / digest[:2] / f"{digest}{suffix_for(kind)}"


def write(site: str, url: str, text: str, kind: str = "") -> tuple[str, int]:
    """Store a capture; returns the content's sha256 and its uncompressed size."""
    raw = text.encode("utf-8")
    path = path_for(site, url, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(raw, 6))
    return hashlib.sha256(raw).hexdigest(), len(raw)


def read(site: str, url: str, kind: str = "") -> str:
    return gzip.decompress(path_for(site, url, kind).read_bytes()).decode("utf-8")
