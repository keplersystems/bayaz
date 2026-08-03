"""What a captured page adds to the manifest beyond itself.

Three shapes:

- Paging fragments (rekhtadictionary): listing sections load further entries through GET
  /PartialWordLoading fragments. A fragment carries no next-button, so each fragment that
  still contains links enqueues the next index, and the first empty one ends the chain.
- Audio: pronunciation files, present either as <audio> sources or as data-srcid GUIDs the
  site's JS turns into CDN urls. Recorded into media for a later download job.
- Content links (platform sites): their sitemaps are months stale, so links whose first
  path segment the sitemaps have already established are recorded as discovered pages.
  Query-string urls are variants of a page already held, and paths under /ebooks are out
  of scope; both are skipped.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit

from selectolax.parser import HTMLParser

from bayaz.apis import api_for, is_miss, parse_payload
from bayaz.db import PageRef
from bayaz.sites import Site

_GUID = re.compile(r"^[0-9a-fA-F-]{36}$")
_DICTIONARY_AUDIO = "https://rekhta.pc.cdn.bitgravity.com/Images/SiteImages/DictionaryAudio"


@dataclass(slots=True)
class Discovered:
    pages: list[PageRef] = field(default_factory=list)
    media: list[str] = field(default_factory=list)


def discover(site: Site, segments: dict[str, str], page: PageRef, body: str) -> Discovered:
    if (api := api_for(site.name, page.kind)) is not None:
        return _discover_api(api, page, body)

    html = body
    tree = HTMLParser(html)
    found = Discovered(media=_audio(tree))

    if page.kind == "partial":
        # The fragment is its own pager: links mean there may be another page after it.
        if tree.css_first("a[href]"):
            found.pages.append(_ref(site, _next_fragment(page.url), "partial"))
        return found

    if page.kind in site.paginated:
        found.pages.extend(
            _ref(site, urljoin(page.url, data_url), "partial")
            for node in tree.css("[data-url]")
            if "PartialWordLoading" in (data_url := node.attributes.get("data-url") or "")
        )

    if site.discover_links:
        found.pages.extend(_content_links(site, segments, page, tree))
    return found


def _discover_api(api, page: PageRef, body: str) -> Discovered:
    payload = parse_payload(body)

    if page.kind == api.listing_kind:
        return Discovered(
            pages=[
                PageRef(url=url, site=page.site, kind=page.kind, source="discovered")
                for url in api.next_listing_url(page.url, payload)
            ]
        )

    if is_miss(payload):
        return Discovered()

    pages = [
        PageRef(url=url, site=page.site, kind=page.kind, source="discovered")
        for url in api.extra_langs(page.url, payload)
    ]
    pages += [
        PageRef(url=url, site=page.site, kind=api.listing_kind, source="discovered")
        for url in api.overflow_urls(page.url, payload)
    ]
    return Discovered(pages=pages, media=api.audio_urls(payload))


def _ref(site: Site, url: str, kind: str) -> PageRef:
    return PageRef(url=url, site=site.name, kind=kind, source="discovered")


def _next_fragment(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["pageIndex"] = str(int(query.get("pageIndex", "2")) + 1)
    return parts._replace(query=urlencode(query)).geturl()


def _audio(tree: HTMLParser) -> list[str]:
    urls = [
        src
        for node in tree.css("audio source[src]")
        if (src := node.attributes.get("src") or "").startswith("http")
    ]
    urls += [
        f"{_DICTIONARY_AUDIO}/{guid}.mp3"
        for node in tree.css("[data-srcid]")
        if _GUID.match(guid := node.attributes.get("data-srcid") or "")
    ]
    return urls


def _content_links(site: Site, segments: dict[str, str], page: PageRef, tree: HTMLParser) -> list[PageRef]:
    refs: dict[str, PageRef] = {}
    for node in tree.css("a[href]"):
        url = urljoin(page.url, node.attributes.get("href") or "").partition("#")[0]
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or parts.netloc not in site.hosts or parts.query:
            continue
        path_segments = parts.path.strip("/").split("/")
        if "ebooks" in path_segments:
            continue
        if len(path_segments) < 2:
            # A bare section index, not a content page; the sitemapped pages link plenty.
            continue
        if kind := segments.get(path_segments[0]):
            refs[url] = _ref(site, url, kind)
    return list(refs.values())
