"""rekhtadictionary.com: the word page and everything orbiting it.

A word's data is spread across three page variants (each fully expands only its own
language's meaning sections; corpus merging keeps the fullest), standalone relation pages,
and paging fragments. Every parser here lands on the same entry slug — the word part of
the url — so the pieces assemble no matter what order they parse in.

Extraction is maximal: scripts, meter, per-language senses with POS, in-section usage
examples, sher examples with both renderings and their attribution, every relation list
with inline meanings, and the trivia section. Skipped as chrome: blogs, subscription and
donation blocks, share widgets, SEO tag paragraphs, "related searched words".
"""

import re
from urllib.parse import parse_qsl, urlsplit

from selectolax.parser import HTMLParser, Node

from bayaz.corpus import Entry, Relation, Sense, Sher
from bayaz.parse import Parsed, assign_scripts

VERSION = 1

_AUDIO_CDN = "https://rekhta.pc.cdn.bitgravity.com/Images/SiteImages/DictionaryAudio"
_GUID = re.compile(r"^[0-9a-fA-F-]{36}$")

_LANG_BY_SEQ = {
    "languageSequence_DetailsPage_1": "en",
    "languageSequence_DetailsPage_2": "hi",
    "languageSequence_DetailsPage_3": "ur",
    "languageSequence_DetailsPage_0": "ur_roman",
}

# Section headers -> relation type, matched case-insensitively on the English header text
_REL_HEADERS = (
    ("synonym", "synonym"),
    ("antonym", "antonym"),
    ("compound", "compound"),
    ("idiom", "idiom"),
    ("proverb", "proverb"),
    ("rhyming", "rhyming"),
)

_REL_BY_CATEGORY = (
    ("compound", "compound"),
    ("idiom", "idiom"),
    ("proverb", "proverb"),
    ("synonym", "synonym"),
    ("antonym", "antonym"),
    ("rhym", "rhyming"),
)

_WORD_PREFIXES = ("meaning-of-",)


def _clean(text: str) -> str:
    text = re.sub(r"\s*,\s*(?:,\s*)+", ", ", " ".join(text.split()))
    return text.strip(" ,•")


def _slug(url: str) -> str:
    path = urlsplit(url).path.strip("/")
    for prefix in _WORD_PREFIXES:
        if path.startswith(prefix):
            return path.removeprefix(prefix)
    return path


def _rel_slug(url: str, marker: str) -> str:
    """synonyms-of-X, proverbs-containing-X ... -> X"""
    path = urlsplit(url).path.strip("/")
    return path.partition(marker)[2] or path


def parse(site: str, url: str, html: str) -> Parsed:
    path = urlsplit(url).path.strip("/")
    if path.startswith("PartialWordLoading"):
        return _parse_partial(site, url, html)
    if path.startswith("word-family/"):
        return _parse_word_family(site, url, html)
    if path.startswith("tags/"):
        return _parse_tag_page(site, url, html)
    if "-of-" in path and not path.startswith(("meaning-of-", "urdu-meaning-of-")):
        return _parse_relation_page(site, url, html)
    if "-containing-" in path:
        return _parse_relation_page(site, url, html)
    return _parse_word(site, url, html)


def _parse_word(site: str, url: str, html: str) -> Parsed:
    tree = HTMLParser(html)
    entry = Entry(site=site, slug=_slug(url))

    if head := tree.css_first(".rdWordDsplyFormat"):
        forms = [_clean(h2.text())] if (h2 := head.css_first("h2")) else []
        if h3 := head.css_first("h3"):
            forms += [_clean(part) for part in h3.text().split("•")]
        assign_scripts(entry, forms)

    if vazn := tree.css_first(".rdSrchWrdVazn"):
        entry.vazn = _clean(vazn.text().split(":", 1)[-1]) or None

    entry.audio_url = _audio(tree)

    seen_sher: set[str] = set()
    for section in tree.css(".rdPartsofSpeechContainer"):
        classes = (section.attributes.get("class") or "").split()
        if lang := next((_LANG_BY_SEQ[c] for c in classes if c in _LANG_BY_SEQ), None):
            _parse_language_section(section, lang, entry, seen_sher)
            continue
        header = section.css_first("h2, h3")
        header_text = header.text().lower() if header else ""
        if "interesting" in header_text:
            entry.trivia = _trivia(section, header)
        elif rel_type := next((rel for marker, rel in _REL_HEADERS if marker in header_text), None):
            entry.relations += _anchor_relations(section, rel_type)
        elif "tags for" in header_text:
            entry.relations += [
                Relation("tag", _clean(a.text()), _href(a))
                for a in section.css("a[href]")
                if "/tags/" in (a.attributes.get("href") or "")
            ]
        elif section.css_first(".rdWordCard"):
            entry.relations += _card_relations(section)

    return Parsed(entries=[entry])


def _parse_language_section(section: Node, lang: str, entry: Entry, seen_sher: set[str]):
    # Usage examples nest inside definition <li>s as <p><cite>label</cite>sentence</p>;
    # pulled out first so they land as examples instead of leaking into the definitions.
    for example in section.css(".rdSpeechListing p"):
        cite = example.css_first("cite")
        if cite is None:
            continue
        label = _clean(cite.text())
        if text := _clean(example.text()).removeprefix(label).strip(" ,•"):
            entry.examples.append((lang, text))
        example.decompose()

    for listing in section.css(".rdSpeechListing"):
        pos = None
        for node in listing.traverse():
            classes = node.attributes.get("class") or "" if node.tag != "-text" else ""
            if node.tag == "p" and "rdwordOrigin" in classes:
                span = node.css_first("span")
                pos = _clean(span.text()) if span else None
            elif node.tag == "li" and "toggleInputWrapper" not in classes:
                if definition := _clean(node.text(separator=", ")):
                    entry.senses.append(Sense(lang=lang, pos=pos, definition=definition))
    for item in section.css(".rdPosSherexmpl"):
        renderings = [_clean(pmc.text()) for pmc in item.css(".pMC") if _clean(pmc.text())]
        if not renderings or renderings[0] in seen_sher:
            continue
        seen_sher.add(renderings[0])
        poet = item.css_first("a")
        ghazal = item.css_first(".rdSeeGhazalPipe a")
        entry.shers.append(
            Sher(
                lines=renderings[0],
                lines_alt=renderings[1] if len(renderings) > 1 else None,
                poet=_clean(poet.text()) if poet else None,
                poet_url=_href(poet),
                ghazal_url=_href(ghazal),
            )
        )


def _trivia(section: Node, header: Node) -> str | None:
    text = " ".join(section.text().split())
    header_text = " ".join(header.text().split())
    return text.removeprefix(header_text).strip() or None


def _audio(tree: HTMLParser) -> str | None:
    source = tree.css_first("audio source[src]")
    if source is not None and (src := source.attributes.get("src") or "").startswith("http"):
        return src
    if marked := tree.css_first("[data-srcid]"):
        guid = marked.attributes.get("data-srcid") or ""
        if _GUID.match(guid):
            return f"{_AUDIO_CDN}/{guid}.mp3"
    return None


def _href(node: Node | None) -> str | None:
    href = (node.attributes.get("href") or "") if node is not None else ""
    return href if href.startswith(("http", "/")) else None


def _anchor_relations(section: Node, rel_type: str) -> list[Relation]:
    return [
        Relation(rel_type, text, _href(a))
        for a in section.css(".rdWrdRelatedtags a, .rdWrdRelatedtags ~ * a[href*='meaning-of-']")
        if (text := _clean(a.text()))
    ]


def _card_relations(section: Node) -> list[Relation]:
    relations = []
    for card in section.css(".rdWordCard"):
        title = card.css_first("h3")
        if title is None or not (text := _clean(title.text())):
            continue
        meaning = card.css_first(".rdWrdCrdMeaning")
        link = card.css_first("a[href]")
        relations.append(Relation("related", text, _href(link), _clean(meaning.text()) if meaning else None))
    return relations


def _parse_relation_page(site: str, url: str, html: str) -> Parsed:
    path = urlsplit(url).path.strip("/")
    marker = "-of-" if "-of-" in path else "-containing-"
    rel_type = next((rel for m, rel in _REL_BY_CATEGORY if m in path), "related")
    slug = _rel_slug(url, marker)
    tree = HTMLParser(html)
    relations = _anchor_relations(tree, rel_type) + _card_relations(tree)
    relations = [Relation(rel_type, r.target_text, r.target_url, r.target_meaning) for r in relations]
    return Parsed(relations_for={slug: relations}) if relations else Parsed()


def _parse_partial(site: str, url: str, html: str) -> Parsed:
    query = dict(parse_qsl(urlsplit(url).query))
    slug = query.get("id", "")
    category = query.get("wordCategory", "")
    rel_type = next((rel for marker, rel in _REL_BY_CATEGORY if marker in category), "related")
    tree = HTMLParser(html)
    relations = [
        Relation(rel_type, text, _href(a)) for a in tree.css("a[href]") if (text := _clean(a.text()))
    ]
    return Parsed(relations_for={slug: relations}) if slug and relations else Parsed()


def _parse_word_family(site: str, url: str, html: str) -> Parsed:
    root = urlsplit(url).path.strip("/").removeprefix("word-family/")
    tree = HTMLParser(html)
    relations_for: dict[str, list[Relation]] = {}
    for a in tree.css("a[href*='meaning-of-']"):
        if _clean(a.text()) and (href := _href(a)):
            relations_for[_slug(href)] = [Relation("word-family", root)]
    return Parsed(relations_for=relations_for)


def _parse_tag_page(site: str, url: str, html: str) -> Parsed:
    tag = urlsplit(url).path.strip("/").removeprefix("tags/")
    tree = HTMLParser(html)
    relations_for: dict[str, list[Relation]] = {}
    for a in tree.css("a[href*='meaning-of-']"):
        if _clean(a.text()) and (href := _href(a)):
            relations_for[_slug(href)] = [Relation("tag", tag, urlsplit(url).path)]
    return Parsed(relations_for=relations_for)
