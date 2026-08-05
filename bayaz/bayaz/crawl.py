"""The crawl: fetch pending pages, store them raw, record what they reference.

Raw first, parse later: a capture is the page exactly as served, gzipped, so a parser
mistake costs a re-parse of local files, never a re-crawl. Crawl-time discovery is limited
to what the manifest cannot be rebuilt from later — paging fragments, audio urls, and on
the platform sites the content links their stale sitemaps miss.

Sites crawl in parallel, paced per origin rather than per site: each origin's gate spaces
request starts its own delay apart while a fixed number may be in flight, so slow responses
overlap without the request rate ever rising. Two sites answering from one machine share
that budget, which is what keeps the dictionary APIs off double rate. Every page's outcome is committed as it happens;
stopping the process at any point loses nothing but the requests in flight.
"""

import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from bayaz import config, rawstore
from bayaz.db import Database, PageRef
from bayaz.discover import discover
from bayaz.request import Request, request_for
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


# Hosts that are one machine. Rekhta's three app backends all answer from 14.140.111.5,
# an origin IIS box with no CDN in front of it, so pacing them by hostname would hand one
# server three budgets. The websites are separate addresses and keep their own.
@dataclass(frozen=True)
class Origin:
    key: str
    delay: float
    concurrency: int


_REKHTA_APP = Origin("rekhta-app", config.APP_REQUEST_DELAY, config.APP_CONCURRENCY)
_ORIGIN_GROUPS = {
    "app-rekhta.rekhta.org": _REKHTA_APP,
    "app-rekhta-dictionary.rekhta.org": _REKHTA_APP,
    "world.rekhta.org": _REKHTA_APP,
}


class Gate:
    """One origin's budget: request starts spaced `delay` apart, `concurrency` in flight."""

    def __init__(self, origin: Origin):
        self.delay = origin.delay
        self.lock = asyncio.Lock()
        self.slots = asyncio.Semaphore(origin.concurrency)


class Pacer:
    """One budget per origin, shared across sites."""

    def __init__(self):
        self._gates: dict[str, Gate] = {}

    def for_url(self, url: str) -> Gate:
        host = urlsplit(url).netloc
        origin = _ORIGIN_GROUPS.get(host) or Origin(host, config.REQUEST_DELAY, config.CONCURRENCY)
        if origin.key not in self._gates:
            self._gates[origin.key] = Gate(origin)
        return self._gates[origin.key]


class SiteCrawler:
    def __init__(
        self, db: Database, site: Site, pacer: Pacer, *, kind: str | None, limit: int | None, retry_failed: bool
    ):
        self.db = db
        self.site = site
        self.pacer = pacer
        self.kind = kind
        self.limit = limit
        self.retry_failed = retry_failed
        self._segments: dict[str, str] = {}
        # The connection pool has to cover the in-flight ceiling. httpx keeps 20 alive by
        # default, so every request beyond that opens a fresh TLS connection: a handshake
        # their server pays for on every call, and latency we pay for on every call.
        slots = max(config.CONCURRENCY, config.APP_CONCURRENCY)
        self._client = httpx.AsyncClient(
            headers={"User-Agent": config.USER_AGENT},
            follow_redirects=True,
            timeout=config.TIMEOUT,
            limits=httpx.Limits(max_connections=slots + 10, max_keepalive_connections=slots),
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
        gate = self.pacer.for_url(page.url)
        async with gate.slots:
            try:
                response = await self._fetch(page.url, gate, request_for(self.site.name, page.kind))
            except FetchError as e:
                logger.warning(f"{self.site.name}: {e} (failure {page.attempts + 1})")
                await self.db.mark_failed(page.url, e.status, str(e))
                self.failed += 1
                return

        # Off the event loop: gzip and HTML parsing are the crawl's whole CPU cost, and on
        # the loop they stall every site's fetch handling, not just this one's.
        sha256, size = await asyncio.to_thread(rawstore.write, self.site.name, page.url, response.text, page.kind)
        found = await asyncio.to_thread(discover, self.site, self._segments, page, response.text)
        await self.db.add_pages(found.pages)
        await self.db.add_media(self.site.name, found.media, page.url)
        await self.db.mark_fetched(page.url, response.status_code, sha256, size)

        self.fetched += 1
        if self.fetched % _PROGRESS_EVERY == 0:
            logger.info(f"{self.site.name}: {self.fetched} fetched this run")

    async def _fetch(self, url: str, gate: Gate, spec: Request) -> httpx.Response:
        for attempt, backoff in enumerate(_BACKOFF, start=1):
            async with gate.lock:
                await asyncio.sleep(gate.delay)
            try:
                response = await self._client.request(
                    spec.method, url, headers=spec.headers(), json=spec.body
                )
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
        pacer = Pacer()
        crawlers = [
            SiteCrawler(db, site, pacer, kind=kind, limit=limit, retry_failed=retry_failed) for site in sites
        ]
        results = await asyncio.gather(*(crawler.run() for crawler in crawlers))
    fetched = sum(f for f, _ in results)
    failed = sum(f for _, f in results)
    logger.info(f"Crawl finished: {fetched} fetched, {failed} failed")
