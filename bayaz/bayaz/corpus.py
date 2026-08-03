"""The parsed corpus: structured data extracted from the raw page store.

A separate database from the crawl manifest because they live different lives: the manifest
is crawl state, rebuilt from sitemaps; the corpus is derived data, rebuilt from raw/ by
re-parsing. `parsed` records which url each parser version has consumed, so parse runs
resume, and bumping a parser's version re-parses exactly its pages.

Dictionary senses arrive per language, and the three rekhtadictionary page variants each
carry their own language's sections in full while truncating the others. `replace_senses`
therefore keeps whichever variant supplied the most text for a language, which makes the
merge order-independent: parse the variants in any order and the full sections win.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    site TEXT NOT NULL,
    slug TEXT NOT NULL,
    headword TEXT,
    headword_hindi TEXT,
    headword_urdu TEXT,
    vazn TEXT,
    trivia TEXT,
    audio_url TEXT,
    video_url TEXT,
    UNIQUE (site, slug)
);

CREATE TABLE IF NOT EXISTS senses (
    entry_id INTEGER NOT NULL,
    lang TEXT NOT NULL,              -- en | hi | ur | ur_roman
    ord INTEGER NOT NULL,
    pos TEXT,
    definition TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_senses_entry ON senses(entry_id, lang);

CREATE TABLE IF NOT EXISTS entry_examples (
    entry_id INTEGER NOT NULL,
    lang TEXT NOT NULL,
    ord INTEGER NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entry_examples_entry ON entry_examples(entry_id);

CREATE TABLE IF NOT EXISTS shers (
    entry_id INTEGER NOT NULL,
    ord INTEGER NOT NULL,
    lines TEXT NOT NULL,             -- couplet, newline-joined
    lines_alt TEXT,                  -- second rendering when the page carries one
    poet TEXT,
    poet_url TEXT,
    ghazal_url TEXT
);
CREATE INDEX IF NOT EXISTS idx_shers_entry ON shers(entry_id);

CREATE TABLE IF NOT EXISTS relations (
    entry_id INTEGER NOT NULL,
    rel_type TEXT NOT NULL,          -- synonym antonym compound idiom proverb rhyming word-family related tag
    target_text TEXT NOT NULL,
    target_url TEXT,
    target_meaning TEXT,
    UNIQUE (entry_id, rel_type, target_text)
);

CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY,
    site TEXT NOT NULL,
    slug TEXT NOT NULL,
    work_type TEXT NOT NULL,
    title TEXT,
    title_translit TEXT,
    author_name TEXT,
    author_url TEXT,
    body TEXT,
    source TEXT,
    UNIQUE (site, slug)
);

CREATE TABLE IF NOT EXISTS work_tags (
    work_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    tag_url TEXT,
    UNIQUE (work_id, tag)
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    site TEXT NOT NULL,
    slug TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    name TEXT,
    name_hindi TEXT,
    name_urdu TEXT,
    name_translit TEXT,
    description TEXT,
    born TEXT,
    died TEXT,
    UNIQUE (site, slug)
);

CREATE TABLE IF NOT EXISTS parsed (
    url TEXT PRIMARY KEY,
    site TEXT NOT NULL,
    kind TEXT NOT NULL,
    version INTEGER NOT NULL,
    parsed_at TIMESTAMP NOT NULL
);
"""


@dataclass(slots=True)
class Sense:
    lang: str
    pos: str | None
    definition: str


@dataclass(slots=True)
class Sher:
    lines: str
    lines_alt: str | None
    poet: str | None
    poet_url: str | None
    ghazal_url: str | None


@dataclass(slots=True)
class Relation:
    rel_type: str
    target_text: str
    target_url: str | None = None
    target_meaning: str | None = None


@dataclass(slots=True)
class Entry:
    """One dictionary headword, possibly assembled from several page variants."""

    site: str
    slug: str
    headword: str | None = None
    headword_hindi: str | None = None
    headword_urdu: str | None = None
    vazn: str | None = None
    trivia: str | None = None
    audio_url: str | None = None
    video_url: str | None = None
    senses: list[Sense] = field(default_factory=list)
    examples: list[tuple[str, str]] = field(default_factory=list)  # (lang, text)
    shers: list[Sher] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)


@dataclass(slots=True)
class Work:
    site: str
    slug: str
    work_type: str
    title: str | None = None
    title_translit: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    body: str | None = None
    source: str | None = None
    tags: list[tuple[str, str | None]] = field(default_factory=list)  # (tag, url)


@dataclass(slots=True)
class Entity:
    site: str
    slug: str
    entity_type: str
    name: str | None = None
    name_hindi: str | None = None
    name_urdu: str | None = None
    name_translit: str | None = None
    description: str | None = None
    born: str | None = None
    died: str | None = None


class Corpus:
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

    async def parsed_urls(self, site: str, kind: str, version: int) -> set[str]:
        cursor = await self._connection.execute(
            "SELECT url FROM parsed WHERE site = ? AND kind = ? AND version >= ?", (site, kind, version)
        )
        return {row["url"] for row in await cursor.fetchall()}

    async def mark_parsed(self, url: str, site: str, kind: str, version: int):
        await self._connection.execute(
            """
            INSERT INTO parsed (url, site, kind, version, parsed_at) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET version = excluded.version, parsed_at = excluded.parsed_at
            """,
            (url, site, kind, version, datetime.now(UTC).isoformat()),
        )
        await self._connection.commit()

    async def _entry_id(self, site: str, slug: str) -> int:
        await self._connection.execute("INSERT OR IGNORE INTO entries (site, slug) VALUES (?, ?)", (site, slug))
        cursor = await self._connection.execute("SELECT id FROM entries WHERE site = ? AND slug = ?", (site, slug))
        return (await cursor.fetchone())["id"]

    async def upsert_entry(self, entry: Entry):
        entry_id = await self._entry_id(entry.site, entry.slug)
        # COALESCE keeps what another variant already supplied; a variant only adds.
        await self._connection.execute(
            """
            UPDATE entries SET
                headword = COALESCE(?, headword), headword_hindi = COALESCE(?, headword_hindi),
                headword_urdu = COALESCE(?, headword_urdu), vazn = COALESCE(?, vazn),
                trivia = COALESCE(?, trivia), audio_url = COALESCE(?, audio_url),
                video_url = COALESCE(?, video_url)
            WHERE id = ?
            """,
            (entry.headword, entry.headword_hindi, entry.headword_urdu, entry.vazn, entry.trivia, entry.audio_url, entry.video_url, entry_id),
        )
        for lang in {sense.lang for sense in entry.senses}:
            await self._replace_senses(entry_id, lang, [s for s in entry.senses if s.lang == lang])
        for lang in {lang for lang, _ in entry.examples}:
            await self._replace_examples(entry_id, lang, [t for g, t in entry.examples if g == lang])
        if entry.shers:
            await self._connection.execute("DELETE FROM shers WHERE entry_id = ?", (entry_id,))
            await self._connection.executemany(
                "INSERT INTO shers (entry_id, ord, lines, lines_alt, poet, poet_url, ghazal_url)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (entry_id, i, s.lines, s.lines_alt, s.poet, s.poet_url, s.ghazal_url)
                    for i, s in enumerate(entry.shers)
                ],
            )
        if entry.relations:
            await self._connection.executemany(
                "INSERT OR IGNORE INTO relations (entry_id, rel_type, target_text, target_url, target_meaning)"
                " VALUES (?, ?, ?, ?, ?)",
                [(entry_id, r.rel_type, r.target_text, r.target_url, r.target_meaning) for r in entry.relations],
            )
        await self._connection.commit()

    async def _replace_senses(self, entry_id: int, lang: str, senses: list[Sense]):
        cursor = await self._connection.execute(
            "SELECT SUM(LENGTH(definition)) AS n FROM senses WHERE entry_id = ? AND lang = ?", (entry_id, lang)
        )
        held = (await cursor.fetchone())["n"] or 0
        if sum(len(s.definition) for s in senses) <= held:
            return
        await self._connection.execute("DELETE FROM senses WHERE entry_id = ? AND lang = ?", (entry_id, lang))
        await self._connection.executemany(
            "INSERT INTO senses (entry_id, lang, ord, pos, definition) VALUES (?, ?, ?, ?, ?)",
            [(entry_id, lang, i, s.pos, s.definition) for i, s in enumerate(senses)],
        )

    async def _replace_examples(self, entry_id: int, lang: str, texts: list[str]):
        cursor = await self._connection.execute(
            "SELECT SUM(LENGTH(text)) AS n FROM entry_examples WHERE entry_id = ? AND lang = ?", (entry_id, lang)
        )
        held = (await cursor.fetchone())["n"] or 0
        if sum(len(t) for t in texts) <= held:
            return
        await self._connection.execute("DELETE FROM entry_examples WHERE entry_id = ? AND lang = ?", (entry_id, lang))
        await self._connection.executemany(
            "INSERT INTO entry_examples (entry_id, lang, ord, text) VALUES (?, ?, ?, ?)",
            [(entry_id, lang, i, t) for i, t in enumerate(texts)],
        )

    async def add_relations(self, site: str, slug: str, relations: list[Relation]):
        if not relations:
            return
        entry_id = await self._entry_id(site, slug)
        await self._connection.executemany(
            "INSERT OR IGNORE INTO relations (entry_id, rel_type, target_text, target_url, target_meaning)"
            " VALUES (?, ?, ?, ?, ?)",
            [(entry_id, r.rel_type, r.target_text, r.target_url, r.target_meaning) for r in relations],
        )
        await self._connection.commit()

    async def upsert_work(self, work: Work):
        await self._connection.execute(
            """
            INSERT INTO works (site, slug, work_type, title, title_translit, author_name, author_url, body, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site, slug) DO UPDATE SET
                work_type = excluded.work_type, title = excluded.title, title_translit = excluded.title_translit,
                author_name = excluded.author_name, author_url = excluded.author_url,
                body = excluded.body, source = excluded.source
            """,
            (
                work.site,
                work.slug,
                work.work_type,
                work.title,
                work.title_translit,
                work.author_name,
                work.author_url,
                work.body,
                work.source,
            ),
        )
        cursor = await self._connection.execute(
            "SELECT id FROM works WHERE site = ? AND slug = ?", (work.site, work.slug)
        )
        work_id = (await cursor.fetchone())["id"]
        await self._connection.executemany(
            "INSERT OR IGNORE INTO work_tags (work_id, tag, tag_url) VALUES (?, ?, ?)",
            [(work_id, tag, url) for tag, url in work.tags],
        )
        await self._connection.commit()

    async def upsert_entity(self, entity: Entity):
        """Facet and language variants of the same entity page each contribute their
        pieces; every column keeps the first non-null value a variant supplied."""
        await self._connection.execute(
            """
            INSERT INTO entities (site, slug, entity_type, name, name_hindi, name_urdu, name_translit,
                                  description, born, died)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site, slug) DO UPDATE SET
                entity_type = excluded.entity_type,
                name = COALESCE(name, excluded.name),
                name_hindi = COALESCE(name_hindi, excluded.name_hindi),
                name_urdu = COALESCE(name_urdu, excluded.name_urdu),
                name_translit = COALESCE(name_translit, excluded.name_translit),
                description = COALESCE(description, excluded.description),
                born = COALESCE(born, excluded.born), died = COALESCE(died, excluded.died)
            """,
            (
                entity.site,
                entity.slug,
                entity.entity_type,
                entity.name,
                entity.name_hindi,
                entity.name_urdu,
                entity.name_translit,
                entity.description,
                entity.born,
                entity.died,
            ),
        )
        await self._connection.commit()

    async def stats(self) -> dict[str, int]:
        out = {}
        for table in ("entries", "senses", "shers", "relations", "works", "work_tags", "entities", "parsed"):
            cursor = await self._connection.execute(f"SELECT COUNT(*) AS n FROM {table}")
            out[table] = (await cursor.fetchone())["n"]
        return out
