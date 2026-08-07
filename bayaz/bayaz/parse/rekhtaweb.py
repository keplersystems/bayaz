"""rekhta.org work pages: the text of the works the poetry API withholds.

`GetContentById` returns the prose types as an empty container, `<div class='pMC'
data-pc='49'></div>`, at every language: a 49-page story arrives as ~1.5 KB of metadata and
the text is not in the response at all. The website page carries the whole work, every page
inline, in one request, in the same per-word markup the platform tag pages use.

The `data-m` codes here are base64 where the API's are backslash-prefixed (`\\1nn2`), so
they are stored as the page gives them rather than resolved through `GetWordMeaningByLang`,
exactly as `taglist` does with the same markup on hindwi and sufinama.

Only the body is taken. Title, author, tags and source already came from the API record
under the same slug, and `upsert_work` coalesces, so a page that is missing something
cannot blank what the API supplied.
"""

from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from bayaz.corpus import Work
from bayaz.parse import Parsed, script_of

VERSION = 1

# The language enum the corpus stores against word occurrences, set by rekhtaapi.
_LANG = {"en": 1, "hi": 2, "ur": 3}
_BODY_FIELD = {"en": "body", "hi": "body_hindi", "ur": "body_urdu"}


def _clean(text: str) -> str:
    return " ".join(text.split())


def parse(site: str, url: str, html: str) -> Parsed:
    tree = HTMLParser(html)
    # Every page carries a second `.pMC`, a couplet-of-the-day canvas in the chrome, and on
    # a drama both it and the work report `data-pc='1'`, so the page count cannot tell them
    # apart. The content wrapper can.
    container = tree.css_first(".poemPageContentBody .pMC")
    if container is None:
        return Parsed()

    # The content GUID, so the body lands on the row the API record already created rather
    # than on a second work keyed by the page's own slug.
    favourite = tree.css_first("a.favorite[data-id]")
    if favourite is None:
        return Parsed()
    slug = favourite.attributes["data-id"]

    # The body is the paragraph text, never the spans: the annotated types wrap every word
    # in a `data-m` span, but the interviews do not span their text at all, and reading the
    # words would silently return nothing for them. `data-l` is no help either, since it
    # numbers within a page and repeats across the work.
    paragraphs = [para for para in container.css(".c p") if _clean(para.text())]
    if not paragraphs:
        return Parsed()

    body = "\n".join(_clean(para.text()) for para in paragraphs)
    script = script_of(body)

    # /<content-type>/<slug>, the same slug the API reports as `TS`. work_type is the one
    # column upsert_work overwrites rather than coalesces, so it has to be right.
    work = Work(site=site, slug=slug, work_type=urlsplit(url).path.strip("/").split("/")[0])
    setattr(work, _BODY_FIELD[script], body)

    # Word codes are an annotation layer over that text, present on the verse and prose
    # templates and absent on the interviews, so their absence is not a parse failure.
    words: list[tuple[int, int, int, str, str | None]] = []
    for line_ord, para in enumerate(paragraphs):
        annotated = [
            (text, span.attributes["data-m"])
            for span in para.css("span[data-m]")
            if (text := _clean(span.text()))
        ]
        words += [
            (_LANG[script], line_ord, word_ord, text, code)
            for word_ord, (text, code) in enumerate(annotated)
        ]
    return Parsed(works=[work], work_words={slug: words})
