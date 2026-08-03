"""The dictionary JSON APIs, parsed into the same corpus as the HTML.

One extractor serves both. On rekhtadictionary `RML[0].ML[i]` is a language block; on
Hindwi `RML[i]` is a dialect block with `ML[]` inside it. `_blocks` normalises that; the
rest is shared. Field names follow docs/*-api.md.
"""

from urllib.parse import urlsplit

from bayaz.apis import is_miss, parse_payload
from bayaz.corpus import Entry, Relation, Sense, Sher
from bayaz.parse import Parsed, assign_scripts, script_of

VERSION = 1

# Transcribed literally: the API pluralises inconsistently
_REL_TYPES = {
    "synonyms": "synonym",
    "antonyms": "antonym",
    "compound": "compound",
    "idioms": "idiom",
    "proverb": "proverb",
    "qaafiya": "rhyming",
}

def parse(site: str, url: str, body: str) -> Parsed:
    payload = parse_payload(body)
    query = _query(url)
    if "category" in query:
        return _parse_listing(site, query, payload)
    if is_miss(payload):
        return Parsed()

    result = payload["R"]
    basic = result.get("BI") or {}
    slug = _slug_of(url)
    entry = Entry(site=site, slug=slug)

    assign_scripts(entry, (basic.get("W1"), basic.get("W2"), basic.get("W3")))
    entry.headword = entry.headword or slug
    entry.audio_url = next((u for u in (basic.get("AMF"), basic.get("AOF")) if (u or "").endswith(".mp3")), None)

    seen_shers: set[str] = set()
    for label, container in _blocks(result):
        lang = _lang_of(label, container)
        for group in container.get("R") or []:
            _senses(entry, lang, group)
            _shers(entry, group, seen_shers)

    for group in _relation_groups(result):
        _relations(entry, group)
    _additional_info(entry, result)
    return Parsed(entries=[entry])


def _query(url: str) -> dict[str, str]:
    return dict(pair.split("=", 1) for pair in urlsplit(url).query.split("&") if "=" in pair)


def _slug_of(url: str) -> str:
    if slug := _query(url).get("wordId"):
        return slug
    raise ValueError(f"no wordId in {url}")


def _parse_listing(site: str, query: dict[str, str], payload: dict) -> Parsed:
    """Overflow past a relation group's inline ceiling, keyed to the word it belongs to."""
    rel_type = _REL_TYPES.get(query.get("category") or "")
    items = payload.get("R") or []
    if rel_type is None or not items:
        return Parsed()
    return Parsed(relations_for={query["wordId"]: _relation_items(rel_type, items)})


def _blocks(result: dict) -> list[tuple[str, dict]]:
    return [
        (meaning.get("HT") or outer.get("HT") or "", meaning)
        for outer in result.get("RML") or []
        for meaning in outer.get("ML") or []
    ]


def _lang_of(label: str, container: dict) -> str:
    if "english" in label.lower():
        return "en"
    return script_of(label) if label else script_of(_first_sense_text(container) or "")


def _first_sense_text(container: dict) -> str | None:
    for group in container.get("R") or []:
        for meaning_group in group.get("MGL") or []:
            for sense in meaning_group.get("WM") or []:
                if text := sense.get("C"):
                    return text
    return None


def _senses(entry: Entry, lang: str, group: dict) -> None:
    for meaning_group in group.get("MGL") or []:
        pos = meaning_group.get("MT") or None
        for sense in meaning_group.get("WM") or []:
            if text := (sense.get("C") or "").strip():
                entry.senses.append(Sense(lang=lang, pos=pos, definition=text))
            entry.examples += [(lang, example) for example in _examples(sense)]


def _examples(sense: dict) -> list[str]:
    example = sense.get("ME")
    if not isinstance(example, dict):
        return []
    return [text.strip() for item in example.get("MEN") or [] if (text := item.get("EN") or "")]


def _shers(entry: Entry, group: dict, seen: set[str]) -> None:
    # Text is word-tokenised so the site can link each word. Each language call returns the
    # couplet in its own script, so all renderings are kept and only repeats within a call
    # are dropped.
    sher_list = group.get("SL")
    items = (sher_list.get("R") if isinstance(sher_list, dict) else sher_list) or []
    for item in items:
        text = " ".join(token.get("W") or "" for token in item.get("RW") or []).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        entry.shers.append(
            Sher(lines=text, lines_alt=None, poet=item.get("PN") or None, poet_url=None, ghazal_url=None)
        )


def _relation_groups(result: dict) -> list[dict]:
    return [group for outer in result.get("RML") or [] for group in (outer.get("R") or []) if group.get("CT")]


def _relations(entry: Entry, group: dict) -> None:
    rel_type = _REL_TYPES.get(group.get("CT") or "")
    if rel_type is None:
        return
    entry.relations += _relation_items(rel_type, group.get("R") or [])


def _relation_items(rel_type: str, items: list) -> list[Relation]:
    # Rhyming words carry tokenised text under QW instead of the W1/W2/W3 of every other type
    relations = []
    for item in items:
        if tokens := item.get("QW"):
            if text := " ".join(t.get("W") or "" for t in tokens).strip():
                relations.append(Relation(rel_type, text, None, None))
            continue
        for value in (item.get("W1"), item.get("W2"), item.get("W3")):
            if value:
                relations.append(Relation(rel_type, value, None, item.get("WM") or None))
    return relations


def _additional_info(entry: Entry, result: dict) -> None:
    rows = []
    for info in result.get("AIL") or []:
        values = [value for item in info.get("R") or [] if (value := item.get("WV"))]
        if not values:
            continue
        category = info.get("CT") or ""
        if category == "vazn":
            entry.vazn = entry.vazn or values[0]
            continue
        if category == "word-family":
            entry.relations += [Relation("word-family", value) for value in values]
        elif category == "tags":
            entry.relations += [Relation("tag", value) for value in values]
        rows.append(f"{(info.get('ST') or '').strip()} {', '.join(values)}".strip())
    if rows:
        entry.trivia = "\n".join(rows)
