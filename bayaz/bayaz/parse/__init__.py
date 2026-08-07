"""Parse: raw captures into the corpus, offline.

Each (site, kind) with structure worth extracting has a parser; kinds without one (blog,
static, listing chrome) simply stay unparsed. Parsers are versioned: bumping a module's
VERSION re-parses exactly its pages on the next run, which is the whole point of keeping
the raw store — extraction mistakes cost a local re-parse, never a re-crawl.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from bayaz import config, rawstore
from bayaz.corpus import Corpus, Entity, Entry, Relation, Work
from bayaz.db import Database
from bayaz.sites import SITES

logger = logging.getLogger(__name__)


_DEVANAGARI = range(0x0900, 0x0980)
_ARABIC = range(0x0600, 0x0700)


def script_of(text: str) -> str:
    for char in text:
        if ord(char) in _DEVANAGARI:
            return "hi"
        if ord(char) in _ARABIC:
            return "ur"
    return "en"


def assign_scripts(entry, values) -> None:
    """Which slot a headword lands in is decided by its script, never by its position: both
    the API's W1/W2/W3 and the page's own heading order rotate with the requested language."""
    for value in values:
        if not value:
            continue
        match script_of(value):
            case "hi":
                entry.headword_hindi = entry.headword_hindi or value
            case "ur":
                entry.headword_urdu = entry.headword_urdu or value
            case _:
                entry.headword = entry.headword or value


@dataclass(slots=True)
class Parsed:
    """Everything one page contributed. `relations_for` attaches relations to entries the
    page is about but does not define — a tag page names many words, a fragment extends
    one — keyed by the entry slug they belong to."""

    entries: list[Entry] = field(default_factory=list)
    relations_for: dict[str, list[Relation]] = field(default_factory=dict)
    works: list[Work] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    # Word occurrences per work slug: (lang, line_ord, word_ord, word, code). Only the
    # rekhta poetry API supplies these; the sites' HTML carries no word-level codes.
    work_words: dict[str, list[tuple[int, int, int, str, str | None]]] = field(default_factory=dict)


Parser = Callable[[str, str, str], Parsed]  # (site, url, html) -> Parsed


def _registry() -> dict[tuple[str, str], tuple[Parser, int]]:
    from bayaz.parse import dictapi, platform, rekhtaapi, rekhtadict, rekhtaweb, taglist

    table: dict[tuple[str, str], tuple[Parser, int]] = {}
    for kind in ("word", "synonym", "antonym", "compound", "idiom", "proverb", "word-family", "tag", "partial"):
        table[("rekhtadictionary", kind)] = (rekhtadict.parse, rekhtadict.VERSION)
    for site in ("hindwi", "sufinama"):
        for kind in ("dict", "work", "entity"):
            table[(site, kind)] = (platform.parse, platform.VERSION)
    for site in ("hindwi", "sufinama"):
        # Tag pages and their paging fragments share a template and a parser: the fragment
        # is the same list of sections without the surrounding page.
        for kind in ("tag", "tag-page"):
            table[(site, kind)] = (taglist.parse, taglist.VERSION)
    table[("rekhtadictionary", "word-api")] = (dictapi.parse, dictapi.VERSION)
    table[("rekhtadictionary", "wordlist-api")] = (dictapi.parse, dictapi.VERSION)
    table[("hindwi", "dict-api")] = (dictapi.parse, dictapi.VERSION)
    for kind in ("content", "poet", "poets", "word", "word-group"):
        table[("rekhta", kind)] = (rekhtaapi.parse, rekhtaapi.VERSION)
    table[("rekhta", "work-text")] = (rekhtaweb.parse, rekhtaweb.VERSION)
    return table


def parsed_kinds() -> set[tuple[str, str]]:
    """The (site, kind) pairs some parser consumes. Anything outside this set is archived
    but never enters the corpus, so callers that wait on parse state must treat it as done
    rather than wait forever."""
    return set(_registry())


async def _apply(corpus: Corpus, result: Parsed, site: str):
    for entry in result.entries:
        await corpus.upsert_entry(entry)
    for slug, relations in result.relations_for.items():
        await corpus.add_relations(site, slug, relations)
    for work in result.works:
        await corpus.upsert_work(work)
    for entity in result.entities:
        await corpus.upsert_entity(entity)
    for slug, words in result.work_words.items():
        await corpus.set_work_words(site, slug, words)


async def run(site_names: list[str] | None, kind: str | None, limit: int | None):
    table = _registry()
    sites = [SITES[name] for name in (site_names or SITES)]
    async with Database(config.DATABASE_PATH) as db, Corpus(config.DATA_DIR / "corpus.db") as corpus:
        for site in sites:
            kinds = [k for (s, k) in table if s == site.name and (kind is None or k == kind)]
            for k in kinds:
                parser, version = table[(site.name, k)]
                fetched = await db.fetched_urls(site.name, k)
                done = await corpus.parsed_urls(site.name, k, version)
                todo = [u for u in fetched if u not in done]
                if limit is not None:
                    todo = todo[:limit]
                if not todo:
                    continue
                logger.info(f"{site.name}/{k}: parsing {len(todo)} page(s)")
                failed = 0
                for url in todo:
                    try:
                        result = parser(site.name, url, rawstore.read(site.name, url, k))
                        await _apply(corpus, result, site.name)
                    except Exception:
                        failed += 1
                        logger.exception(f"{url}: parse failed")
                        continue
                    await corpus.mark_parsed(url, site.name, k, version)
                if failed:
                    logger.warning(f"{site.name}/{k}: {failed} page(s) failed to parse")
        stats = await corpus.stats()
    logger.info("corpus: " + ", ".join(f"{k}={v:,}" for k, v in stats.items()))
