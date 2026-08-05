# Hindwi Dictionary API

The JSON API behind the Hindwi Dictionary mobile apps. It serves the same shabdkosh we
otherwise crawl as HTML from `hindwi.org/hindi-dictionary/meaning-of-<slug>`, and it serves
it structured, so it replaces the `hindwi/dict` portion of the crawl.

Recorded 2026-08-04. Endpoint and parameter names, and every response shape below, were
read off live responses.

Scope: this API serves the Hindwi corpus only. `rekhtadictionary.com` and `sufinama.org`
have separate backends. Verified by calling `GetWordDetailsByIdSlug` with the
rekhtadictionary slug `bhuchkaanaa`, which returns HTTP 200 with an empty payload, while
the hindwi slug `sushamana` returns a full entry.

rekhtadictionary's own API is documented in
[rekhta-dictionary-api.md](rekhta-dictionary-api.md). The two share an envelope and most
field names but differ in base path, parameters, and how meaning blocks nest, so a parser
cannot be shared blindly. Sufinama has not been located yet.

## Base URL and auth

```
https://app-rekhta-dictionary.rekhta.org/api/v1/hindwi-dict/
```

From `BuildConfig.CONFIG_BASE_URL_API_V2`, whose name says V2 while its value is the `/api/v1/`
path. A second base, `CONFIG_BASE_URL_API_ACCOUNT_V5` = `/api/V5_ApiAccount/`, carries login
and registration only and is irrelevant to archiving.

**Same host as the Rekhta Urdu API, different mount point.** That one is
`app-rekhta-dictionary.rekhta.org/rd-api/v1/`. Both resolve to `14.140.111.5`, a different
machine from the websites (`64.185.166.71`) and with no CDN in front of it. The two API
fetchers therefore have to share one pacing gate rather than each getting a budget. Full
detail in [rekhta-dictionary-api.md](rekhta-dictionary-api.md#one-origin-two-apis).

**Read endpoints require no authentication**, in two different ways:

- `GetHomePage` and `GetWordDetailsByIdSlug` send **no `Authorization` header at all**. The
  client never attaches one.
- `search` and `WordListingByCategory` do attach one, built as
  `String.valueOf(DakshaDB.getUserData()?.getAuthorizationToken())`. Logged out that is
  Kotlin null passed through `String.valueOf`, so the app sends the literal four-character
  header value `null` rather than omitting the header. Both return 200 regardless.

No `Bearer` prefix is added at any call site. Some user-scoped endpoints also send a
`TempToken` header set to a fresh `UUID.randomUUID()` per request, which the read endpoints
we use do not.

There is no API key, bearer secret, or request signing for the dictionary API, and no
certificate pinning. The dictionary API does not use a Firebase or other app key.

Practical consequence: we are not reusing anyone's credential. This is an open public read
API. Their terms still govern the traffic, so keep the same pacing discipline as the crawl.

Send a browser-ish or the app's own user agent (`okhttp/4.12.0`). No other header is
required.

## Pacing

Measured on 2026-08-04, all serial with at least 3 s between requests:

| Call | Time | Bytes |
|---|---|---|
| `GetWordDetailsByIdSlug` (`pyaar`, 12 dialects) | 0.19 s | 21,229 |
| `GetWordDetailsByIdSlug` (miss) | 2.62 s | 367 |
| `search` (`pageSize=500`) | 0.33 s | 171,715 |

Warm hits come back in about 0.2 s. The miss was slower than any hit, which suggests misses
fall through a cache; do not read a slow response as a rate limit.

No rate limiting, throttling, or blocking was observed, but total volume across this session
was under 25 requests, which is far too few to conclude anything. Treat that as untested and
keep the crawl's existing pacing gate (`BAYAZ_REQUEST_DELAY`, `BAYAZ_CONCURRENCY`) rather
than assuming the API tolerates more than the HTML crawl does. It is the same organisation's
infrastructure, and being lighter on it is the entire reason for using this API.

## Conventions

Every endpoint except `search` wraps its payload in a status envelope:

```json
{"S": 1, "Me": null, "Mh": null, "Mu": null, "R": <payload>, "T": "2026-08-04T02:08:55.33+05:30"}
```

`S` is the status flag (1 on success), `R` the payload, `T` the server timestamp. `Me`,
`Mh`, `Mu` are message slots for English, Hindi, and Urdu, null in every response observed.
`search` is the exception and returns its object bare, with no envelope.

The server sends more of this envelope than the client models. `BaseApiResponse` maps only
`S`, `Mh`, and `R`, and `Me` is read ad hoc by a `getErrorMessage` helper; `Mu` and `T` are
in the wire responses we captured but appear nowhere in the client. Do not take the client
as the authority on the envelope, and do not assume unmodelled fields are stable.

Client helpers read `S` as `success != 0`. Some sibling models nest `R` inside `R`, so check
the shape per endpoint rather than assuming a uniform payload.

An empty result is still `S: 1`. A missing word gives `S: 1` with an empty `R`, so check the
payload rather than the status flag.

`lang` is hardcoded to `2` in the client. `deviceType` is hardcoded to `0`, though our tests
sent `1` and worked, so the server appears not to care. Field names throughout are two- and
three-letter abbreviations; query parameter casing is inconsistent between camelCase and
PascalCase and is transcribed literally below.

## Endpoints

### GET `search`

Substring search over headwords. This is the app's search box.

| Parameter | Required | Notes |
|---|---|---|
| `lang` | yes | always `2` |
| `keyword` | yes | matches as a substring, not a prefix |
| `pageIndex` | yes | 1-indexed |
| `pageSize` | no | the client never sends it and it is absent from the client entirely, but the server honors it |

The client sends only `lang`, `pageIndex`, and `keyword`, all as strings. Note the path
segment `search` is lowercase, unlike every other endpoint on this base.

```bash
curl -sS -H 'User-Agent: okhttp/4.12.0' -G \
  'https://app-rekhta-dictionary.rekhta.org/api/v1/hindwi-dict/search' \
  --data-urlencode 'lang=2' --data-urlencode 'keyword=प्रेम' \
  --data-urlencode 'pageIndex=1' --data-urlencode 'pageSize=500'
```

Response (bare, no envelope):

```json
{"Total": 98, "TotalPages": 2, "IsRTL": false, "WordList": [...]}
```

`WordList[]` item:

| Field | Type | Notes |
|---|---|---|
| `id` | string | GUID, the word's primary key; also keys the audio file |
| `word` | string | headword as displayed |
| `slug` | string | Roman transliteration, matches the web URL slug |
| `meaning` | string | first sense, flattened for the result list |
| `lang` | int | `2` |
| `dialectSlug` | string | e.g. `hindi` |
| `DialectId` | string | GUID |
| `DialectName` | string | e.g. `Hindi`, `Kumaoni`, `Malvi` |
| `DialectSeq` | int | display order |
| `IsPrimaryWord` | bool | true on every result observed |
| `ScriptId` | int | `1` on every result observed |

Measured: default page size is 60. `pageSize=500` returned 500 items in 0.33 s / 172 KB.
`TotalPages` recomputes against the supplied `pageSize`.

**`Total` saturates at exactly 10000** (Elasticsearch `max_result_window`), so a broad query
cannot enumerate more than 10k words no matter how you page. This does not affect us,
because we enumerate from sitemaps, but it does mean `Total` is not a corpus count.

Results are per dialect, so the same slug can appear more than once (498 unique slugs in a
500-item page).

### GET `GetWordDetailsByIdSlug`

The endpoint that matters. One call returns every dialect's meanings, all senses, relations,
and the audio URLs for a single word.

| Parameter | Required | Notes |
|---|---|---|
| `lang` | yes | always `2` |
| `wordId` | yes | accepts either the slug or the GUID |
| `regionalLangSlug` | yes | e.g. `hindi`; selects which dialect block sorts first |
| `categoryType` | yes | may be empty |
| `searchKeyword` | yes | may be empty; used for hit highlighting |
| `showNonClickableWord` | yes | `false` |
| `deviceType` | yes | client sends `0`; `1` also works |

```bash
curl -sS -H 'User-Agent: okhttp/4.12.0' -G \
  'https://app-rekhta-dictionary.rekhta.org/api/v1/hindwi-dict/GetWordDetailsByIdSlug' \
  --data-urlencode 'lang=2' --data-urlencode 'wordId=prem' \
  --data-urlencode 'regionalLangSlug=hindi' --data-urlencode 'categoryType=' \
  --data-urlencode 'searchKeyword=' --data-urlencode 'showNonClickableWord=false' \
  --data-urlencode 'deviceType=1'
```

Since `wordId` takes the slug, the slugs already in `pages.url` map straight onto this call:
`https://www.hindwi.org/hindi-dictionary/meaning-of-<slug>` gives `wordId=<slug>`.

#### `R.BI`, basic info

| Field | Type | Notes |
|---|---|---|
| `I` | string | word GUID, lowercase |
| `W1` | string | headword, Devanagari |
| `W2`, `W3` | string | second and third script slots, **empty on every Hindwi word observed**; the model is shared with the tri-script Rekhta Urdu dictionary |
| `WM` | string/null | meaning summary, null on both words observed |
| `WO` | string | origin language, e.g. `संस्कृत` |
| `HA` | bool | has audio |
| `AMF` | string | **direct mp3 URL** |
| `AOF` | string | **direct ogg URL** |
| `ST` | string | share text, and the only place the canonical web URL appears: `https://hindwidictionary.com/meaning-of-<slug>` |
| `WU` | string | empty on both words observed |
| `RF`, `ME`, `MH`, `MU` | | flag and message slots, unset |

#### `R.RLL`, regional language list

One entry per dialect that has content for this word. `RML` is parallel to it by index.

| Field | Type | Notes |
|---|---|---|
| `WI` | string | word GUID |
| `I` | string | dialect GUID |
| `RLN` | string | dialect name in Devanagari, e.g. `हिंदी` |
| `SS` | string | dialect slug, e.g. `hindi` |
| `SRL` | bool | selected/primary |

#### `R.RML`, meanings per dialect

`RML[i]` corresponds to `RLL[i]`. Each block has `HT` (a rendered header such as
`'प्रेम' के हिंदी अर्थ`), `ML[]` (meaning containers), `R[]` (relation groups), and `AWV`.

The senses are nested four deep:

```
RML[].ML[].R[].MGL[].MT        part of speech, e.g. "संज्ञा, पुल्लिंग"
RML[].ML[].R[].MGL[].WM[].C    the sense text itself
RML[].ML[].R[].MGL[].WM[].RW[] related words inline in the sense
RML[].ML[].R[].IL / .VL / .SL  idiom / verse / sentence example slots
```

`ML[].SW` repeats the headword for that dialect. `MGL[]` groups senses under one part of
speech, and a word can carry several groups.

`IL`, `VL`, and `SL` were **null on both words sampled**, so the populated shape of the
example slots is unconfirmed for this corpus.

#### `R.RML[].R`, relation groups

| Field | Type | Notes |
|---|---|---|
| `CT` | string | relation type; only `synonyms` observed on Hindwi |
| `HT` | string | rendered header, e.g. `प्रेम के पर्यायवाची शब्द` |
| `PS`, `TP`, `TT` | int | page size, type, and template hints |
| `R[]` | array | the related words |

Relation items use the same shape as `WordListingByCategory` results:
`I` (GUID), `W1`/`W2`/`W3` (script slots), `WM` (meaning), `WO` (origin), plus unset flags.
Relations attach to the dialect block, not to the word: for प्रेम all 119 synonyms hang off
the Hindi block and the other eight dialects carry none.

#### `R.AIL`, additional info

One entry per labelled extra row, mirroring the attribute rows on the web page.

| Field | Type | Notes |
|---|---|---|
| `CT` | string | `alternate-word`, `origin` |
| `ST` | string | display label, e.g. `अथवा : ` |
| `R[]` | array | items of `{WI, WV}`, where `WV` is the value |

`R.FD` carries a per-request timestamp. `R.R` was an empty array on every word sampled.

#### Detecting a miss

An unknown word returns **HTTP 200 with a 367-byte skeleton**, not a 404. Neither status
flag helps:

- envelope `S` is `1` on both a hit and a miss
- **`R.S` is `false` on hits too**, so it is not a found-flag despite the name

Use the payload instead. A miss looks like this, and the tells are unambiguous:

```json
{"S": 1, "Me": null, "Mh": null, "Mu": null,
 "R": {"RLL": [], "RML": [], "AIL": [], "R": [],
       "BI": {"I": "00000000-0000-0000-0000-000000000000", "W1": null, "W2": null, "W3": null,
              "WM": null, "WO": null, "HA": null, "AMF": "", "AOF": "", "ST": null, "WU": "",
              "RF": false, "ME": null, "MH": null, "MU": null},
       "FD": "0001-01-01T00:00:00", "S": false, "AppInfo": null, "ADB": null},
 "T": "2026-08-04T02:14:56.60+05:30"}
```

Check any of: `R.BI.I` equal to the all-zero GUID, `R.BI.W1` null, or `R.RML` empty. `R.FD`
also degrades to `0001-01-01T00:00:00`, which is .NET `DateTime.MinValue`.

Verified twice: with `bhuchkaanaa` (a real word, but in the rekhtadictionary corpus) and
with the nonsense slug `zzzznotarealwordzzzz`. Both give byte-identical skeletons, so a
wrong-corpus slug and a nonexistent slug are indistinguishable from the response.

### GET `WordListingByCategory`

Flat word lists for a named category.

| Parameter | Required | Notes |
|---|---|---|
| `wordId` | **yes** | may be empty, but must be present |
| `lang` | yes | `2` |
| `category` | yes | see below |
| `pageIndex` | yes | 1-indexed |
| `pageSize` | yes | |
| `searchKeyword` | yes | may be empty |
| `showNonClickableWord` | yes | client defaults this one to `true`, unlike the detail call |

The Kotlin argument is `categoryType` while the wire key is `category`. This endpoint and
`search` are the two read calls that carry an `Authorization` header.

> **Gotcha:** omit `wordId` entirely and the server hangs, then cancels the stream after
> about 32 seconds. Send it empty rather than dropping it.

Category slugs seen in the client: `top-searched-word`, `meaning-of`, `word-family`,
`tooltip-pos`, `alternate-word`, `origin`. `top-searched-word` is a curated list of about 50
words. Returns `R[]` as a flat array with no total, so it is not a corpus enumerator.

### GET `GetHomePage`

| Parameter | Required | Notes |
|---|---|---|
| `lang` | yes | `2` |
| `lastFetchDate` | yes | client always sends it empty |
| `deviceType` | yes | client sends `0` |

Returns ten curated sections in `R.R[]` plus `R.ExploreMore`. Useful only for discovering
category slugs.

`lastFetchDate` is homepage cache control and **not** a corpus changed-since filter. Tested
with `lastFetchDate=2026-08-01`: the same ten sections came back, differing only in the
banner and word-of-the-day sections, which rotate per request anyway.

### Full endpoint inventory

The complete surface declared by the client, for reference. Everything below the first four
is user-scoped, holds nothing archivable, and was neither called nor tested.

On `/api/v1/hindwi-dict/`:

| Path | Verb | Archivable |
|---|---|---|
| `search` | GET | **yes** |
| `GetWordDetailsByIdSlug` | GET | **yes** |
| `WordListingByCategory` | GET | **yes** |
| `GetHomePage` | GET | **yes**, for category discovery |
| `GetFavoriteListWithPaging` | GET | no |
| `GetRecentActivity` | GET | no |
| `RemoveRecentActivity?isRemoveAll=true` | GET | no |
| `GetUserSettings` | GET | no |
| `SetUserSettings` | POST | no |
| `MarkFavorite?targetId=` | POST | no |
| `RemoveFavorite?targetId=` | POST | no |
| `SaveUserFeedback` | POST | no |
| `SaveUploadedWordImages` | POST | no |
| `DeviceRegisterForPush?deviceId=` | POST | no |

On `/api/V5_ApiAccount/`: `Login?reToken=`, `LoginExternal?reToken=`, `Register`,
`ForgotPassword?reToken=`, `GetProfileDeletionReason`, `DeleteProfile?reasonText=`,
`CancelDeleteProfile`, `CheckProfileReactivation`. Account management, all irrelevant here.

### The client is not a reliable spec

Worth knowing before reasoning from the client rather than from live responses,
because several of its methods do not do what their names say:

- `setUserSettings` issues a GET against `GetUserSettings` and writes nothing. Only
  `setProfile` reaches the real `SetUserSettings` path.
- `appVersionInfo` and `registerDeviceForPush` both POST an empty body to
  `Login?reToken=`, carry no relevant payload, and never touch `DeviceRegisterForPush`.
  They look like copy-paste stubs.
- `MarkFavorite` hardcodes `lang=1`, ignoring the selected language everywhere else.
- `setRecentWordData` puts `Authorization` into the header map twice.

Treat the endpoint values as authoritative and the surrounding client behaviour as
approximate. Everything in this document that describes a response was read from a live
response, not inferred from the client.

## Audio

`BI.AMF` and `BI.AOF` give the mp3 and ogg URLs directly, so no derivation is needed when
fetching a word detail:

```
https://www.rekhta.org/Images/SiteImages/HindwiDictionaryAudio/{GUID-UPPERCASE}.mp3
https://www.rekhta.org/Images/SiteImages/HindwiDictionaryAudio/{GUID-UPPERCASE}.ogg
```

The GUID is `BI.I` uppercased, which is also `WordList[].id` from search, so audio URLs can
be built from a search sweep without fetching details.

Verified downloadable: a HEAD on the प्रेम mp3 returns 200, `audio/mpeg`, 71,146 bytes,
`accept-ranges: bytes`, served by `x-powered-by: Rekhta`. Note this host differs from the
`rekhta.pc.cdn.bitgravity.com` CDN recorded during HTML recon, so confirm which one the
bulk audio job should pull from.

## What this replaces

`hindwi/dict` is 343,477 of the 1,569,901 dictionary pages in the manifest, about 22%.

| | HTML crawl | This API |
|---|---|---|
| Requests | 1 per word | 1 per word |
| Bytes per word | 189.6 KB average (n=20 fetched) | 1.5 KB (सुषमना) to 26.2 KB (प्रेम, 9 dialects) |
| Parse | offline HTML extraction | none, already structured |
| Audio discovery | requires fetching the page | included in the detail response |
| Dialect attribution | inferred from markup classes | explicit, with dialect GUID, name, and slug |

Request count is unchanged because Hindwi already serves one page per word. The win is
bytes off their servers, roughly 7x to 130x less, plus dialect attribution that the HTML
only implies.

Enumeration stays on the sitemaps. Slugs come from `pages.url`, so the API's missing bulk
enumerator, missing total count, and 10,000-result ceiling are all irrelevant to us. Do not
build a keyword-prefix sweep to work around them; it would reintroduce a completeness
question the sitemaps already answer.

Delta stays `enumerate` then `crawl`, unchanged. The API has no changed-since filter.

## What it does not cover

This is the dictionary app, so it serves the shabdkosh and nothing else. Hindwi's literary
side has no API path here and stays on the HTML crawl.

| Kind | Pages | Avg page | Sampled | Source |
|---|---|---|---|---|
| `dict` | 343,477 | 185.2 KB | 20 | **this API** |
| `work` | 45,547 | 226.6 KB | 15 | HTML crawl |
| `entity` | 19,170 | 200.0 KB | 6 | HTML crawl |
| `tag` | 4,568 | not yet fetched | 0 | HTML crawl |
| `collection` | 853 | 267.1 KB | 15 | HTML crawl |
| `emagazine`, `work-type`, `static`, `entity-type` | 169 | not yet fetched | 0 | HTML crawl |

Hindwi is 413,784 pages in the manifest. The API covers 343,477 of them, 83% by count and
about 80% by bytes (roughly 61 GB of the 75 GB). The 70,307 pages left are around 15 GB.

The same trick may apply to most of that remainder. The Rekhta Foundation ships a separate
app per property, and this is specifically the *dictionary* app. A Hindwi content app, if
one exists, would likely cover `work` and `entity`, which are 64,717 pages, 92% of what is
left. Worth checking before committing to crawling them as HTML. After that the leftovers
are tags, collections, emagazines and static pages, about 5,600 pages, small enough that
crawling them is not worth optimising.

`sufinama/dict` (294,465 pages) and all of `rekhtadictionary` (933,150) have their own
backends and are out of scope for this endpoint. See the note under Scope above.

## Capture path

Switching the dictionary to the API changes what lands in `raw/`: JSON responses rather
than served HTML. That is still raw-first in the sense that matters, since it is stored
exactly as returned and before any parsing, so a parser bug still never costs a re-fetch.
It is a different artifact from the rendered page, though, and two things follow:

- The `hindwi dict` extractor in `bayaz/parse/platform.py` expects HTML and would need a
  JSON path alongside it. The corpus schema itself does not change; the API carries the
  same fields the HTML does, with dialect attribution the markup only implies.
- The rendered page and the API response are not identical artifacts. If the point is to
  preserve the page as a reader saw it, the API supplements the crawl. If the point is the
  structured corpus, the API replaces it. Decide this deliberately rather than by default.

## Field glossary

The API names everything in two- and three-letter abbreviations, and the same abbreviation
can mean different things at different depths. Expansions marked *(inferred)* are read from
context rather than stated anywhere in the client.

| Field | Where | Meaning |
|---|---|---|
| `S` | envelope | success flag, `1` on success |
| `R` | envelope | response payload |
| `T` | envelope | server timestamp |
| `Me`, `Mh`, `Mu` | envelope | message, English / Hindi / Urdu *(inferred from `getErrorMessage`)* |
| `BI` | `R` | basic info *(inferred)* |
| `RLL` | `R` | regional language list |
| `RML` | `R` | regional meaning list, parallel to `RLL` |
| `AIL` | `R` | additional info list *(inferred)* |
| `FD` | `R` | fetch date; `0001-01-01T00:00:00` on a miss |
| `I` | `BI`, relation item | GUID of the word |
| `WI` | `RLL`, `AIL` item | word GUID |
| `W1`, `W2`, `W3` | `BI`, relation item | script slots 1 to 3; only `W1` used on Hindwi |
| `WM` | `BI`, relation item | word meaning |
| `WO` | `BI`, relation item | word origin, e.g. `संस्कृत` |
| `WU` | `BI` | unused on every word sampled |
| `HA` | `BI` | has audio |
| `AMF` | `BI` | audio mp3 file URL |
| `AOF` | `BI` | audio ogg file URL |
| `ST` | `BI` | share text; carries the canonical web URL |
| `ST` | `AIL` item | display label, e.g. `अथवा : ` (different meaning from `BI.ST`) |
| `RLN` | `RLL` item | regional language name, e.g. `हिंदी` |
| `SS` | `RLL` item | slug of that language, e.g. `hindi` |
| `SRL` | `RLL` item | selected regional language |
| `ML` | `RML` item | meaning list |
| `MGL` | `ML[].R[]` | meaning group list, one per part of speech |
| `MT` | `MGL` item | meaning type, i.e. part of speech |
| `WM` | `MGL` item | word meanings array (**an array here**, a string on `BI`) |
| `C` | `MGL[].WM[]` | the sense text itself |
| `RW` | `MGL[].WM[]` | related words inline in that sense |
| `MN` | `MGL[].WM[]` | null on every sample |
| `IL`, `VL`, `SL` | `ML[].R[]` | idiom / verse / sentence lists *(inferred)*; null on every sample |
| `CT` | relation group, `AIL` | category or relation type, e.g. `synonyms`, `origin` |
| `HT` | most containers | heading text, pre-rendered for display |
| `SW` | most containers | subject word, the headword being described |
| `AWV` | `RML` item | empty on every sample |
| `DE` | most containers | null or empty on every sample |
| `PS`, `TP`, `TT`, `TBC`, `IC`, `RF` | most containers | display and template hints, not content |

Anything in the last row can be ignored by a parser. `HT` and `ST` are pre-rendered display
strings and should be treated as presentation, not data, since they bake the headword and
labels into a sentence.

## Archiving recipe

Enumeration comes from the manifest, not the API. The slug is already the last path segment
of every `hindwi/dict` URL, so no discovery step is needed:

```sql
select url, replace(url, 'https://www.hindwi.org/hindi-dictionary/meaning-of-', '') as slug
from pages where site = 'hindwi' and kind = 'dict';
```

Per slug, one call gets everything:

```bash
curl -sS -H 'User-Agent: okhttp/4.12.0' -G \
  'https://app-rekhta-dictionary.rekhta.org/api/v1/hindwi-dict/GetWordDetailsByIdSlug' \
  --data-urlencode 'lang=2' --data-urlencode "wordId=$SLUG" \
  --data-urlencode 'regionalLangSlug=hindi' --data-urlencode 'categoryType=' \
  --data-urlencode 'searchKeyword=' --data-urlencode 'showNonClickableWord=false' \
  --data-urlencode 'deviceType=0'
```

Then:

1. Check for a miss via `R.BI.I` against the all-zero GUID. Record misses rather than
   discarding them; a slug in the sitemap that the API does not know is a real finding about
   corpus drift between the two.
2. Store the response body verbatim, gzipped, keyed the same way `rawstore.py` keys pages.
3. Take audio from `R.BI.AMF` and `R.BI.AOF` directly. No separate discovery pass, and
   `R.BI.HA` says whether audio exists at all.
4. Parse offline from the stored JSON. Senses are at
   `R.RML[].ML[].R[].MGL[].WM[].C` with part of speech at the enclosing `MGL[].MT`, and the
   dialect for each block comes from the parallel `R.RLL[]` entry.

`regionalLangSlug=hindi` only decides which dialect block sorts first. Every dialect comes
back regardless, so it does not need to vary per word.

Do not paginate `search` to enumerate. It cannot return more than 10,000 results per query,
it returns one row per dialect rather than per word, and the sitemaps already give a complete
and deduplicated slug list.

## Confirmed, and not

Everything above was recorded on 2026-08-04, in about 25 requests total. Endpoint paths,
parameter names, and response shapes come from live responses.

Verified live: the base URL, absence of auth on all four read endpoints, `pageSize` override,
the 10,000 `Total` ceiling, the `WordListingByCategory` hang when `wordId` is omitted,
slug-as-`wordId` against real manifest slugs, the miss skeleton, that `R.S` is false on hits,
audio URLs downloading, and every field in the tables above.

Words sampled: प्रेम (`prem`, 9 dialects, 119 synonyms), प्यार (`pyaar`, 12 dialects),
सुषमना (`sushamana`, 1 dialect), plus two misses. That is a thin sample, and the gaps below
follow from it.

Unverified:

- The populated shape of `IL`, `VL`, and `SL`. Null on all three words. Hindwi is a shabdkosh
  rather than a poetry corpus, so they may never populate here, but a word carrying a cited
  usage example would settle it.
- Whether `W2` and `W3` are ever non-empty on Hindwi. Empty on all three, and the corpus is
  single-script, so probably always empty. They exist because the model is shared with the
  tri-script Rekhta Urdu dictionary.
- Relation types beyond `synonyms`. Only that one appeared, and only on प्रेम.
- Whether `WordListingByCategory` is useful for anything beyond the curated
  `top-searched-word` list. The other category slugs were read from the client, not called.
- Rate limits. Nothing was observed, but 25 requests proves nothing. See Pacing.
- Whether the API corpus and the sitemap corpus agree in size or membership. The 10,000
  ceiling hides the API's real total, so this can only be checked by running manifest slugs
  through the API and counting misses.
