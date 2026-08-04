"""rekhta.org, through the poetry API its mobile client uses.

Unlike the other three sites there is no sitemap to enumerate from, so the corpus is
discovered from the API itself: the content-type list and the poet list are seeded, every
listing page enqueues the next page and the contents it names, every content record
enqueues the word codes it contains, and every word code resolves to a dictionary entry.
That makes the crawl a closure rather than a walk, which is why discovery carries more
weight here than on the sitemap sites.

Every content type enumerates corpus-wide, fragments included, which is what keeps the
listing phase to roughly 2,900 calls for 146,807 works.

Full reference, including how the endpoints were obtained and what remains unverified, is
in docs/rekhta-poetry-api.md. Two things from it are load-bearing and easy to lose:

- POST handlers require a JSON body of `{"a": "a"}`. Without it the server holds the
  connection for about 36 seconds and closes it, which is indistinguishable from a missing
  parameter, so a body bug looks exactly like a parameter bug.
- On the word endpoints, `word` carries the machine code and `selectedWord` the readable
  text, which is the reverse of how the names read.

Audio, video and books are deliberately out of scope, so their listing endpoints are never
called. Media urls that arrive inline on a content record are left in the stored response
rather than being downloaded.
"""

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit

from bayaz.request import REKHTA_GET, REKHTA_POST, Request

SITE = "rekhta"
BASE = "https://app-rekhta.rekhta.org/rekhta-api/v1"

# Page size is fixed server-side; TC carries a genuine total, so paging is arithmetic
# rather than a walk until empty.
PAGE_SIZE = 50

# Enums from the client: sortBy 0 = popularity, lang 1 = English, 2 = Hindi, 3 = Urdu.
SORT_POPULARITY = "0"
LANGS = (1, 2, 3)

# kind -> the handler it calls. Every kind is one endpoint, which keeps the manifest's
# `kind` column meaningful as both a queue selector and a parse selector.
ENDPOINTS = {
    "content-types": "GetContentTypeList",
    "poets": "GetPoetsListWithPaging",
    "tags": "GetTagsList",
    "content-list": "GetContentListWithPaging",
    "couplet-list": "GetCoupletListWithPaging",
    "content": "GetContentById",
    "poet": "GetPoetCompleteProfile",
    "word": "GetWordMeaningByLang",
    "word-group": "GetGroupWordMeaningByLang",
}

# The only GET among them, per the verb rule in the docs.
_GET_KINDS = frozenset({"content"})

# Kinds that enumerate the corpus rather than being part of it. They are re-fetched on
# every `enumerate`, because on a site with no sitemap the listings *are* the sitemap: left
# marked fetched they would be skipped, and a delta run would report nothing to do while
# newly published work sat undiscovered behind them.
ENUMERATION_KINDS = ("content-types", "poets", "content-list", "couplet-list", "tags")


def request_for_kind(kind: str) -> Request:
    return REKHTA_GET if kind in _GET_KINDS else REKHTA_POST


def _url(endpoint: str, params: dict[str, str]) -> str:
    return f"{BASE}/{endpoint}?{urlencode(sorted(params.items()))}"


def query(url: str) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))


def kind_of(url: str) -> str | None:
    endpoint = urlsplit(url).path.rsplit("/", 1)[-1]
    return next((kind for kind, name in ENDPOINTS.items() if name == endpoint), None)


def content_types_url() -> str:
    return _url(ENDPOINTS["content-types"], {"lastFetchDate": ""})


def tags_url(lang: int = 1) -> str:
    return _url(ENDPOINTS["tags"], {"lang": str(lang)})


def poets_url(page: int) -> str:
    return _url(ENDPOINTS["poets"], {"lastFetchDate": "", "targetId": "", "keyword": "", "pageIndex": str(page)})


def poet_url(poet_id: str, lang: int = 1) -> str:
    return _url(ENDPOINTS["poet"], {"poetId": poet_id, "lang": str(lang)})


def listing_url(content_type_id: str, page: int, *, fragments: bool, poet_id: str = "") -> str:
    """A listing page. `fragments` selects the couplet endpoint, which serves the three
    LT=2 types. Both endpoints enumerate corpus-wide with `poetId` empty, and the couplet
    one additionally keeps the poet id that the content one drops in that mode."""
    return _url(
        ENDPOINTS["couplet-list" if fragments else "content-list"],
        {
            "targetId": "",
            "keyword": "",
            "poetId": poet_id,
            "contentTypeId": content_type_id,
            "sortBy": SORT_POPULARITY,
            "pageIndex": str(page),
        },
    )


def content_url(content_id: str, lang: int) -> str:
    return _url(ENDPOINTS["content"], {"contentId": content_id, "lang": str(lang)})


def word_url(code: str, selected: str, lang: int, *, group: bool = False) -> str:
    # `word` takes the machine code and `selectedWord` the readable text, which is the
    # reverse of how the parameter names read.
    return _url(ENDPOINTS["word-group" if group else "word"], {"lang": str(lang), "word": code, "selectedWord": selected})


@dataclass(frozen=True, slots=True)
class ContentType:
    id: str
    slug: str
    name: str
    fragments: bool  # LT == 2
    prose: bool  # CT == 2

    @classmethod
    def from_row(cls, row: dict) -> "ContentType":
        return cls(
            id=row["I"],
            slug=row.get("SS") or row["I"],
            name=row.get("NE") or "",
            fragments=row.get("LT") == 2,
            prose=row.get("CT") == 2,
        )


def pages_for(total: int) -> int:
    return (total + PAGE_SIZE - 1) // PAGE_SIZE


def seed_urls() -> list[tuple[str, str]]:
    """The roots the corpus unfolds from. Everything else is discovered."""
    return [
        (content_types_url(), "content-types"),
        (poets_url(1), "poets"),
        (tags_url(), "tags"),
    ]


def envelope(payload: dict) -> dict | list | None:
    """Every handler wraps its result in the same status envelope; `S` is 1 on success and
    an empty result is still a success, so the payload decides, not the flag."""
    return payload.get("R")


def _content_ids(rows: list[dict]) -> list[str]:
    return [row["I"] for row in rows if row.get("I")]


def word_codes(node, found: list[tuple[str, str]]) -> None:
    """Collect (code, readable) for every word in a text tree.

    The tree arrives as nested stanza/line/word objects under different keys depending on
    the endpoint, so this walks structurally rather than by key name: any object carrying
    an `M` code and a `W` word is a word node, and anything else is recursed into."""
    if isinstance(node, dict):
        code, word = node.get("M"), node.get("W")
        if isinstance(code, str) and code and isinstance(word, str) and word:
            found.append((code, word))
        for value in node.values():
            word_codes(value, found)
    elif isinstance(node, list):
        for value in node:
            word_codes(value, found)


def discover(url: str, payload: dict) -> tuple[list[tuple[str, str]], list[str]]:
    """What a captured response adds to the queue, as (url, kind) pairs, plus media urls.

    Media is recorded rather than fetched: audio, video and books are out of scope, but the
    urls cost nothing to keep and re-deriving them later would mean re-parsing the corpus.
    """
    kind = kind_of(url)
    result = envelope(payload)
    if result is None:
        return [], []

    params = query(url)
    pages: list[tuple[str, str]] = []
    media: list[str] = []

    match kind:
        case "content-types":
            for row in result if isinstance(result, list) else []:
                content_type = ContentType.from_row(row)
                kind = "couplet-list" if content_type.fragments else "content-list"
                pages.append((listing_url(content_type.id, 1, fragments=content_type.fragments), kind))

        case "poets":
            rows = result.get("P") or []
            page = int(params.get("pageIndex", "1"))
            if page == 1:
                pages += [(poets_url(n), "poets") for n in range(2, pages_for(result.get("TC") or 0) + 1)]
            pages += [(poet_url(row["I"]), "poet") for row in rows if row.get("I")]

        case "content-list" | "couplet-list":
            rows = result.get("CS") if kind == "content-list" else result.get("CD")
            rows = rows or []
            page = int(params.get("pageIndex", "1"))
            if page == 1:
                total_pages = pages_for(result.get("TC") or 0)
                fragments = kind == "couplet-list"
                pages += [
                    (
                        listing_url(
                            params["contentTypeId"], n, fragments=fragments, poet_id=params.get("poetId", "")
                        ),
                        kind,
                    )
                    for n in range(2, total_pages + 1)
                ]
            # Every language of every content record: the tree is rendered in the requested
            # script and the three are not derivable from one another.
            for content_id in _content_ids(rows):
                pages += [(content_url(content_id, lang), "content") for lang in LANGS]

        case "content":
            found: list[tuple[str, str]] = []
            word_codes(result.get("CR"), found)
            lang = int(params.get("lang", "1"))
            seen = set()
            for code, readable in found:
                if code in seen:
                    continue
                seen.add(code)
                pages.append((word_url(code, readable, lang), "word"))
            media += _media_urls(result)

        case "word" | "word-group":
            media += _media_urls(result)

    return pages, media


_MEDIA_KEYS = ("AMF", "AOF", "AU", "MU", "VU")


def _media_urls(node) -> list[str]:
    urls: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _MEDIA_KEYS and isinstance(value, str) and value.startswith("http"):
                urls.append(value)
            else:
                urls += _media_urls(value)
    elif isinstance(node, list):
        for value in node:
            urls += _media_urls(value)
    return urls
