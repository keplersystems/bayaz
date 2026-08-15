# bayaz-api

A read-only HTTP API over the parsed corpus: 258,232 works, 962,724 dictionary entries,
22,051 poets, and 53.1M word positions across rekhta.org, hindwi.org, sufinama.org and
rekhtadictionary.com.

## Running it

```bash
uv run bayaz-serving data/corpus.db data/serve.db     # ~4 min, 6.58 GB
uv run uvicorn bayaz_api.main:app
```

`BAYAZ_SERVE_DB` points at the database, `BAYAZ_CORS_ORIGINS` is a comma-separated list and
is only needed while the site runs on a different origin.

Interactive docs at `/docs`, the machine-readable contract at `/openapi.json`.

## Why there is a build step

`corpus.db` is shaped for writing, so the API serves a database derived from it. Three
differences, each measured rather than assumed:

**`parsed` is dropped.** It records which URL each parser version consumed: 658 MB of crawl
bookkeeping with no meaning to an HTTP API.

**`works.author_id` is resolved.** rekhta stores the poet's GUID in `author_url` and joins to
`entities` as published. The platform sites store a URL, and the parser often caught the
poet's per-type listing link (`/poets/<poet>/ghazals?lang=ur`), so the poet is the segment
after the entity type, never the last one. Without this, poet pages work on rekhta and return
nothing on the other two.

```
rekhta       146,349 of 146,373    99.98%
hindwi        72,727 of  76,612    94.9%
sufinama      33,092 of  35,247    93.9%
             252,168 of 258,232    97.7%
```

The 6,064 that stay unlinked are works whose poet page was never captured, or that carry no
author link at all.

**Full-text search is built.** The corpus has no FTS table, and `LIKE '%...%'` over the
912 MB `works` table measured 470-670 ms per query. `works_fts` mirrors `works` through
fts5's external-content mode; `entries_fts` cannot, because an entry's definitions live in
`senses` and external content reads one table.

## Routes

```
GET  /health
GET  /sites                                  the four sites and their counts
GET  /sites/{site}/work-types                58 types, most-used first

GET  /works?site=&work_type=&author=
GET  /works/{site}/{slug}                    title and body in up to three scripts
GET  /works/{site}/{slug}/words              word positions, by script variant and line

GET  /poets?site=&entity_type=               poets, authors, translators, publishers, ...
GET  /poets/{site}/{slug}
GET  /poets/{site}/{slug}/works

GET  /entries?site=
GET  /entries/lookup?code=                   word code to entry
GET  /entries/{site}/{slug}                  senses by language, relations, example couplets

GET  /tags?site=
GET  /tags/{tag}/works

GET  /search?q=&kind=works|entries&site=
```

Listings take `limit` (max 100) and `offset`, and return `{items, total, limit, offset}`.

## The reader chain

The one flow worth knowing, because the rest follows from it:

```
/works/rekhta/8b90497f-…            "suna hai log use aankh bhar ke dekhte hain"
/works/rekhta/8b90497f-…/words      3 script variants x 44 lines
                                    first word "sunā", code \287g
/entries/lookup?code=\287g          sunaa / सुना / سُنا
```

`lang` on a word variant is the site's own id (`1`, `2`, `3`), not a language code. That is
what the source supplies, and mapping it would invent a fact the archive does not hold.

Only rekhta's 262,030 poetry codes resolve. The 592,351 codes on hindwi and sufinama works
match no entry, and neither does prose recovered from rekhta.org's own pages, which encodes
the same words differently. Those return 404 by design, so a reader should treat a missing
entry as normal rather than as an error.

## Shape

```
bayaz_api/
  serving.py    corpus.db -> serve.db
  db.py         thread-local read-only connections
  models.py     response models
  listing.py    filtering, counting and paging, shared by every listing
  config.py
  main.py
  routers/      catalog · works · poets · entries · tags · search
```

Endpoints are `def`, not `async def`, so SQLite's blocking reads run on starlette's thread
pool. The database never changes while the process runs, so there is no pool, no write path
and no transactions.

That also means no accounts, favourites or submissions. Adding them means a second, writable
database, not a change to this one.

## Measured

Warm, on the full corpus:

```
listing page 1                    6 ms
listing page 2000 (offset 40k)  110 ms
work detail                       4 ms
search "ishq"                    36 ms      16,924 hits
search "इश्क़"                    59 ms      17,399 hits
search entries                  285 ms
```
