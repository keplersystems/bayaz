# Rekhta Urdu Dictionary API

The JSON API behind the Rekhta Urdu Dictionary mobile apps. It serves the tri-script Urdu
dictionary we otherwise crawl as HTML from `rekhtadictionary.com`, and it is the single
largest reduction available to this project: it can replace roughly 927,000 of
rekhtadictionary's 933,150 pages.

Source: Rekhta Urdu Dictionary for Android 1.1.10 (versionCode 35), package
`com.rekhta.dict`. Endpoint and parameter names transcribed from the decompiled client;
every response shape below was read off a live response. Recorded 2026-08-04.

This is a sibling of the [Hindwi Dictionary API](hindwi-dictionary-api.md) and shares its
envelope and most field names, but the base path, the parameter set, and the meaning-block
nesting all differ. Read the differences below rather than assuming the two are
interchangeable.

## Base URL and auth

```
https://app-rekhta-dictionary.rekhta.org/rd-api/v1/
```

Note `rd-api`, not `api`. There is no `NetworkAPIConstants` class here: every endpoint is a
hardcoded absolute URL in the `@GET` annotation of `com/rekhta/network/RekthaApi.smali`
(their typo, "Rektha"). Retrofit's configured `baseUrl` is
`https://world.rekhta.org/api/V5_ApiAccount/` and applies only to account endpoints.

**No authentication on any read endpoint**, and more cleanly than on Hindwi: the read
methods declare no `Authorization` parameter at all, so nothing is sent. The OkHttp builder
adds a logging interceptor and Chucker, with no auth interceptor and no signing.
`Authorization` and `TempToken` exist only on user-scoped endpoints.

`res/values/strings.xml` carries a Firebase `google_api_key`, a `facebook_client_token`, and
a Google OAuth client id. None of them are used by or needed for the dictionary API, so
there is no credential of theirs in play when we call it.

Send the app's user agent (`okhttp/4.12.0`). Nothing else is required. Responses support
gzip, so send `--compressed`.

## Languages

Unlike Hindwi, `lang` is user-selectable and meaningful. From `com/rekhta/enums/Language`:

| `lang` | Language |
|---|---|
| `1` | English |
| `2` | Hindi |
| `3` | Urdu |

`lang` does **not** filter content. It rotates which script lands in `W1` and which meaning
block sorts first. See "What one call actually returns" below, which is the crux of the
whole document.

## Conventions

The envelope is identical to Hindwi's:

```json
{"S": 1, "Me": null, "Mh": null, "Mu": null, "R": <payload>, "T": "<timestamp>"}
```

`search` is the exception and returns bare. As on Hindwi, `R.S` is `false` even on a
successful hit, so it is not a found-flag; detect a miss via `R.BI.I` against the all-zero
GUID.

A wrong slug fails silently with `S: 1` and an all-null payload. In particular the **full web
slug does not work**: `wordId=urdu-meaning-of-warn` returns the empty skeleton, while
`wordId=warn` returns the entry. Strip the prefix.

## Endpoints

All read endpoints are GET and unauthenticated.

| Path | Query parameters, in interface order |
|---|---|
| `search` | `keyword`, `lang`, `pageIndex` |
| `GetWordDetailsByIdSlug` | `lang`, `wordId`, `deviceType`, `categoryType`, `searchKeyword`, `showNonClickableWord` |
| `WordListingByCategory` | `wordId`, `lang`, `category`, `pageIndex`, `searchKeyword`, `showNonClickableWord` |
| `GetHomePage` | `lang`, `lastFetchDate`, `deviceType` |
| `GetVocabularyFeed` | `pageIndex`, `displayDate`, `lang`, `deviceType` |
| `GetAppUrl` | `deviceType`, `lang` |
| `GetAppVersionInfo` | `deviceType` |

Client constants: `deviceType=0`, `searchKeyword=""`, `showNonClickableWord=true`.

Differences from the Hindwi endpoints of the same name:

- `search` has **no `pageSize`**. Page size is fixed server-side at 60.
- `GetWordDetailsByIdSlug` has **no `regionalLangSlug`**.
- `WordListingByCategory` uses `category` and adds `pageIndex`, `searchKeyword`,
  `showNonClickableWord`.
- Interface methods `getWordDetailsV2` and `getWordDetailsV3` are identical and hit the same
  path; only V3 is called.

### GET `GetWordDetailsByIdSlug`

```bash
curl -sS --compressed -A 'okhttp/4.12.0' \
 'https://app-rekhta-dictionary.rekhta.org/rd-api/v1/GetWordDetailsByIdSlug?lang=1&wordId=ishq&deviceType=0&categoryType=&searchKeyword=&showNonClickableWord=true'
```

`wordId` accepts the slug or the GUID.

#### What one call actually returns

This is the finding that collapses the crawl. On the web a word is three URLs whose content
genuinely differs (`/meaning-of-X`, `?lang=hi`, `?lang=ur`). One API call returns all of it.

**All three scripts, always.** `W1` is the selected language's script and the others follow:

| | `lang=1` | `lang=3` |
|---|---|---|
| `W1` | `bhuchkaanaa` | `بُھچکانا` |
| `W2` | `भुचकाना` | `bhuchkaanaa` |
| `W3` | `بُھچکانا` | `भुचकाना` |

No call omits a script.

**All three languages' meanings, in one call.** A single `lang=1` request for `ishq` returned
three sibling blocks under `RML[0].ML[]`, each with its own full and genuinely different
sense list:

```
RML[0].ML[0].HT = "English meaning of 'ishq"
RML[0].ML[1].HT = "'इश्क़ के हिंदी अर्थ"
RML[0].ML[2].HT = "عِشْق کے اردو معانی"
```

`lang` only reorders them. `BI.ME`, `BI.MH`, and `BI.MU` additionally carry a one-line
meaning summary per language, all three populated (on Hindwi these are always null).

**The one reason to still make three calls.** Two things render in the selected script only:

- `SL`, the sher examples, attach to the **first block only** and are in that script.
  `lang=1` gives `sitāroñ se aage jahāñ aur bhī haiñ`; `lang=3` gives
  `ستاروں سے آگے جہاں اور بھی ہیں`. That is genuinely different content, not a transliteration
  we can generate.
- Relation entries return `W1` populated with `W2`/`W3` null, so related headwords come back
  in one script. This one is recoverable without extra calls, since every relation entry
  carries its GUID `I` and can be joined to that word's own record.

So: one call per word if shers in a single script are acceptable, three if you want the
couplets in all three. Both are enormous improvements over three 368 KB page fetches.

#### `R.BI`, basic info

| Field | Notes |
|---|---|
| `I` | word GUID |
| `W1`, `W2`, `W3` | the three scripts, rotated by `lang` |
| `ME`, `MH`, `MU` | one-line meaning summary in English, Hindi, Urdu, **all populated** |
| `WO` | origin language, e.g. `Arabic` |
| `WM` | null on every word sampled |
| `HA` | has audio |
| `AMF`, `AOF` | direct mp3 and ogg URLs |
| `ST` | share text, carrying the canonical URL `https://rekhtadictionary.com/meaning-of-<slug>` |
| `WU`, `RF` | unused |

#### `R.RML`, meanings

The nesting differs from Hindwi. Here `RML` holds a **single** block, and the per-language
split lives one level down in `ML[]`:

```
RML[0].ML[i]                     language block, i = English / Hindi / Urdu
RML[0].ML[i].R[].MGL[].MT        part of speech, e.g. "Noun, Masculine"
RML[0].ML[i].R[].MGL[].WM[].C    the sense text
RML[0].ML[i].R[].MGL[].WM[].ME   usage example object, see below
RML[0].ML[i].R[].SL              sher list, first block only
RML[0].ML[i].R[].IL / .VL        null on every word sampled
```

On Hindwi, by contrast, `RML[i]` is one block per dialect. Do not share a parser between the
two without accounting for this.

**Usage examples** arrive as an object on `WM[].ME`, which is null on Hindwi:

```json
{"MT": "Example", "RF": false, "MEN": [{"EN": "Ali ka Zara ke liye ishq itna gehra hai ke woh sab kuch bhool gaya."}]}
```

#### `R.RML[0].R`, relation groups

All six relation types that are separate web pages for us arrive inline. Observed on `ishq`:

| `CT` | `HT` | `PS` | Returned |
|---|---|---|---|
| `synonyms` | Synonyms of 'ishq | 15 | 14 |
| `antonyms` | Antonyms of 'ishq | 15 | 4 |
| `compound` | Compound words of 'ishq | 15 | 15 |
| `idioms` | Idioms of 'ishq | 5 | 5 |
| `proverb` | Proverbs of 'ishq | 5 | 5 |
| `qaafiya` | Rhyming words of 'ishq | 15 | 4 |

Note the inconsistent pluralisation (`compound` and `proverb` singular against `synonyms`,
`antonyms`, `idioms`). Transcribe literally.

`PS` is the inline page size. A group returning exactly `PS` items is truncated and the
remainder needs `WordListingByCategory`; a group returning fewer is complete.

Relation items: `{I, W1, W2, W3, WM, WO, RF, ME, MH, MU}`, with `W2`/`W3` null as noted.

#### `R.RML[0].ML[0].R[0].SL`, shers

`SL.R[]` items carry poet attribution and **word-tokenised** text:

| Field | Notes |
|---|---|
| `I` | sher GUID |
| `PN` | poet name, e.g. `Allama Iqbal` |
| `RW` | array of `{W, SW}` tokens; the sher text is the `W` values joined |
| `WM`, `PD`, `BG` | null on every sher sampled |

The text is tokenised so the site can make each word clickable, so a parser has to rejoin
`RW[].W`. Note `BG` is null, meaning the API does **not** carry the ghazal URL that the HTML
parser currently extracts. That is a genuine regression against the HTML path.

#### `R.AIL`, additional info

| `CT` | `ST` | Example value |
|---|---|---|
| `origin` | `Origin : ` | `Arabic` |
| `vazn` | `Vazn : ` | `21` |
| `tags` | `Tags : ` | `Medical` |
| `word-family` | `Word Family : ` | `a-sh-q` |

`word-family` gives the root and its GUID, **not** the member list. See the gap below.

### GET `search`

```bash
curl -sS --compressed -A 'okhttp/4.12.0' \
 'https://app-rekhta-dictionary.rekhta.org/rd-api/v1/search?keyword=warn&lang=1&pageIndex=1'
```

`pageIndex` is 1-based, page size is fixed at 60, and the response carries `Total` and
`TotalPages` (`warn` gave `Total: 167, TotalPages: 3`). Whether a 10,000-result ceiling
applies as it does on Hindwi was **not tested**.

Not needed for archiving: enumeration comes from sitemaps.

### GET `WordListingByCategory`

```bash
curl -sS --compressed -A 'okhttp/4.12.0' \
 'https://app-rekhta-dictionary.rekhta.org/rd-api/v1/WordListingByCategory?wordId=ishq&lang=1&category=compound&pageIndex=2&searchKeyword=&showNonClickableWord=true'
```

Only needed for relation groups that hit their `PS` ceiling in the detail response.

- `pageIndex` is 1-based, with `0` clamped to `1` (verified: pages 0 and 1 are byte-identical).
- Page size is **6**.
- **There is no total or page count.** The payload is a bare array, so you must paginate
  until `R` comes back empty. Budget for that in the crawler.

## Audio

`BI.AMF` and `BI.AOF` are absolute URLs, with `BI.HA` as the has-audio flag:

```
https://www.rekhta.org/Images/SiteImages/DictionaryAudio/{GUID-UPPERCASE}.mp3
https://www.rekhta.org/Images/SiteImages/DictionaryAudio/{GUID-UPPERCASE}.ogg
```

Note the path segment is `DictionaryAudio`, against Hindwi's `HindwiDictionaryAudio`.

**The audio GUID is not the word GUID.** For `ishq` the word is
`f3f55c98-c907-4924-bcd4-d11bff03b4b3` while the audio is
`CEC6ABC5-AA36-4608-9678-FBA37D8720CF`. You must read `AMF`/`AOF` and cannot synthesise the
URL, which is the opposite of the Hindwi case. Words without audio return `HA: false` and
empty strings.

## What this replaces

The manifest holds 853,365 `word` pages for rekhtadictionary, which is **284,455 unique
words** across three URL variants each:

| Web prefix | Words | Pages |
|---|---|---|
| `meaning-of-` | 263,264 | 789,792 |
| `urdu-meaning-of-` | 21,191 | 63,573 |

Slug extraction is stripping that prefix and any `?lang=` suffix.

| Kind | Pages | Source after this change |
|---|---|---|
| `word` | 853,365 | **API**, 284,455 calls at one per word |
| `compound` | 32,475 | **API**, inline in the detail response |
| `synonym` | 18,033 | **API**, inline |
| `idiom` | 16,431 | **API**, inline |
| `antonym` | 3,999 | **API**, inline |
| `proverb` | 2,976 | **API**, inline |
| `word-family` | 4,680 | **HTML crawl**, no API path |
| `tag` | 1,110 | HTML crawl |
| `blog` | 63 | HTML crawl |
| `static` | 18 | HTML crawl |

That is **927,279 of 933,150 pages replaced**, leaving 5,871 on the HTML crawl.

Observed response sizes: `bhuchkaanaa` 3.7 KB, `warn` 6.2 KB, `ishq` 21.6 KB (three
languages, six relation groups, six shers), against 368 KB per HTML page.

| | HTML crawl | API, 1 call/word | API, 3 calls/word |
|---|---|---|---|
| Requests | 853,365 | 284,455 | 853,365 |
| Bytes | ~314 GB | ~1.7 GB | ~5 GB |

Even the full-fidelity three-call option, at identical request count to the current plan, is
roughly a 60x reduction in bytes taken off their servers. The one-call option is a 3x
reduction in requests on top of that.

Relation pages are the second win: about 73,900 of them ride along inside detail responses
for free, with only overflow past `PS` needing a follow-up call.

## The word-family gap

`word-family` is the one relation type with no API path. It appears in `AIL` as the root and
its GUID (`a-sh-q`, `971ef1b6-…`) but never as a member list. `WordListingByCategory` with
`category=word-family` returns an empty `R` for both the word slug and the family GUID, and
no word-family listing call appears anywhere in the app's smali, so the app very likely does
not offer that screen at all.

Those 4,680 pages stay on the HTML crawl. This was not an exhaustive search of possible
`category` values, so a working string may exist.

## Confirmed, and not

Recorded 2026-08-04 against app version 1.1.10, in 12 requests. Endpoint paths and parameter
names come from the decompiled client; response shapes come from live responses.

Verified live: base URL, absence of auth, the three-script rotation across `lang=1` and
`lang=3`, all three language meaning blocks arriving in one call, shers differing by script,
all six relation `CT` values with their `PS` sizes, the `AIL` rows, direct audio URLs with a
GUID distinct from the word GUID, `pageIndex=0` clamping, `WordListingByCategory` page size 6
with no total, and that the full web slug fails while the stripped slug works.

Words sampled: `ishq` (rich: 3 languages, 6 relation groups, 6 shers), `warn`, `bhuchkaanaa`.

Unverified:

- Whether `search` has a result-count ceiling like Hindwi's 10,000. Not tested.
- Whether `lang=2` behaves symmetrically to `lang=1` and `lang=3`. Inferred from the rotation
  pattern, not directly tested.
- Whether `IL` and `VL` ever populate. Null on both words checked. Idioms already arrive as a
  relation group, so these may be legacy.
- Whether relation `W2`/`W3` are genuinely recoverable by joining on the entry GUID.
  Structurally sound, not verified with a fetch.
- Rate limits. Nothing observed in 12 requests, which proves nothing. Keep the crawl's
  existing pacing gate.
- Whether a `category` value exists that returns word-family members.
- Sufinama, which is a third backend and has been neither located nor tested.
