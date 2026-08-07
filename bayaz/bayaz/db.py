"""The crawl manifest: every URL the archive knows about and where its capture stands.

One `pages` row per URL; `status` is the whole state machine. Pending rows are the work
queue, so an interrupted crawl resumes by selecting them again, and every write path is
INSERT OR IGNORE, so re-running enumerate months later is itself the delta: new URLs land
pending, everything already captured keeps its state.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Self

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    url TEXT PRIMARY KEY,
    site TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    lastmod TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    http_status INTEGER,
    attempts INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT,
    bytes INTEGER,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fetched_at TIMESTAMP,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_pages_site_status ON pages(site, status);
CREATE INDEX IF NOT EXISTS idx_pages_site_kind ON pages(site, kind);
-- Looked up once per fetch to end paging chains, so it cannot be a scan of 2.5M rows.
CREATE INDEX IF NOT EXISTS idx_pages_content ON pages(site, kind, sha256);

-- Pronunciation audio and any other media the captured pages reference. Recorded now,
-- downloaded by a later job: the urls are in the raw HTML too, but re-deriving them
-- means re-parsing a million pages, and one row per file is cheap.
CREATE TABLE IF NOT EXISTS media (
    url TEXT PRIMARY KEY,
    site TEXT NOT NULL,
    first_seen_url TEXT NOT NULL,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- First path segment -> kind, per platform site, derived from the sitemaps at enumerate
-- time. This is what lets crawl-time link discovery classify a found URL without any
-- hardcoded list of the sites' content types.
CREATE TABLE IF NOT EXISTS segments (
    site TEXT NOT NULL,
    segment TEXT NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (site, segment)
);
"""


class PageStatus(StrEnum):
    PENDING = "pending"
    FETCHED = "fetched"
    FAILED = "failed"
    # Served by an API instead. Kept rather than deleted: the row still records that the
    # page exists on the web, and unsuperseding it is how we fall back if an API dies.
    SUPERSEDED = "superseded"


@dataclass(slots=True)
class PageRef:
    """What enumerate and discovery record, and what the crawler works from."""

    url: str
    site: str
    kind: str
    source: str = "sitemap"
    lastmod: str | None = None
    attempts: int = 0

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> Self:
        return cls(
            url=row["url"],
            site=row["site"],
            kind=row["kind"],
            source=row["source"],
            lastmod=row["lastmod"],
            attempts=row["attempts"],
        )


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: aiosqlite.Connection = None  # type: ignore

    async def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.executescript(SCHEMA)
        await self._connection.commit()

    async def close(self):
        if self._connection:
            await self._connection.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def add_pages(self, pages: list[PageRef]) -> int:
        if not pages:
            return 0
        cursor = await self._connection.executemany(
            "INSERT OR IGNORE INTO pages (url, site, kind, source, lastmod) VALUES (?, ?, ?, ?, ?)",
            [(p.url, p.site, p.kind, p.source, p.lastmod) for p in pages],
        )
        await self._connection.commit()
        return cursor.rowcount

    async def add_media(self, site: str, urls: list[str], first_seen_url: str):
        if not urls:
            return
        await self._connection.executemany(
            "INSERT OR IGNORE INTO media (url, site, first_seen_url) VALUES (?, ?, ?)",
            [(url, site, first_seen_url) for url in urls],
        )
        await self._connection.commit()

    async def add_segments(self, site: str, pairs: set[tuple[str, str]]):
        if not pairs:
            return
        await self._connection.executemany(
            "INSERT OR IGNORE INTO segments (site, segment, kind) VALUES (?, ?, ?)",
            [(site, segment, kind) for segment, kind in pairs],
        )
        await self._connection.commit()

    async def segments(self, site: str) -> dict[str, str]:
        cursor = await self._connection.execute("SELECT segment, kind FROM segments WHERE site = ?", (site,))
        return {row["segment"]: row["kind"] for row in await cursor.fetchall()}

    async def pending(
        self, site: str, kind: str | None, limit: int, include_failed: bool, max_attempts: int
    ) -> list[PageRef]:
        statuses = "('pending', 'failed')" if include_failed else "('pending')"
        kind_filter = "AND kind = ?" if kind else ""
        cursor = await self._connection.execute(
            f"""
            SELECT url, site, kind, source, lastmod, attempts FROM pages
            WHERE site = ? AND status IN {statuses} AND attempts < ? {kind_filter}
            ORDER BY discovered_at LIMIT ?
            """,
            (site, max_attempts, kind, limit) if kind else (site, max_attempts, limit),
        )
        return [PageRef.from_row(row) for row in await cursor.fetchall()]

    async def urls_of_kinds(self, site: str, kinds: Sequence[str]) -> list[str]:
        placeholders = ", ".join("?" * len(kinds))
        cursor = await self._connection.execute(
            f"SELECT url FROM pages WHERE site = ? AND kind IN ({placeholders})", (site, *kinds)
        )
        return [row["url"] for row in await cursor.fetchall()]

    async def reset_to_pending(self, site: str, kinds: Sequence[str]) -> int:
        """Queue already-captured rows again. Used for the kinds that enumerate a site
        rather than belong to it, which have to be re-walked to reveal new content."""
        placeholders = ", ".join("?" * len(kinds))
        cursor = await self._connection.execute(
            f"""
            UPDATE pages SET status = 'pending', attempts = 0, error = NULL
            WHERE site = ? AND kind IN ({placeholders}) AND status != 'pending'
            """,
            (site, *kinds),
        )
        await self._connection.commit()
        return cursor.rowcount

    async def supersede(self, site: str, kinds: Sequence[str]) -> int:
        """Stop crawling pages an API now serves. Only pending rows are touched, so
        anything already captured keeps its status and its file."""
        placeholders = ", ".join("?" * len(kinds))
        cursor = await self._connection.execute(
            f"UPDATE pages SET status = 'superseded' WHERE site = ? AND kind IN ({placeholders}) AND status = 'pending'",
            (site, *kinds),
        )
        await self._connection.commit()
        return cursor.rowcount

    async def fetched_urls(self, site: str, kind: str) -> list[str]:
        cursor = await self._connection.execute(
            "SELECT url FROM pages WHERE site = ? AND kind = ? AND status = 'fetched' ORDER BY fetched_at",
            (site, kind),
        )
        return [row["url"] for row in await cursor.fetchall()]

    async def fetched_kinds(self, site: str) -> list[str]:
        cursor = await self._connection.execute(
            "SELECT DISTINCT kind FROM pages WHERE site = ? AND status = 'fetched' ORDER BY kind", (site,)
        )
        return [row["kind"] for row in await cursor.fetchall()]

    async def seen_content(self, site: str, kind: str, sha256: str) -> bool:
        """Whether this exact body was already captured for this site and kind.

        Used to end paging chains. A spent pager here does not answer empty: rekhtadictionary
        serves the same fragment for every `pageIndex` past the last real one, so identical
        content is the only signal that a chain has run out. One chain reached pageIndex 7,911
        before this existed."""
        cursor = await self._connection.execute(
            "SELECT 1 FROM pages WHERE site = ? AND kind = ? AND sha256 = ? LIMIT 1", (site, kind, sha256)
        )
        return await cursor.fetchone() is not None

    async def mark_fetched(self, url: str, http_status: int, sha256: str, size: int):
        await self._connection.execute(
            """
            UPDATE pages SET status = 'fetched', http_status = ?, sha256 = ?, bytes = ?,
                fetched_at = ?, error = NULL
            WHERE url = ?
            """,
            (http_status, sha256, size, datetime.now(UTC).isoformat(), url),
        )
        await self._connection.commit()

    async def mark_failed(self, url: str, http_status: int | None, error: str):
        await self._connection.execute(
            """
            UPDATE pages SET status = 'failed', http_status = ?, error = ?, attempts = attempts + 1
            WHERE url = ?
            """,
            (http_status, error, url),
        )
        await self._connection.commit()

    async def counts(self) -> list[aiosqlite.Row]:
        cursor = await self._connection.execute(
            """
            SELECT site, kind, COUNT(*) AS total,
                   SUM(status = 'fetched') AS fetched,
                   SUM(status = 'failed') AS failed,
                   SUM(status = 'pending') AS pending,
                   SUM(CASE WHEN status = 'fetched' THEN bytes ELSE 0 END) AS bytes
            FROM pages GROUP BY site, kind ORDER BY site, total DESC
            """
        )
        return list(await cursor.fetchall())

    async def media_count(self) -> int:
        cursor = await self._connection.execute("SELECT COUNT(*) AS n FROM media")
        return (await cursor.fetchone())["n"]
