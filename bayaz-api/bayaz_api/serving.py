"""Build `serve.db` from the published corpus.

The corpus is shaped for writing and indexed only where the parse run needed it, so the api
serves a database derived from it: `parsed` dropped, `works.author_id` resolved, fts5 added.
See `bayaz-api/README.md` for why each of those is necessary.
"""

import argparse
import logging
import re
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE entries (
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

CREATE TABLE senses (
    entry_id INTEGER NOT NULL,
    lang TEXT NOT NULL,
    ord INTEGER NOT NULL,
    pos TEXT,
    definition TEXT NOT NULL
);
CREATE INDEX idx_senses_entry ON senses(entry_id, lang);

CREATE TABLE entry_examples (
    entry_id INTEGER NOT NULL,
    lang TEXT NOT NULL,
    ord INTEGER NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX idx_entry_examples_entry ON entry_examples(entry_id);

CREATE TABLE shers (
    entry_id INTEGER NOT NULL,
    ord INTEGER NOT NULL,
    lines TEXT NOT NULL,
    lines_alt TEXT,
    poet TEXT,
    poet_url TEXT,
    ghazal_url TEXT
);
CREATE INDEX idx_shers_entry ON shers(entry_id);

CREATE TABLE relations (
    entry_id INTEGER NOT NULL,
    rel_type TEXT NOT NULL,
    target_text TEXT NOT NULL,
    target_url TEXT,
    target_meaning TEXT
);
CREATE INDEX idx_relations_entry ON relations(entry_id, rel_type);

CREATE TABLE entities (
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
CREATE INDEX idx_entities_browse ON entities(site, entity_type, name_translit);

CREATE TABLE works (
    id INTEGER PRIMARY KEY,
    site TEXT NOT NULL,
    slug TEXT NOT NULL,
    work_type TEXT NOT NULL,
    title TEXT,
    title_translit TEXT,
    title_hindi TEXT,
    title_urdu TEXT,
    author_name TEXT,
    author_url TEXT,
    author_id INTEGER REFERENCES entities(id),
    body TEXT,
    body_hindi TEXT,
    body_urdu TEXT,
    explanation TEXT,
    translation TEXT,
    source TEXT,
    UNIQUE (site, slug)
);
CREATE INDEX idx_works_browse ON works(site, work_type, id);
CREATE INDEX idx_works_author ON works(author_id, id);

CREATE TABLE work_tags (
    work_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    tag_url TEXT,
    UNIQUE (work_id, tag)
);
CREATE INDEX idx_work_tags_tag ON work_tags(tag, work_id);

CREATE TABLE work_words (
    work_id INTEGER NOT NULL,
    lang TEXT NOT NULL,
    line_ord INTEGER NOT NULL,
    word_ord INTEGER NOT NULL,
    word TEXT NOT NULL,
    code TEXT,
    PRIMARY KEY (work_id, lang, line_ord, word_ord)
);
CREATE INDEX idx_work_words_code ON work_words(code);
"""

# `works_fts` mirrors the columns it indexes from `works` rather than duplicating them,
# which is what `content=` buys; `entries_fts` cannot, because an entry's definitions live
# in `senses` and external content fts5 reads one table.
FTS = """
CREATE VIRTUAL TABLE works_fts USING fts5(
    title, title_translit, title_hindi, title_urdu, body, body_hindi, body_urdu,
    content='works', content_rowid='id', tokenize="unicode61 remove_diacritics 2"
);

CREATE VIRTUAL TABLE entries_fts USING fts5(
    headword, headword_hindi, headword_urdu, definitions,
    tokenize="unicode61 remove_diacritics 2"
);

CREATE VIRTUAL TABLE entities_fts USING fts5(
    name, name_hindi, name_urdu, name_translit,
    content='entities', content_rowid='id', tokenize="unicode61 remove_diacritics 2"
);
"""

_COPY = (
    "entries",
    "senses",
    "entry_examples",
    "shers",
    "relations",
    "entities",
    "work_tags",
    "work_words",
)

_WORK_COLUMNS = (
    "id, site, slug, work_type, title, title_translit, title_hindi, title_urdu,"
    " author_name, author_url, body, body_hindi, body_urdu, explanation, translation, source"
)

_ENTITY_PATH = re.compile(r"/(?:poets|authors|translators|editors|publishers|artists|contributors)/([^/?#]+)")


def entity_slug(author_url: str | None) -> str | None:
    """The poet an `author_url` points at, as `entities.slug` spells it.

    rekhta stores a bare guid, which is already the slug. The platform sites store a url
    whose poet segment is followed by an optional work-type segment, so the poet is the
    segment after the entity type, never the last one.
    """
    if not author_url:
        return None
    match = _ENTITY_PATH.search(author_url)
    return match.group(1) if match else author_url


def _step(label: str):
    start = time.perf_counter()

    def done(detail: str = ""):
        logger.info(f"{label}: {time.perf_counter() - start:.1f}s {detail}".rstrip())

    return done


def build(corpus_path: Path, serve_path: Path):
    if not corpus_path.exists():
        raise FileNotFoundError(corpus_path)
    serve_path.unlink(missing_ok=True)
    serve_path.parent.mkdir(parents=True, exist_ok=True)

    # uri=True on the main connection is what lets ATTACH take a `file:...?mode=ro` name,
    # which keeps the published corpus untouchable for the length of the build.
    connection = sqlite3.connect(f"file:{serve_path.resolve()}", uri=True)
    connection.create_function("entity_slug", 1, entity_slug, deterministic=True)
    connection.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;")
    connection.executescript(SCHEMA)
    connection.execute("ATTACH DATABASE ? AS corpus", (f"file:{corpus_path.resolve()}?mode=ro",))

    for table in _COPY:
        done = _step(f"copy {table}")
        cursor = connection.execute(f"INSERT INTO {table} SELECT * FROM corpus.{table}")
        connection.commit()
        done(f"{cursor.rowcount:,} rows")

    done = _step("copy works")
    connection.execute(f"INSERT INTO works ({_WORK_COLUMNS}) SELECT {_WORK_COLUMNS} FROM corpus.works")
    connection.commit()
    done()

    done = _step("resolve author_id")
    cursor = connection.execute(
        "UPDATE works SET author_id = ("
        "  SELECT e.id FROM entities e WHERE e.site = works.site AND e.slug = entity_slug(works.author_url)"
        ") WHERE author_url IS NOT NULL"
    )
    connection.commit()
    linked = connection.execute("SELECT count(*) FROM works WHERE author_id IS NOT NULL").fetchone()[0]
    total = connection.execute("SELECT count(*) FROM works").fetchone()[0]
    done(f"{linked:,} of {total:,} works linked to a poet ({linked / total:.1%})")

    connection.executescript(FTS)

    done = _step("index works_fts")
    connection.execute("INSERT INTO works_fts(works_fts) VALUES ('rebuild')")
    connection.commit()
    done()

    done = _step("index entries_fts")
    connection.execute(
        "INSERT INTO entries_fts(rowid, headword, headword_hindi, headword_urdu, definitions)"
        " SELECT e.id, e.headword, e.headword_hindi, e.headword_urdu,"
        "        (SELECT group_concat(s.definition, ' ') FROM senses s WHERE s.entry_id = e.id)"
        " FROM entries e"
    )
    connection.commit()
    done()

    # ANALYZE writes to every attached database, and the corpus is attached read-only.
    connection.execute("DETACH DATABASE corpus")

    done = _step("index entities_fts")
    connection.execute("INSERT INTO entities_fts(entities_fts) VALUES ('rebuild')")
    connection.commit()
    done()

    done = _step("analyze")
    connection.execute("ANALYZE")
    connection.commit()
    done()

    connection.close()
    logger.info(f"{serve_path}: {serve_path.stat().st_size / 1e9:.2f} GB")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser(description="Build the serving database from the parsed corpus")
    parser.add_argument("corpus", type=Path, help="path to corpus.db")
    parser.add_argument("serve", type=Path, help="path to write serve.db")
    arguments = parser.parse_args()
    build(arguments.corpus, arguments.serve)
