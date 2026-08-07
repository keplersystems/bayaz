import argparse
import asyncio
import logging
import sys

from bayaz.crawl import crawl
from bayaz.db import Database
from bayaz.sitemaps import enumerate_site
from bayaz.sites import SITES

from bayaz import config

logger = logging.getLogger(__name__)


def _sites(names: list[str] | None):
    return [SITES[name] for name in (names or SITES)]


async def _enumerate(names: list[str] | None):
    async with Database(config.DATABASE_PATH) as db:
        for site in _sites(names):
            await enumerate_site(db, site)


async def _status():
    async with Database(config.DATABASE_PATH) as db:
        rows = await db.counts()
        media = await db.media_count()

    if not rows:
        print("Manifest is empty; run `bayaz enumerate` first.")
        return
    header = f"{'site':<18} {'kind':<12} {'total':>9} {'fetched':>9} {'failed':>7} {'pending':>9} {'raw MB':>8}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['site']:<18} {row['kind']:<12} {row['total']:>9,} {row['fetched']:>9,}"
            f" {row['failed']:>7,} {row['pending']:>9,} {row['bytes'] / 1e6:>8,.0f}"
        )
    total = sum(r["total"] for r in rows)
    fetched = sum(r["fetched"] for r in rows)
    size = sum(r["bytes"] for r in rows)
    print("-" * len(header))
    print(f"{'all':<18} {'':<12} {total:>9,} {fetched:>9,} {'':>7} {total - fetched:>9,} {size / 1e6:>8,.0f}")
    print(f"\n{media:,} media urls recorded (not downloaded)")


def main():
    parser = argparse.ArgumentParser(prog="bayaz", description="Archive of the Rekhta Foundation's literary web")
    commands = parser.add_subparsers(dest="command", required=True)

    enum = commands.add_parser(
        "enumerate", help="Read every site's sitemaps into the manifest; idempotent, re-run later for the delta"
    )
    enum.add_argument("--site", choices=SITES, action="append", help="Only this site; repeatable")

    crawl_cmd = commands.add_parser("crawl", help="Fetch pending pages into the raw store; resumable at any point")
    crawl_cmd.add_argument("--site", choices=SITES, action="append", help="Only this site; repeatable")
    crawl_cmd.add_argument("--kind", help="Only pages of this kind (see `status` for kinds)")
    crawl_cmd.add_argument("--limit", type=int, help="Stop after this many pages per site")
    crawl_cmd.add_argument("--retry-failed", action="store_true", help="Also retry pages that previously failed")

    parse_cmd = commands.add_parser("parse", help="Extract structured data from captured pages into the corpus")
    parse_cmd.add_argument("--site", choices=SITES, action="append", help="Only this site; repeatable")
    parse_cmd.add_argument("--kind", help="Only pages of this kind")
    parse_cmd.add_argument("--limit", type=int, help="Stop after this many pages per site and kind")

    replay_cmd = commands.add_parser(
        "rediscover", help="Re-run discovery over captures already fetched; adds urls a newer rule finds"
    )
    replay_cmd.add_argument("--site", choices=SITES, action="append", help="Only this site; repeatable")
    replay_cmd.add_argument("--kind", help="Only captures of this kind")
    replay_cmd.add_argument("--limit", type=int, help="Stop after this many captures per site and kind")

    commands.add_parser("status", help="Where the archive stands, per site and kind")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs one INFO line per request; at millions of requests that is the whole log
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        match args.command:
            case "enumerate":
                asyncio.run(_enumerate(args.site))
            case "crawl":
                asyncio.run(crawl(_sites(args.site), args.kind, args.limit, args.retry_failed))
            case "parse":
                from bayaz import parse

                asyncio.run(parse.run(args.site, args.kind, args.limit))
            case "rediscover":
                from bayaz import discover

                asyncio.run(discover.replay(args.site, args.kind, args.limit))
            case "status":
                asyncio.run(_status())
    except KeyboardInterrupt:
        logger.info("Interrupted; everything committed so far is kept. Re-run to resume.")
        sys.exit(130)
