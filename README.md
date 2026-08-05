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

`docs/` holds reference for the upstream JSON APIs the sites' mobile apps use, where one
exists. Fetching a dictionary entry as JSON is far lighter on Rekhta than fetching the
rendered page, so these replace most of the HTML crawl:

| Doc | Covers |
|---|---|
| [rekhta-dictionary-api.md](docs/rekhta-dictionary-api.md) | replaces 927k of rekhtadictionary's 933k pages |
| [hindwi-dictionary-api.md](docs/hindwi-dictionary-api.md) | replaces 343k of hindwi's 414k pages |
| [rekhta-poetry-api.md](docs/rekhta-poetry-api.md) | rekhta.org poets, poems, couplets, audio. Deferred scope, recorded because the endpoint names are perishable |

Both are unauthenticated read APIs. Together they cover 1,270,756 of the manifest's
1,750,436 pages (73%), leaving 479,680 on the HTML crawl, of which sufinama's dictionary is
294,465. Enumeration still comes from the sitemaps; the APIs replace the fetch, not the
manifest.

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

## Resuming

Re-run the same command. The checkpoint is per URL rather than a position or a timestamp:
every row in the manifest carries its own status, so a crawl selects whatever is still
pending and carries on, whether it stopped a minute ago or a year ago.

```bash
uv run bayaz enumerate   # optional, picks up anything the sites published since
uv run bayaz crawl
```

That makes `data/` the only thing worth backing up, since the raw store can be re-fetched
and the corpus re-parsed, but the manifest is what knows which of the 1.75M URLs are done.

Two caveats. Improving a parser means re-parsing, which needs the raw captures on local
disk, so anything moved to cold storage has to come back first. And the APIs in `docs/`
will drift, which is why the endpoints are written down at all; re-verify them against a
current client before a large run rather than trusting a six-month-old note.

`ops/` holds the loop we use to run this on a server, keeping the crawl alive and moving
parsed captures to object storage. It is one deployment rather than part of the tool.

## How it works

All in the `bayaz` library:

- `sitemaps.py` — reads each site's sitemap index; idempotent. Also derives the
  path-segment → kind table that link discovery classifies against.
- `crawl.py` — the sites crawl in parallel, each behind a pacing gate keyed on origin
  rather than site, so hosts that share one machine share one budget
  (`BAYAZ_REQUEST_DELAY` between request starts, `BAYAZ_CONCURRENCY` in flight). Rekhta's
  app backends answer ~5 KB of JSON where the websites serve 90-460 KB pages, so they get
  their own faster budget via `BAYAZ_APP_REQUEST_DELAY` and `BAYAZ_APP_CONCURRENCY`.
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
