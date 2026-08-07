"""rekhta.org's poetry API, parsed into the corpus.

The three-script fields are the point of this corpus rather than a convenience: `E`, `H`
and `U` suffixes are the same text rendered in Roman, Devanagari and Nastaliq, not
translations, so all three are kept. The text itself arrives as a nested tree whose leaves
carry a machine code per word, and preserving those codes in reading order is what lets the
poetry join the dictionary at word level.
"""

import json
import re
from urllib.parse import urlsplit

from bayaz.corpus import Entity, Entry, Sense, Work
from bayaz.parse import Parsed
from bayaz.rekhta import query, text_tree

VERSION = 2

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


_TAG = re.compile(r"<[^>]+>")


def _part(tree, key: str) -> list:
    """One part of the text, gathered across every stanza.

    `P` holds the stanzas and each carries three parallel parts: the verse under `L`, an
    English translation under `T`, and Rekhta AI's interpretation under `E`. They share the
    line/word shape, so walking the tree whole appends translation and interpretation to the
    verse, markup and all. Measured before this existed: 1% of content records carry a
    non-empty `T` or `E`, and 3,130 body fields had `<h6>Interpretation: Rekhta AI</h6>` and
    its commentary run onto the end of the poem."""
    if not isinstance(tree, dict):
        return []
    return [
        part for stanza in tree.get("P") or [] if isinstance(stanza, dict) for part in (stanza.get(key) or [])
    ]


def _prose(part: list) -> str | None:
    """A translation or interpretation as plain text. Its words carry markup the verse never
    does, including the site's own `nonContent` spans, so tags are stripped rather than kept."""
    text = "\n".join(" ".join(word for word, _ in line) for line in _lines(part))
    return " ".join(_TAG.sub(" ", text).split()) or None


def _lines(tree) -> list[list[tuple[str, str | None]]]:
    """One part as lines of (word, code), in reading order.

    Within a part the shape is line -> word and both levels use `W` for their children, so
    they are told apart by type rather than by key: a word's `W` is the word itself as a
    string, while a line's `W` is the list of them."""
    lines: list[list[tuple[str, str | None]]] = []

    def walk(node):
        if isinstance(node, dict):
            children = node.get("W")
            if isinstance(children, list) and any(isinstance(c, dict) and isinstance(c.get("W"), str) for c in children):
                lines.append([(c["W"], c.get("M")) for c in children if isinstance(c.get("W"), str)])
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(tree)
    return lines


def _content(result: dict, params: dict) -> Parsed:
    content_id = params.get("contentId", "")
    lang = int(params.get("lang", "1"))
    poet = result.get("Poet") or {}

    # `CT` is the title in the requested script and `TS` the content type's slug, despite
    # `T`-prefixed fields being titles everywhere else in this API.
    work = Work(
        site=SITE,
        slug=content_id,
        work_type=result.get("TS") or "content",
        # The inlined poet uses PN/PI rather than the NE/NH/NU triple the poet endpoints
        # return, so it carries one rendering in the requested script and its id.
        author_name=poet.get("PN"),
        author_url=poet.get("PI"),
        source=result.get("CS") or None,
    )
    title = (result.get("CT") or "").strip() or None
    match lang:
        case 2:
            work.title_hindi = title
        case 3:
            work.title_urdu = title
        case _:
            work.title = work.title_translit = title

    tree = text_tree(result)
    lines = _lines(_part(tree, "L"))
    body = "\n".join(" ".join(word for word, _ in line) for line in lines) or None
    setattr(work, f"body{_LANG_FIELD.get(lang, '')}" if lang != 1 else "body", body)
    work.explanation = _prose(_part(tree, "E"))
    work.translation = _prose(_part(tree, "T"))

    work.tags = [(name, tag.get("TS")) for tag in result.get("Tags") or [] if (name := tag.get("TN"))]

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


# The script suffix whose text belongs to each requested definition language. All nine
# M{n}{E,H,U} fields are present on every call, but their contents change with `lang`, so
# taking only the matching suffix keeps the three languages distinct instead of storing the
# same definition three times under different labels.
_SENSE_SUFFIX = {1: "E", 2: "H", 3: "U"}

_SENSE_FIELD = re.compile(r"^M(\d+)([EHU])$")


def _word(result: dict, params: dict) -> Parsed:
    code = params.get("word", "")
    lang = int(params.get("lang", "1"))
    entry = Entry(
        site=SITE,
        slug=code,
        headword=result.get("E") or params.get("selectedWord"),
        headword_hindi=result.get("H"),
        headword_urdu=result.get("U"),
        trivia=_origin(result),
    )

    suffix = _SENSE_SUFFIX.get(lang, "E")
    numbered = []
    for field, value in result.items():
        match = _SENSE_FIELD.match(field)
        if match and match.group(2) == suffix and isinstance(value, str) and value.strip():
            numbered.append((int(match.group(1)), value.strip()))
    entry.senses = [
        Sense(lang=_LANG_CODE.get(lang, "en"), pos=result.get(f"P{suffix}") or None, definition=text)
        for _, text in sorted(numbered)
    ]

    entry.audio_url = next((result.get(k) for k in ("AMF", "AOF") if (result.get(k) or "").startswith("http")), None)
    return Parsed(entries=[entry])


def _origin(result: dict) -> str | None:
    origins = [result.get(f"O{s}") for s in ("E", "H", "U")]
    named = [o.strip() for o in origins if isinstance(o, str) and o.strip()]
    return f"Origin: {' / '.join(named)}" if named else None
