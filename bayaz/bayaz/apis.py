"""The dictionary JSON APIs behind the Rekhta Foundation's mobile apps.

Unauthenticated, and both lighter and richer than the pages they replace: a
rekhtadictionary word is 3.7-21 KB of JSON against three 368 KB page fetches, and carries
all three languages plus six relation groups that are separate pages on the web. Full
reference in docs/hindwi-dictionary-api.md and docs/rekhta-dictionary-api.md.

An API call is modelled as a page: its url is the manifest key, its response lands in the
raw store, and it resumes and re-parses like everything else.
"""

import json
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

_HOST = "https://app-rekhta-dictionary.rekhta.org"


@dataclass(frozen=True, slots=True)
class DictApi:
    site: str
    kind: str
    endpoint: str
    params: tuple[tuple[str, str], ...]
    prefixes: tuple[str, ...]
    replaces: tuple[str, ...]
    langs: tuple[int, ...] = (1,)
    path_segment: str | None = None
    listing_endpoint: str | None = None
    listing_kind: str = ""

    def url(self, slug: str, lang: int) -> str:
        query = urlencode([("lang", str(lang)), ("wordId", slug), *self.params])
        return f"{_HOST}{self.endpoint}?{query}"

    def slug(self, page_url: str) -> str | None:
        """The wordId for a web page url. Both APIs reject the full web slug, and the
        `?lang=` variants collapse onto one word, which is most of the saving."""
        path = urlsplit(page_url).path.strip("/")
        if self.path_segment:
            if not path.startswith(self.path_segment):
                return None
            path = path.removeprefix(self.path_segment).strip("/")
        for prefix in self.prefixes:
            if path.startswith(prefix):
                return path.removeprefix(prefix) or None
        return None

    def lang_of(self, api_url: str) -> int:
        return int(_query(api_url).get("lang", self.langs[0]))

    def extra_langs(self, api_url: str, payload: dict) -> list[str]:
        """Only shers justify a second call: they render in the requested script only, and
        a Devanagari couplet is not derivable from its Roman rendering. Everything else
        already arrives in all three scripts."""
        if len(self.langs) < 2 or self.lang_of(api_url) != self.langs[0] or not _has_shers(payload):
            return []
        slug = _query(api_url).get("wordId")
        return [self.url(slug, lang) for lang in self.langs[1:]] if slug else []

    def audio_urls(self, payload: dict) -> list[str]:
        basic = (payload.get("R") or {}).get("BI") or {}
        return [url for name in ("AMF", "AOF") if (url := basic.get(name) or "").startswith("http")]

    def overflow_urls(self, api_url: str, payload: dict) -> list[str]:
        """A relation group returning exactly its PS is truncated; the rest come from
        WordListingByCategory, which reports no total, so it pages until empty."""
        if not self.listing_endpoint:
            return []
        slug = _query(api_url).get("wordId")
        if not slug:
            return []
        return [
            self.listing_url(slug, group["CT"], 1)
            for outer in (payload.get("R") or {}).get("RML") or []
            for group in outer.get("R") or []
            if group.get("CT") and group.get("PS") and len(group.get("R") or []) >= group["PS"]
        ]

    def listing_url(self, slug: str, category: str, page: int) -> str:
        query = urlencode(
            [
                ("wordId", slug),
                ("lang", str(self.langs[0])),
                ("category", category),
                ("pageIndex", str(page)),
                ("searchKeyword", ""),
                ("showNonClickableWord", "true"),
            ]
        )
        return f"{_HOST}{self.listing_endpoint}?{query}"

    def next_listing_url(self, api_url: str, payload: dict) -> list[str]:
        query = _query(api_url)
        if not (payload.get("R") or []):
            return []
        return [self.listing_url(query["wordId"], query["category"], int(query["pageIndex"]) + 1)]


def _query(url: str) -> dict[str, str]:
    return dict(pair.split("=", 1) for pair in urlsplit(url).query.split("&") if "=" in pair)


def _has_shers(payload: dict) -> bool:
    for block in (payload.get("R") or {}).get("RML") or []:
        for meaning in block.get("ML") or []:
            for group in meaning.get("R") or []:
                sher_list = group.get("SL")
                if sher_list and (sher_list.get("R") if isinstance(sher_list, dict) else sher_list):
                    return True
    return False


REKHTA_DICT = DictApi(
    site="rekhtadictionary",
    kind="word-api",
    endpoint="/rd-api/v1/GetWordDetailsByIdSlug",
    params=(
        ("deviceType", "0"),
        ("categoryType", ""),
        ("searchKeyword", ""),
        ("showNonClickableWord", "true"),
    ),
    prefixes=("urdu-meaning-of-", "meaning-of-"),
    replaces=("word", "compound", "synonym", "idiom", "antonym", "proverb"),
    langs=(1, 2, 3),
    listing_endpoint="/rd-api/v1/WordListingByCategory",
    listing_kind="wordlist-api",
)

HINDWI_DICT = DictApi(
    site="hindwi",
    kind="dict-api",
    endpoint="/api/v1/hindwi-dict/GetWordDetailsByIdSlug",
    params=(
        ("regionalLangSlug", "hindi"),
        ("categoryType", ""),
        ("searchKeyword", ""),
        ("showNonClickableWord", "false"),
        ("deviceType", "1"),
    ),
    prefixes=("meaning-of-",),
    replaces=("dict",),
    langs=(2,),
    path_segment="hindi-dictionary",
)

APIS = {api.site: api for api in (REKHTA_DICT, HINDWI_DICT)}


def api_for(site: str, kind: str) -> DictApi | None:
    api = APIS.get(site)
    return api if api is not None and kind in (api.kind, api.listing_kind) else None


def is_miss(payload: dict) -> bool:
    """Both APIs answer an unknown word with HTTP 200 and an empty skeleton; the envelope's
    S is 1 either way and R.S is false even on a hit, so the all-zero GUID is the tell."""
    basic = (payload.get("R") or {}).get("BI") or {}
    return basic.get("I") in (None, "00000000-0000-0000-0000-000000000000") or not basic.get("W1")


def parse_payload(text: str) -> dict:
    return json.loads(text)
