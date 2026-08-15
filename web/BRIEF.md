# Brief: the bayaz reading site

You are building the web front end for **bayaz**, a personal archive of the Rekhta
Foundation's Urdu and Hindi literary web. The archive is finished and the API is done and
running. Your job is the site: every page, every component, and the whole visual design.

The scaffold is already correct. Do not change the toolchain, the adapter, the API client or
the token architecture. Build inside them.

---

## 1. Svelte 5 runes. Read this first.

This project is **Svelte 5 in runes mode**, enforced by the compiler. Svelte 4 syntax will not
compile. If you write `export let`, `$:` or `on:click`, the build fails. The differences that
matter:

| Svelte 4 (do not use)          | Svelte 5 runes (use this)                           |
| ------------------------------ | --------------------------------------------------- |
| `export let title`             | `let { title } = $props()`                          |
| `export let title = 'x'`       | `let { title = 'x' } = $props()`                    |
| `let count = 0` (reactive)     | `let count = $state(0)`                             |
| `$: doubled = count * 2`       | `const doubled = $derived(count * 2)`               |
| `$: { sideEffect(count) }`     | `$effect(() => { sideEffect(count) })`              |
| `on:click={fn}`                | `onclick={fn}`                                      |
| `<slot />`                     | `{@render children()}`                              |
| `<slot name="footer" />`       | `{@render footer()}`                                |
| `createEventDispatcher`        | pass a callback prop: `let { onselect } = $props()` |
| `$$props`, `$$restProps`       | `let { ...rest } = $props()`                        |
| `beforeUpdate` / `afterUpdate` | `$effect.pre` / `$effect`                           |

More rules that catch people out:

- **`$derived` takes an expression, not a function.** `$derived(a + b)`. For multi-statement
  logic use `$derived.by(() => { ...; return x })`.
- **`$state` is deep.** `let items = $state([])` then `items.push(x)` is reactive. You do not
  need to reassign.
- **Props are not reassignable by default.** To write back to a prop, the parent must pass a
  `$bindable()`: `let { value = $bindable() } = $props()`.
- **Typing props:** `let { work }: { work: WorkDetail } = $props()`.
- **Children:** a component that wraps content declares
  `let { children }: { children: Snippet } = $props()` and renders `{@render children()}`,
  importing `Snippet` from `'svelte'`.
- **Snippets replace slots entirely.** Define with `{#snippet name(args)}...{/snippet}`,
  render with `{@render name(args)}`.
- **`$effect` is for synchronising with things outside Svelte** (DOM measurement, listeners,
  timers). Do not use it to derive state; that is `$derived`. Do not fetch in it; that is a
  `+page.ts` load function.
- **Class fields can be reactive:** `class Store { items = $state([]) }` works, and is the
  clean way to share state across components. Export an instance from a `.svelte.ts` file.
- Files containing runes outside a component must be named `*.svelte.ts`.

A component in this codebase should look like:

```svelte
<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { WorkSummary } from '$lib/api';

	let { work, children }: { work: WorkSummary; children?: Snippet } = $props();

	const title = $derived(work.title ?? work.title_hindi ?? work.title_urdu ?? 'Untitled');
</script>

<article>
	<h3>{title}</h3>
	{#if children}{@render children()}{/if}
</article>
```

## 2. SvelteKit conventions here

- Data loading happens in **`+page.ts`** files, never in components and never in `$effect`.
  Use the `fetch` the load function is given, and pass it to the api client as the last
  argument: `api.works({ site }, fetch)`.
- A page reads its data with `let { data }: { data: PageData } = $props()`, where `PageData`
  is imported from `'./$types'`.
- `src/routes/browse/[site]/[type]/` is a **worked reference** for all of this. Read it first.
  Its layout is deliberately plain. Copy the mechanics, not the look.
- The site is `adapter-static` with `ssr = false`. There is no server. Never import
  `$env/dynamic/private`, never write a `+page.server.ts`, never use form actions.
- Rest params (`[...slug]`) are already in place where slugs contain slashes. They do.

## 3. The API

Base URL is `/api`, proxied to the running API in dev. The client is at `$lib/api` and is
**fully typed from the live OpenAPI contract**. Import types from there, never redeclare them.

```ts
import { api, ApiError, type WorkDetail } from '$lib/api';

const works = await api.works({ site: 'rekhta', work_type: 'ghazals', limit: 24 }, fetch);
const work = await api.work('rekhta', slug, fetch);
const words = await api.workWords('rekhta', slug, fetch);
const entry = await api.lookup(code, fetch);
```

Available: `sites`, `workTypes`, `works`, `work`, `workWords`, `poets`, `poet`, `poetWorks`,
`entries`, `entry`, `lookup`, `tags`, `tagWorks`, `search`.

Listings return `{ items, total, limit, offset }`. `limit` maxes out at 100.

If you need to see a response shape, run the API and read `/docs`, or read
`src/lib/api/schema.d.ts`. Do not guess field names.

## 4. What the data actually is

Numbers are measured, not estimated. Design for these sizes.

```
works        258,232     rekhta 146,373 · hindwi 76,612 · sufinama 35,247
entries      962,724     the dictionary, across four sites
poets         22,051     also authors, translators, publishers, artists, editors
tags           3,045
work types        58     ghazals 87,672 · quotes 37,773 · couplets 35,051 · nazms 14,367 · stories 3,108
word positions 53.1M     poetry, per script variant
```

Things that will bite you if you assume otherwise:

- **A work has up to three bodies**: `body` (Roman transliteration), `body_hindi`
  (Devanagari), `body_urdu` (Nastaliq, right-to-left). Any of them can be null. Same for
  titles. The reader has to let someone switch script, and Urdu must render RTL.
- **`author_name` is not always Roman.** Some are Devanagari, some Nastaliq. Do not assume.
- **`author_slug` is null for 6,064 works** whose poet page was never captured. No link then.
- **18,395 works have no body at all.** Titles only. Handle it as a normal case.
- **`explanation` and `translation`** are the site's own gloss and English rendering. They are
  deliberately kept out of the verse. If you show them, show them as clearly secondary, never
  mixed into the poem.
- **Word codes:** `/works/…/words` returns variants keyed by `lang`, which is the source's own
  id (`'1'`, `'2'`, `'3'`), not a language code. Each variant has `lines`, each line a list of
  words with a `code`. `api.lookup(code)` resolves a code to a dictionary entry, **but only
  rekhta's poetry codes resolve**. Roughly 592,000 codes on hindwi and sufinama works, and all
  the codes on prose recovered from rekhta.org, resolve to nothing and return 404. A 404 there
  is normal and must not look like an error. Treat word lookup as progressive enhancement.
- **`has_words`** on a work tells you whether the reader can offer word lookup at all.

## 5. Pages to build

```
/                         landing: what the archive is, the four sites with counts, search,
                          and a way in. This is the page that has to make someone stay.
/browse/[site]            the site's work types with counts
/browse/[site]/[type]     paginated listing            (reference implementation exists)
/work/[site]/[...slug]    THE READER. see below.
/poets                    index, filterable by site and entity type
/poet/[site]/[slug]       profile, dates, description, their works
/dictionary               entry point into the dictionary
/word/[site]/[...slug]    an entry: headword in three scripts, senses by language,
                          relations, example couplets
/tag/[tag]                works under a tag
/search                   works and entries, ?q= driven
```

**The reader is the centre of the whole site.** A ghazal in three scripts, where tapping a
word shows its dictionary entry without leaving the poem. Everything else exists to get
someone there. Give it real thought: script switching, line spacing that suits Nastaliq,
a word popover that feels instant, and a graceful nothing-happens when a code has no entry.

## 6. Design

The register is a quiet, literary reading site. Warm, paper-like, typographic. Not a SaaS
dashboard, not a search engine. The archive holds two hundred years of Urdu poetry; the page
should feel like it deserves that.

- **Material 3**, implemented properly through the design tokens already in
  `src/routes/layout.css`. Use the semantic colour roles (`bg-surface`, `text-on-surface`,
  `bg-primary-container`, `text-on-surface-variant`, `border-outline-variant`, …). Add tokens
  there if you need them; never scatter arbitrary hex or one-off values in markup.
- Follow M3 for elevation, shape and state layers. The radius tokens are `rounded-m3-sm`
  through `rounded-m3-xl`.
- **Light and dark** both work through the tokens. Test both.
- **Typography is the design here.** `--font-urdu` (Nastaliq), `--font-hindi` (Devanagari),
  `--font-serif` for reading Roman text, `--font-sans` for the interface. Nastaliq needs far
  more line height than Latin; the token file starts you at 2.4 for `[lang='ur']`.
  Self-host the fonts in `static/fonts/` and declare `@font-face`. Do not hotlink Google Fonts.
- **Responsive**, with layouts genuinely adapted per breakpoint, not a shrunk desktop.
- **Accessible**: semantic HTML, labelled controls, visible focus, keyboard navigation, real
  contrast. `lang` attributes on every non-English passage, and `dir="rtl"` for Urdu.
- **Every state**: loading, empty, error. Not just the happy path. Listings can legitimately
  return zero results, and the API can 404.
- **Components, not copy-paste.** Anything appearing on two pages is a component in
  `src/lib/components/`. Keep files small.
- Icons: `lucide-svelte`, imported individually (`import Search from 'lucide-svelte/icons/search'`).

Interface language is **English** throughout. The literary content is Urdu and Hindi; the
chrome around it is English.

## 7. Working rules

- `bun run check` must pass with zero errors when you are done. Run it as you go.
- `bun run format` before you finish.
- No comments that restate the code. Comment only a non-obvious _why_.
- No dead code, no placeholder routes left empty, no TODOs.
- Do not add dependencies beyond what is installed unless you genuinely need one. If you do,
  say which and why in your final message.
- The API must be running for the site to show data:
  `cd .. && uv run uvicorn bayaz_api.main:app --port 8100`. It is probably already up.
- Build the whole thing. Every route in section 5, working, designed, and checked.
