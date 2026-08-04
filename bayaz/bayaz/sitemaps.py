"""Enumerate: read each site's sitemap index into the manifest.

Idempotent by construction: every URL lands with INSERT OR IGNORE, so re-running after
months is the delta walk. Hindwi's sitemaps have not been regenerated since 2025-03, so
enumeration alone undercounts new content there; crawl-time link discovery covers the gap.

On the platform sites this also derives the first-path-segment -> kind table that link
discovery classifies against, so the whitelist maintains itself from what the sites
publish rather than from a hardcoded list of their content types.
"""

import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import httpx

from bayaz import config, rekhta
from bayaz.apis import APIS
from bayaz.db import Database, PageRef
from bayaz.sites import Site

logger = logging.getLogger(__name__)


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _kind(site: Site, sitemap_url: str) -> str | None:
    stem = sitemap_url.rsplit("/", 1)[-1].removesuffix(".xml")
    match = re.match(r"[A-Za-z]+", stem)
    name = match.group() if match else stem
    if name in site.kinds:
        return site.kinds[name]
    if name not in site.excluded:
        logger.warning(f"{site.name}: unrecognized sitemap {sitemap_url}, skipping")
    return None


def _entries(body: bytes) -> list[tuple[str, str | None]]:
    """(loc, lastmod) pairs from a urlset or sitemapindex, namespace-agnostic."""
    entries = []
    for element in ET.fromstring(body):
        if _tag(element) not in ("url", "sitemap"):
            continue
        loc = lastmod = None
        for child in element:
            match _tag(child):
                case "loc":
                    loc = (child.text or "").strip()
                case "lastmod":
                    lastmod = (child.text or "").strip()
        if loc:
            entries.append((loc, lastmod))
    return entries


def _segment(url: str) -> str | None:
    parts = urlsplit(url).path.strip("/").split("/")
    return parts[0] if parts[0] else None


async def enumerate_site(db: Database, site: Site) -> tuple[int, int]:
    """Returns (urls seen, urls new). Child sitemaps are fetched one at a time; this is a
    few dozen requests, not a crawl."""
    if not site.sitemap_index:
        return await seed_rekhta(db)

    async with httpx.AsyncClient(
        headers={"User-Agent": config.USER_AGENT}, follow_redirects=True, timeout=config.TIMEOUT
    ) as client:
        index = await client.get(site.sitemap_index)
        index.raise_for_status()

        seen = added = 0
        for child_url, _ in _entries(index.content):
            kind = _kind(site, child_url)
            if kind is None:
                continue
            response = await client.get(child_url)
            response.raise_for_status()
            pages = [
                PageRef(url=loc, site=site.name, kind=kind, lastmod=lastmod)
                for loc, lastmod in _entries(response.content)
            ]
            new = await db.add_pages(pages)
            if site.discover_links:
                await db.add_segments(
                    site.name, {(segment, kind) for page in pages if (segment := _segment(page.url))}
                )
            seen += len(pages)
            added += new
            logger.info(f"{site.name}: {child_url.rsplit('/', 1)[-1]} — {len(pages)} urls, {new} new")

    logger.info(f"{site.name}: {seen} urls enumerated, {added} new")
    await seed_api(db, site)
    return seen, added


async def seed_rekhta(db: Database) -> tuple[int, int]:
    """rekhta.org has no sitemap, so enumeration is its own listing walk: seed the roots and
    queue the listing kinds again so the walk re-runs and surfaces anything published since.
    """
    added = await db.add_pages(
        [PageRef(url=url, site=rekhta.SITE, kind=kind, source="seed") for url, kind in rekhta.seed_urls()]
    )
    requeued = await db.reset_to_pending(rekhta.SITE, rekhta.ENUMERATION_KINDS)
    logger.info(f"rekhta: {added} seed url(s), {requeued:,} listing page(s) queued for re-walk")
    return added, requeued


async def seed_api(db: Database, site: Site):
    """Turn the word pages an API serves into API rows, and stop crawling their HTML.

    Runs inside enumerate so it stays idempotent with it: the API url is derived from the
    page url, so re-running only ever adds words the sitemaps have newly listed. The three
    `?lang=` variants of one word collapse onto a single call, which is most of the saving.
    """
    api = APIS.get(site.name)
    if api is None:
        return

    slugs = {slug for url in await db.urls_of_kinds(site.name, api.replaces) if (slug := api.slug(url))}
    if not slugs:
        return
    # Only the first language is seeded. The rest are enqueued at crawl time, and only for
    # the few words whose response carries script-specific content.
    added = await db.add_pages(
        [PageRef(url=api.url(slug, api.langs[0]), site=site.name, kind=api.kind, source="api") for slug in slugs]
    )
    superseded = await db.supersede(site.name, api.replaces)
    logger.info(
        f"{site.name}: {len(slugs):,} words -> {api.kind} ({added:,} new); "
        f"{superseded:,} html page(s) superseded across {', '.join(api.replaces)}"
    )
