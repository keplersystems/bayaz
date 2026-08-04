"""rekhta.org's poetry API, parsed into the corpus.

The three-script fields are the point of this corpus rather than a convenience: `E`, `H`
and `U` suffixes are the same text rendered in Roman, Devanagari and Nastaliq, not
translations, so all three are kept. The text itself arrives as a nested tree whose leaves
carry a machine code per word, and preserving those codes in reading order is what lets the
poetry join the dictionary at word level.
"""

import json
from urllib.parse import urlsplit

from bayaz.corpus import Entity, Entry, Sense, Work
from bayaz.parse import Parsed
from bayaz.rekhta import query

VERSION = 1

SITE = "rekhta"

_LANG_FIELD = {1: "", 2: "_hindi", 3: "_urdu"}
_LANG_CODE = {1: "en", 2: "hi", 3: "ur"}


def parse(site: str, url: str, body: str) -> Parsed:
    payload = json.loads(body)
    result = payload.get("R")
    if result is None:
        return Parsed()

    endpoint = urlsplit(url).path.rsplit("/", 1)[-1]
    params = query(url)
    match endpoint:
        case "GetContentById":
            return _content(result, params)
        case "GetPoetCompleteProfile" | "GetPoetProfile":
            return _poet(result, params)
        case "GetWordMeaningByLang" | "GetGroupWordMeaningByLang":
            return _word(result, params)
        case "GetPoetsListWithPaging":
            return _poet_list(result)
        case _:
            # Listing pages carry no content the detail records do not, so they are
            # captured for the archive but contribute nothing to the corpus.
            return Parsed()


def _text(row: dict, prefix: str) -> tuple[str | None, str | None, str | None]:
    return (row.get(f"{prefix}E"), row.get(f"{prefix}H"), row.get(f"{prefix}U"))


def _lines(tree) -> list[list[tuple[str, str | None]]]:
    """The tree as lines of (word, code), in reading order.

    Line structure is recovered by grouping: a node holding word leaves is a line, and
    anything above it is a container, which avoids depending on key names that differ
    between the content and couplet endpoints."""
    lines: list[list[tuple[str, str | None]]] = []

    def walk(node):
        if isinstance(node, dict):
            words: list[tuple[str, str | None]] = []
            for value in node.values():
                if isinstance(value, list) and all(isinstance(v, dict) and "W" in v for v in value) and value:
                    words += [(v["W"], v.get("M")) for v in value]
                else:
                    walk(value)
            if words:
                lines.append(words)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(tree)
    return lines


def _content(result: dict, params: dict) -> Parsed:
    content_id = params.get("contentId", "")
    lang = int(params.get("lang", "1"))
    title = _text(result, "T")
    poet = result.get("Poet") or {}

    work = Work(
        site=SITE,
        slug=content_id,
        work_type=result.get("CTS") or result.get("CT") or "content",
        author_name=poet.get("NE") or result.get("PE"),
        author_url=None,
        source=result.get("SS") or None,
    )
    work.title, work.title_hindi, work.title_urdu = title
    work.title_translit = title[0]

    tree = result.get("CR")
    if isinstance(tree, str):
        try:
            tree = json.loads(tree)
        except json.JSONDecodeError:
            tree = None

    lines = _lines(tree)
    body = "\n".join(" ".join(word for word, _ in line) for line in lines) or None
    setattr(work, f"body{_LANG_FIELD.get(lang, '')}" if lang != 1 else "body", body)

    work.tags = [(tag.get("NE") or tag.get("NH") or "", None) for tag in result.get("Tags") or [] if tag.get("NE")]

    words = [
        (lang, line_ord, word_ord, word, code)
        for line_ord, line in enumerate(lines)
        for word_ord, (word, code) in enumerate(line)
    ]
    return Parsed(works=[work], work_words={content_id: words})


def _poet(result: dict, params: dict) -> Parsed:
    header = result.get("CH") or result
    name = _text(header, "N")
    profile = _text(header, "D")
    entity = Entity(
        site=SITE,
        slug=params.get("poetId", ""),
        entity_type="poets",
        name=name[0],
        name_hindi=name[1],
        name_urdu=name[2],
        description=next((d for d in profile if d), None),
        born=header.get("DOB") or None,
        died=header.get("DOD") or None,
    )
    return Parsed(entities=[entity])


def _poet_list(result: dict) -> Parsed:
    entities = []
    for row in result.get("P") or []:
        if not row.get("I"):
            continue
        name = _text(row, "N")
        entities.append(
            Entity(
                site=SITE,
                slug=row["I"],
                entity_type="poets",
                name=name[0],
                name_hindi=name[1],
                name_urdu=name[2],
            )
        )
    return Parsed(entities=entities)


def _word(result: dict, params: dict) -> Parsed:
    code = params.get("word", "")
    lang = _LANG_CODE.get(int(params.get("lang", "1")), "en")
    forms = _text(result, "W")
    entry = Entry(
        site=SITE,
        slug=code,
        headword=forms[0] or params.get("selectedWord"),
        headword_hindi=forms[1],
        headword_urdu=forms[2],
    )
    for field in ("ME", "MH", "MU"):
        meaning = result.get(field)
        if isinstance(meaning, str) and meaning.strip():
            entry.senses.append(Sense(lang={"ME": "en", "MH": "hi", "MU": "ur"}[field], pos=None, definition=meaning.strip()))
    if not entry.senses and isinstance(result.get("M"), str) and result["M"].strip():
        entry.senses.append(Sense(lang=lang, pos=None, definition=result["M"].strip()))
    entry.audio_url = next((result.get(k) for k in ("AMF", "AOF") if (result.get(k) or "").startswith("http")), None)
    return Parsed(entries=[entry])
