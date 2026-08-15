# bayaz web

The reading site: 258,232 works in up to three scripts, 962,724 dictionary entries, and a
reader where tapping a word of verse shows its meaning without leaving the poem.

SvelteKit with `adapter-static`, Svelte 5 runes, Tailwind 4. There is no server: the build is
a bundle of static files, and every page fetches from [`bayaz-api`](../bayaz-api/README.md) in
the browser.

## Running it

```bash
cd .. && uv run uvicorn bayaz_api.main:app --port 8100     # the api
bun install && bun run dev                                 # the site, /api proxied to it
```

`bun run build` writes the static bundle to `build/`. Serve it behind anything, with `/api`
proxied to the API; a `fallback` shell means any path resolves without prerendering 258,232
pages.

`bun run api:types` regenerates `src/lib/api/schema.d.ts` from the live `/openapi.json`. Every
response type in `$lib/api` comes from there, so nothing in this codebase restates the
contract by hand. Regenerate rather than edit.

## Routes

```
/                        the archive, its four sites, and a way in
/browse/[site]           work types with counts
/browse/[site]/[type]    paginated listing
/work/[site]/[...slug]   the reader
/poets                   index, filtered by site and role
/poet/[site]/[slug]      profile and works
/dictionary              entry point
/word/[site]/[...slug]   senses by language, relations, example couplets
/tag/[tag]
/search                  works or dictionary entries
```

Slugs are rest params because 88,925 of them contain slashes.

## The reader

A work carries up to three bodies: Roman transliteration, Devanagari, and Nastaliq which is
right-to-left. Any of them can be null, so the script switcher disables what a work does not
have. Nastaliq needs far more line height than Latin; that lives in the `[lang='ur']` rule and
the `--text-nastaliq` scale rather than in markup.

Verse is grouped into couplets, prose flows as paragraphs. `explanation` and `translation` are
the source's own gloss and English rendering, and they render as secondary cards below the
poem, never mixed into the verse.

Word lookup is progressive enhancement, not a feature that can fail. `/works/…/words` gives
every word a `code`, and `/entries/lookup` resolves it, but only rekhta's 262,030 poetry codes
are in the dictionary. Roughly 592,000 codes on hindwi and sufinama works, and every code on
prose recovered from rekhta.org's own pages, resolve to nothing. The popover treats that as a
quiet nothing rather than an error.

18,395 works have no body at all and are shown as catalogued by title only. 6,064 have no poet
link because that poet's page was never captured, and then there is no link.

## Design

Material 3 through design tokens in `src/routes/layout.css`: colour roles in OKLCH, light and
dark defined token-side so no component knows which theme it is in, plus the type scale, radii
and the three script families. Add tokens there; never scatter arbitrary values in markup.

Fonts are self-hosted in `static/fonts/`, subsetted per script with `unicode-range`, 684 KB in
total. Nothing is fetched from Google.

Interface language is English. The literary content is Urdu and Hindi.

## Shape

```
src/
  lib/
    api/        typed client; schema.d.ts is generated
    components/ 15 components, nothing page-specific
    scripts.ts  script detection and formatting helpers
  routes/       one directory per route, data loaded in +page.ts
```

Data loading belongs in `+page.ts`, never in a component and never in `$effect`. Components
take props and render.
