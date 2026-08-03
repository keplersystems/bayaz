"""The crawl: fetch pending pages, store them raw, record what they reference.

Raw first, parse later: a capture is the page exactly as served, gzipped, so a parser
mistake costs a re-parse of local files, never a re-crawl. Crawl-time discovery is limited
to what the manifest cannot be rebuilt from later — paging fragments, audio urls, and on
the platform sites the content links their stale sitemaps miss.

Sites crawl in parallel, each behind its own pacing gate: the gate spaces request starts
REQUEST_DELAY apart while CONCURRENCY requests may be in flight, so slow responses overlap
without the request rate ever rising. Every page's outcome is committed as it happens;
stopping the process at any point loses nothing but the requests in flight.
"""

import asyncio
import logging

import httpx

from bayaz import config, rawstore
from bayaz.db import Database, PageRef
from bayaz.discover import discover
from bayaz.sites import Site

logger = logging.getLogger(__name__)

_TRANSIENT = frozenset({429, 500, 502, 503, 504})
_BACKOFF = (5, 15, 45)
_CHUNK = 500
_PROGRESS_EVERY = 100


class FetchError(RuntimeError):
    def __init__(self, url: str, status: int | None, detail: str):
        self.status = status
        super().__init__(f"{url}: {detail}")


class SiteCrawler:
    def __init__(self, db: Database, site: Site, *, kind: str | None, limit: int | None, retry_failed: bool):
        self.db = db
        self.site = site
        self.kind = kind
        self.limit = limit
        self.retry_failed = retry_failed
        self._segments: dict[str, str] = {}
        self._gate = asyncio.Lock()
        self._slots = asyncio.Semaphore(config.CONCURRENCY)
        self._client = httpx.AsyncClient(
            headers={"User-Agent": config.USER_AGENT}, follow_redirects=True, timeout=config.TIMEOUT
        )
        self.fetched = 0
        self.failed = 0

    async def run(self) -> tuple[int, int]:
        self._segments = await self.db.segments(self.site.name)
        try:
            while remaining := self._remaining():
                batch = await self.db.pending(
                    self.site.name, self.kind, min(remaining, _CHUNK), self.retry_failed, config.MAX_ATTEMPTS
                )
                if not batch:
                    break
                # retry-failed only seeds the first batch; after that the failures this
                # run produced would be selected again immediately, spinning on them.
                self.retry_failed = False
                await asyncio.gather(*(self._one(page) for page in batch))
        finally:
            await self._client.aclose()
        logger.info(f"{self.site.name}: done — {self.fetched} fetched, {self.failed} failed")
        return self.fetched, self.failed

    def _remaining(self) -> int:
        if self.limit is None:
            return _CHUNK
        return max(0, self.limit - self.fetched - self.failed)

    async def _one(self, page: PageRef):
        async with self._slots:
            try:
                response = await self._fetch(page.url)
            except FetchError as e:
                logger.warning(f"{self.site.name}: {e} (failure {page.attempts + 1})")
                await self.db.mark_failed(page.url, e.status, str(e))
                self.failed += 1
                return

        sha256, size = rawstore.write(self.site.name, page.url, response.text)
        found = discover(self.site, self._segments, page, response.text)
        await self.db.add_pages(found.pages)
        await self.db.add_media(self.site.name, found.media, page.url)
        await self.db.mark_fetched(page.url, response.status_code, sha256, size)

        self.fetched += 1
        if self.fetched % _PROGRESS_EVERY == 0:
            logger.info(f"{self.site.name}: {self.fetched} fetched this run")

    async def _fetch(self, url: str) -> httpx.Response:
        for attempt, backoff in enumerate(_BACKOFF, start=1):
            async with self._gate:
                await asyncio.sleep(config.REQUEST_DELAY)
            try:
                response = await self._client.get(url)
            except httpx.HTTPError as e:
                if attempt == len(_BACKOFF):
                    raise FetchError(url, None, str(e)) from e
                await asyncio.sleep(backoff)
                continue

            if response.status_code in _TRANSIENT:
                if attempt == len(_BACKOFF):
                    raise FetchError(url, response.status_code, f"HTTP {response.status_code} after {attempt} tries")
                wait = float(response.headers.get("Retry-After") or backoff)
                logger.warning(f"{self.site.name}: HTTP {response.status_code}, waiting {wait:.0f}s")
                await asyncio.sleep(wait)
                continue
            if response.status_code >= 400:
                raise FetchError(url, response.status_code, f"HTTP {response.status_code}")
            return response
        raise AssertionError("unreachable")


async def crawl(sites: list[Site], kind: str | None, limit: int | None, retry_failed: bool):
    async with Database(config.DATABASE_PATH) as db:
        crawlers = [SiteCrawler(db, site, kind=kind, limit=limit, retry_failed=retry_failed) for site in sites]
        results = await asyncio.gather(*(crawler.run() for crawler in crawlers))
    fetched = sum(f for f, _ in results)
    failed = sum(f for _, f in results)
    logger.info(f"Crawl finished: {fetched} fetched, {failed} failed")
