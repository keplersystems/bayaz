# bayaz

Personal archive of the Rekhta Foundation's literary web: **rekhtadictionary.com**,
**hindwi.org**, and **sufinama.org**. A bayāz (بیاض) is the notebook in which Urdu poets
and readers hand-copied the verses they wanted to keep.

Raw first, parse later: the crawl stores every page exactly as served, gzipped, beside a
SQLite manifest that knows what exists and what has been captured. Structure extraction
happens offline against the local store, so a parser bug never costs a re-crawl.

## Scale (measured 2026-08-03)

| Site | Pages | Notes |
|---|---|---|
| rekhtadictionary | ~933k | ~284k words × 3 script variants + relation pages; variants carry different content |
| hindwi | ~408k | 343k dictionary entries, 45.5k works, 19k entity pages |
| sufinama | ~404k | 296k dictionary entries, 61.7k works, 45.8k entity pages |

Roughly 1.75M pages, ~140 GB stored. Ebooks (scanned page images) are excluded for now.
Pronunciation audio urls are recorded in the manifest but not yet downloaded.

## Layout

A uv workspace, one member per surface:

| Member | What |
|---|---|
| `bayaz` | Core library — manifest, sitemap enumeration, paced crawl, raw store |
| `bayaz-cli` | The `bayaz` command |

`bayaz-mcp`, `bayaz-api` and `bayaz-web` join the workspace once there is a parsed corpus
to serve; they all sit on the parser, which is the next component.

## Usage

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/). Run from the repo root, or set
`DATA_DIR`/`RAW_DIR`.

```bash
uv sync

uv run bayaz enumerate            # read all sitemaps into the manifest
uv run bayaz crawl                # fetch everything pending; ctrl-c any time
uv run bayaz status               # progress per site and kind

uv run bayaz crawl --site hindwi --kind work --limit 100
uv run bayaz crawl --retry-failed
```

The crawl commits every page as it lands, so stopping and restarting loses nothing. A
later **delta** is the same two commands run again: `enumerate` only ever adds new URLs,
and `crawl` only fetches pending ones.

`--kind` filters skip the paging fragments discovered along the way (they are recorded as
kind `partial`); a run without `--kind` picks them up.

## How it works

All in the `bayaz` library:

- `sitemaps.py` — reads each site's sitemap index; idempotent. Also derives the
  path-segment → kind table that link discovery classifies against.
- `crawl.py` — the sites crawl in parallel, each behind its own pacing gate
  (request starts spaced `BAYAZ_REQUEST_DELAY` apart, `BAYAZ_CONCURRENCY` in flight).
- `discover.py` — captured pages enqueue what only they know about: `/PartialWordLoading`
  paging fragments (rekhtadictionary), pronunciation audio urls, and on hindwi/sufinama
  the content links their stale sitemaps miss.
- `rawstore.py` — one gzip per page under `raw/<site>/`, named by the url's sha1.
- `db.py` — the manifest: `pages`, `media`, `segments`.

At the default pace (~3 requests/s per site, sites in parallel) the full first crawl is
roughly 3–4 days. Times and sizes come from live measurement, not the sites' claims.

## Not yet built

- Audio download job (urls accumulate in `media` during the crawl).
- The structure parsers: dictionary entries (senses per language, examples, relations),
  works, entities — all offline against `raw/`.
- rekhta.org itself: different structure, planned after these three are captured.
