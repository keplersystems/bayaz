"""What a captured page adds to the manifest beyond itself.

Three shapes:

- Paging fragments (rekhtadictionary): listing sections load further entries through GET
  /PartialWordLoading fragments. A fragment carries no next-button, so each fragment that
  still contains links enqueues the next index, and the first empty one ends the chain.
- Gathered listings (platform sites): a tag page holds only the first 50 of its works, and
  for the short forms those works have no page of their own, so everything past the first
  page exists solely in /CollectionLoading fragments. Chained the same way, ending on the
  first fragment with no sections.
- Audio: pronunciation files, present either as <audio> sources or as data-srcid GUIDs the
  site's JS turns into CDN urls. Recorded into media for a later download job.
- Content links (platform sites): their sitemaps are months stale, so links whose first
  path segment the sitemaps have already established are recorded as discovered pages.
  Query-string urls are variants of a page already held, and paths under /ebooks are out
  of scope; both are skipped.
"""

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit

from selectolax.parser import HTMLParser

from bayaz import config, rawstore, rekhta
from bayaz.apis import api_for, is_miss, parse_payload
from bayaz.db import Database, PageRef
from bayaz.sites import SITES, Site

logger = logging.getLogger(__name__)

_GUID = re.compile(r"^[0-9a-fA-F-]{36}$")
_DICTIONARY_AUDIO = "https://rekhta.pc.cdn.bitgravity.com/Images/SiteImages/DictionaryAudio"


@dataclass(slots=True)
class Discovered:
    pages: list[PageRef] = field(default_factory=list)
    media: list[str] = field(default_factory=list)


def discover(site: Site, segments: dict[str, str], page: PageRef, body: str) -> Discovered:
    if site.name == rekhta.SITE:
        # The website kinds are HTML and a leaf: their word codes are the page's own base64
        # form rather than the API's, so nothing on them resolves to a further call.
        if page.kind in rekhta.WEB_KINDS:
            return Discovered()
        pages, media = rekhta.discover(page.url, parse_payload(body))
        return Discovered(
            pages=[PageRef(url=url, site=site.name, kind=kind, source="discovered") for url, kind in pages],
            media=media,
        )

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

    if page.kind.endswith("-page"):
        # Same idea for gathered listings, but keyed on sections rather than links, since a
        # /CollectionLoading fragment always carries navigation chrome even when it is spent.
        if tree.css_first(".sherSection"):
            found.pages.append(_ref(site, _next_fragment(page.url), page.kind))
        return found

    if page.kind in site.gathered:
        found.pages.extend(
            _ref(site, urljoin(page.url, data_url), f"{page.kind}-page")
            for node in tree.css("[data-url]")
            if "CollectionLoading" in (data_url := node.attributes.get("data-url") or "")
        )

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


async def replay(site_names: list[str] | None, kind: str | None, limit: int | None):
    """Re-run discovery over captures already fetched.

    Crawl-time discovery sees a page once. When a rule changes, and a kind that looked like
    a leaf turns out to reference something, the pages that would have enqueued it are
    already marked fetched and are never revisited: only pages captured after the change
    would ever act on it. Replaying from the raw store fixes that without touching the
    network, and is the discovery counterpart of a re-parse, for the same reason. Raw is the
    source of truth, so whatever is derived from it can be re-derived.

    Idempotent: `add_pages` keys on url, so a url already in the manifest keeps its status
    and a replay adds only what is genuinely new.
    """
    sites = [SITES[name] for name in (site_names or SITES)]

    async with Database(config.DATABASE_PATH) as db:
        for site in sites:
            segments = await db.segments(site.name)
            kinds = [kind] if kind else await db.fetched_kinds(site.name)
            for current in kinds:
                urls = await db.fetched_urls(site.name, current)
                if limit is not None:
                    urls = urls[:limit]
                if not urls:
                    continue
                added = failed = 0
                for url in urls:
                    page = PageRef(url=url, site=site.name, kind=current)
                    try:
                        found = discover(site, segments, page, rawstore.read(site.name, url, current))
                    except Exception:
                        failed += 1
                        logger.exception(f"{url}: replay failed")
                        continue
                    added += await db.add_pages(found.pages)
                    await db.add_media(site.name, found.media, url)
                logger.info(f"{site.name}/{current}: replayed {len(urls):,} capture(s), {added:,} new page(s)")
                if failed:
                    logger.warning(f"{site.name}/{current}: {failed} capture(s) could not be replayed")
