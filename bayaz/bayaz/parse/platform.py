"""hindwi.org and sufinama.org: dictionary entries, works, entities.

The two sites share the Rekhta platform templates, so one module parses both. Dictionary
entries carry labeled attribute rows (part of speech, etymology, ...) and per-language
definition lists; works carry a two-script title, verse body, source and tags; entity
pages a name and profile description. Chrome (search boxes, promos, "you may also read")
is skipped.
"""

import re
from urllib.parse import parse_qsl, urlsplit

from selectolax.parser import HTMLParser

from bayaz.corpus import Entity, Entry, Sense, Work
from bayaz.parse import Parsed

VERSION = 1

_POS_LABELS = ("शब्दभेद", "شعبد")

_LANG_BY_ARTH = (("english", "en"), ("urdu", "ur"), ("hindi", "hi"))


def _clean(text: str) -> str:
    return " ".join(text.split()).strip(" ,•:")


def parse(site: str, url: str, html: str) -> Parsed:
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/")
    tree = HTMLParser(html)
    if "dictionary" in segments[0]:
        # Two dictionary templates share the platform: hindwi's per-word pages, and
        # sufinama's keyword pages listing several tri-script matches at once.
        if tree.css_first(".rekhtaDicSrchWord"):
            return _parse_match_dict(site, tree)
        return _parse_dict(site, segments[-1], tree)
    if segments[0] in ("poets", "authors", "translators", "editors", "publishers", "artists", "contributors"):
        lang = dict(parse_qsl(parts.query)).get("lang")
        return _parse_entity(site, segments, lang, tree)
    return _parse_work(site, segments, tree)


def _parse_dict(site: str, slug: str, tree: HTMLParser) -> Parsed:
    entry = Entry(site=site, slug=slug.removeprefix("meaning-of-"))
    if name := tree.css_first(".word-name"):
        entry.headword = _clean(name.text())

    pos = None
    attributes = []
    for row in tree.css(".word-meaning li"):
        label = _clean(row.text(deep=False))
        value_node = row.css_first("span")
        value = _clean(value_node.text()) if value_node else ""
        if not value:
            continue
        if any(pos_label in label for pos_label in _POS_LABELS):
            pos = value
        else:
            attributes.append(f"{label} : {value}")
    entry.trivia = "\n".join(attributes) or None

    for block in tree.css("[class*=arth-line]"):
        classes = block.attributes.get("class") or ""
        lang = next((code for marker, code in _LANG_BY_ARTH if marker in classes), "hi")
        for item in block.css("li"):
            if definition := _clean(item.text()):
                entry.senses.append(Sense(lang=lang, pos=pos, definition=definition))

    source = tree.css_first("audio source[src]")
    if source is not None and (src := source.attributes.get("src") or "").startswith("http"):
        entry.audio_url = src

    return Parsed(entries=[entry])


def _parse_match_dict(site: str, tree: HTMLParser) -> Parsed:
    entries = []
    for block in tree.css(".rekhtaDicSrchWord"):
        word = block.css_first(".dicSrchWord")
        if word is None or not (roman := _clean(word.text())):
            continue
        entry = Entry(site=site, slug=roman.strip("'‘’"), headword=roman)
        if meaning := block.css_first(".dicSrchMnng"):
            entry.headword_hindi = _clean(meaning.text(deep=False)) or None
            if urdu := meaning.css_first(".dicSrchMnngUrdu"):
                entry.headword_urdu = _clean(urdu.text()) or None
        for syno in block.css(".dicSrchWrdSyno"):
            if definition := _clean(syno.text()):
                entry.senses.append(Sense(lang="en", pos=None, definition=definition))
        source = block.css_first("source[src]")
        if source is not None and (src := source.attributes.get("src") or "").startswith("http"):
            entry.audio_url = src
        if video := block.css_first("[data-videosrc]"):
            entry.video_url = video.attributes.get("data-videosrc")
        entries.append(entry)
    return Parsed(entries=entries)


def _parse_work(site: str, segments: list[str], tree: HTMLParser) -> Parsed:
    work = Work(site=site, slug="/".join(segments), work_type=segments[0])

    headings = [h for h in tree.css("h1") if _clean(h.text())]
    if headings:
        work.title = _clean(headings[0].text())
    if len(headings) > 1:
        work.title_translit = _clean(headings[1].text())

    if body := tree.css_first(".poemPageContentBody"):
        work.body = _verse_text(body)

    # The author block sits above the body; site-wide nav also links poets, so the search
    # is scoped to the content header rather than the whole page.
    for scope_selector in (".poemPageContentHeader", ".NewPoem", "body"):
        scope = tree.css_first(scope_selector)
        if scope is None:
            continue
        author = scope.css_first("a[href*='/poets/'], a[href*='/authors/']")
        if author is not None and (name := _clean(author.text())):
            work.author_name = name
            work.author_url = author.attributes.get("href")
            break

    if source_tag := tree.css_first(".hindWi_Sourcetag"):
        holder = source_tag.parent
        if holder is not None and (text := _clean(holder.text())):
            work.source = text.removeprefix("स्रोत").strip(" :") or None

    for tag_section in tree.css("[class*=poemTagSection] a[href], [class*=TagSection] a[href]"):
        if tag := _clean(tag_section.text()):
            work.tags.append((tag, tag_section.attributes.get("href")))

    return Parsed(works=[work])


def _verse_text(body) -> str | None:
    """Verse lines live in block elements whose words are span-wrapped, so a flat text()
    with separators shreds one word per line. Lines are rebuilt per block instead."""
    blocks = body.css("p, .c, li") or [body]
    lines = []
    for block in blocks:
        if block.css_first("p, .c, li"):
            continue  # a container of line blocks, not a line itself
        lines.append(" ".join(block.text().split()))
    text = "\n".join(lines).strip()
    if not text:
        text = " ".join(body.text().split())
    return re.sub(r"\n{3,}", "\n\n", text) or None


def _parse_entity(site: str, segments: list[str], lang: str | None, tree: HTMLParser) -> Parsed:
    entity = Entity(site=site, slug=segments[1], entity_type=segments[0])
    entity.name_translit = segments[1].replace("-", " ")
    if heading := tree.css_first("h2"):
        # ?lang= facets render the same page in another script; each fills its own column
        name = _clean(heading.text())
        match lang:
            case "hi":
                entity.name_hindi = name
            case "ur":
                entity.name_urdu = name
            case _:
                entity.name = name
    for selector in (".poetProfileForMobile", "[class*=poetProfileshortDesc]", "[class*=profileDesc]"):
        if (profile := tree.css_first(selector)) and (description := _clean(profile.text())):
            entity.description = description
            break
    _birth_death(tree, entity)
    return Parsed(entities=[entity])


def _birth_death(tree: HTMLParser, entity: Entity):
    for node in tree.css("[class*=poetDetail], [class*=birthPlace], [class*=DOB]"):
        text = _clean(node.text())
        if not text:
            continue
        if match := re.search(r"(\d{4})\s*[-–]\s*(\d{4})", text):
            entity.born, entity.died = match.group(1), match.group(2)
            return
