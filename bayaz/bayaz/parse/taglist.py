"""hindwi.org and sufinama.org tag pages: verse that exists nowhere else.

A tag page gathers works on a topic, and for the short forms it gathers them whole rather
than as links: every section carries `data-content-slug=""` and links only to its poet and
related topics, so no page of that couplet exists anywhere on the site. The tag page is the
only capture that will ever hold the text, which is why these pages are worth parsing at all
rather than treated as listing chrome.

Each section gives the lines with a per-word `data-m` code, the poet, the related topics and
often the site's own prose gloss. The codes are the same machine identifiers the Rekhta
poetry API resolves through `GetWordMeaningByLang`, so this content joins the dictionary
corpus at word level exactly as the poetry does.
"""

from urllib.parse import parse_qsl, urlsplit

from selectolax.parser import HTMLParser

from bayaz.corpus import Work
from bayaz.parse import Parsed, script_of

VERSION = 1

# The language enum the corpus already stores against word occurrences, set by rekhtaapi.
_LANG = {"en": 1, "hi": 2, "ur": 3}
_BODY_FIELD = {"en": "body", "hi": "body_hindi", "ur": "body_urdu"}


def _clean(text: str) -> str:
    return " ".join(text.split())


def parse(site: str, url: str, html: str) -> Parsed:
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/")
    # The form gathered here is the third segment of /tags/<topic>/<form>, but a paging
    # fragment is /CollectionLoading with no such path, so it carries the form in the query
    # instead. A bare /tags/<topic> gathers mixed forms and stays untyped.
    query = dict(parse_qsl(parts.query))
    work_type = query.get("contentType") or (segments[2] if len(segments) > 2 else "tag")

    tree = HTMLParser(html)
    works: list[Work] = []
    words: dict[str, list[tuple[int, int, int, str, str | None]]] = {}

    for section in tree.css(".sherSection"):
        # Sections that do have their own page are captured there, with more around them.
        if section.attributes.get("data-content-slug"):
            continue
        favourite = section.css_first("a.favorite[data-id]")
        if favourite is None:
            continue
        slug = favourite.attributes["data-id"]

        lines = [
            [
                (_clean(span.text()), span.attributes.get("data-m") or None)
                for span in line.css("span")
                if _clean(span.text())
            ]
            for line in section.css(".c p[data-l]")
        ]
        if not any(lines):
            continue

        body = "\n".join(" ".join(word for word, _ in line) for line in lines)
        script = script_of(body)
        work = Work(site=site, slug=slug, work_type=work_type)
        setattr(work, _BODY_FIELD[script], body)

        if poet := section.css_first(".poetName a"):
            work.author_name = _clean(poet.text()) or None
            work.author_url = poet.attributes.get("href")
        if gloss := section.css_first(".e"):
            work.explanation = _clean(gloss.text()) or None

        work.tags = [
            (name, tag.attributes.get("href"))
            for tag in section.css(".tagDetail a[href]")
            if (name := _clean(tag.text()))
        ]

        works.append(work)
        words[slug] = [
            (_LANG[script], line_ord, word_ord, word, code)
            for line_ord, line in enumerate(lines)
            for word_ord, (word, code) in enumerate(line)
        ]

    return Parsed(works=works, work_words=words)
