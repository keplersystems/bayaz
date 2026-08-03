# Rekhta Poetry API

The JSON API behind rekhta.org's poetry corpus: poets, ghazals, nazms, couplets, and
recitation audio.

**Scope note.** rekhta.org is currently deferred in bayaz (see the README). This document
exists because the API was mapped opportunistically and the knowledge is perishable, not
because a crawl is planned. It does not help hindwi or sufinama; that was tested and is a
confirmed negative, see "What this does not cover".

Recorded 2026-08-04. Endpoint names and parameters are a mix of client transcription (from
Rekhta for Android 5.0.3, package `org.Rekhta`) and live verification. Every response shape
below was read off a live response.

## Provenance, and why this document exists

`GetPoetsListWithPaging`, the entry point to the entire corpus, **appears nowhere in the
decompiled client**. A tree-wide grep finds no reference to it. It is documented here
because it was recovered from a working scraper written in February 2025, and it still
returns 8,839 poets today.

That is the practical lesson for anything built on this API. `/rekhta-api/v1/` is a flat
handler namespace on the backend that resolves handler names regardless of which versioned
prefix a client happens to use. The current app calls these same handlers under
`/api/v7/shayari/` with JSON bodies; the v1 forms still work with query strings. So the v1
surface is **larger than any client**, cannot be enumerated by decompiling one, and absent
handler names hang for 25 seconds rather than returning 404, which makes probing expensive.

This is not a case of an abandoned path that happens to keep answering. The server's own
`AppConfig` handler declares `/rekhta-api/v1/` as the current content base in both `CU` and
`APU`, so v1 is advertised, not merely tolerated. What the client stopped using and what the
backend still considers current are two different things.

Endpoint names are therefore the scarce artifact. Treat this list as something to preserve
rather than rediscover.

## Calling convention

```bash
curl -sS -m 25 --http1.1 -X POST \
  -H 'Temptoken: <any UUID>' \
  -H 'User-Agent: Mozilla/5.0' \
  -H 'Content-Length: 0' \
  'https://app-rekhta.rekhta.org/rekhta-api/v1/<Endpoint>?param=value'
```

Four things that are easy to get wrong, each of which cost real time here:

1. **POST with parameters in the query string and an empty body.** Not a JSON body. This is
   what Python's `requests.post(url, params=...)` produces.
2. **`Content-Length: 0` is mandatory.** Without it the server returns a fast HTTP 411.
   `requests` sets it automatically; curl does not.
3. **Only `Temptoken` and `User-Agent` are needed.** `Temptoken` is a client-generated UUID
   with no server-side registration, so any UUID works. No `Authorization`, and explicitly
   **no `ClientId` or `ClientSecret`**: the current app hardcodes such a pair, but these
   endpoints do not require it, so there is no credential of theirs to reuse.
4. **Use `--http1.1` for large responses.** The corpus-wide calls abort the HTTP/2 stream
   otherwise.

### The hang

A missing required parameter, or an absent handler name, causes the server to **hang for 25
to 47 seconds and then cancel the stream**. It does not return an error. This is the same
behaviour documented as the `wordId` gotcha in
[hindwi-dictionary-api.md](hindwi-dictionary-api.md), so it is a house pattern across
Rekhta's stack rather than a quirk of one endpoint.

Consequences: always pass the full parameter set including empty ones, always use `-m`, and
never probe for handler names in bulk. Each miss holds a connection on their origin for the
better part of a minute, which is worse for them than a successful request.

## Envelope

```json
{"S": 1, "Me": null, "Mh": null, "Mu": null, "R": <payload>, "T": "<server time +05:30>"}
```

Identical to both dictionary APIs. `S: 1` is success. `S: 0` with `R: null` and no message is
a rejection, which is how a bad `lastFetchDate` presents (see below).

`lang`: 1 = English, 2 = Hindi, 3 = Urdu. Page size is **50** everywhere, and `R.TC` carries
a genuine total, unlike the dictionary APIs where the equivalent saturated at 10,000.

## The verb rule, read this first

**Some handlers are GET and some are POST, and calling one with the wrong verb produces the
same 25-second hang as a missing parameter.** There is no error, so a verb mismatch is
indistinguishable from a nonexistent handler unless you know the rule.

This cost real time here. `GetContentById` was written off as "absent under v1" after being
probed as POST. It is a GET, it has always worked, and it returns the full text of every
poem in the corpus. Before concluding any handler is missing, retry it with the other verb.

The authority is the 2.2.6 client, which declares `REQUEST_TYPE.GET` or `POST` per handler.
The table below records the verb for each.

## Endpoints

Verified means HTTP 200 with real data on 2026-08-04.

| Endpoint | Verb | Parameters | Payload | Status |
|---|---|---|---|---|
| `AppConfig` | GET | none | `R` | verified |
| `GetContentById` | **GET** | `contentId` `lang` | `R.CR` | **verified, full poem text** |
| `GetCountingSummaryByTargetId` | **GET** | `targetId` | `R` | verified |
| `GetBottomContentByIdSlug` | GET | `contentId` `lang` `listSlug` | `R` | verified |
| `GetContentTypeTabByType` | GET | `lang` `targetIdSlug` `targetType` | `R` | verified |
| `GetAppUrl` | GET | `lang` | `R` | verified |
| `GetStreamingListByType` | GET | none | `R` | verified |
| `GetYouTubeKey` | GET | none | `R` | verified, see warning below |
| `GetPoetsListWithPaging` | POST | `lastFetchDate` `targetId` `pageIndex` `keyword` | `R.P[]` | verified |
| `GetContentTypeList` | POST | `lastFetchDate` | `R[]` | verified, **filters** |
| `GetContentListWithPaging` | POST | `poetId` `targetId` `contentTypeId` `sortBy` `pageIndex` `keyword` `lang` | `R.CS[]` | verified |
| `GetCoupletListWithPaging` | POST | `poetId` `targetId` `contentTypeId` `sortBy` `pageIndex` `keyword` `lang` | `R.CD[]` | verified |
| `GetAudioListByPoetIdWithPaging` | POST | `poetId` `keyword` `pageIndex` | `R.A[]` | verified |
| `GetVideoListByPoetIdWithPaging` | POST | `poetId` `keyword` `pageIndex` | `R` | verified |
| `GetPoetCompleteProfile` | POST | `poetId` `lang` | `R.{CH,EP,SS,PR,UL,CS}` | verified |
| `GetPoetProfile` | POST | `poetId` `lang` | `R` | verified |
| `GetTagsList` | POST | `lang` | `R` | verified, whole taxonomy, no paging |
| `GetTagsListWithTrendingTag` | POST | `lang` | `R` | verified |
| `GetExplore` | POST | `lang` | `R` | verified |
| `GetHomePageCollection` | POST | `lang` `lastFetchDate` | `R` | verified |
| `GetOccasionList` | POST | `lang` | `R` | verified |
| `GetT20` | POST | none | `R` | verified |
| `WordOfTheDay` | POST | `displayDate` | `R` | verified |
| `SearchAllByType` | POST | `keyword` `lang` `type` | `R` | verified |
| `GetShayariImagesWithSearch` | POST | `keyword` `lang` `targetIdSlug` `targetType` | `R` | verified, `TC` 3027 |
| `GetShayariImageById` | POST | `lang` `shayariImgId` `shayariIngId` `targetIdSlug` | `R` | verified |
| `GetWordMeaningByLang` | POST | `lang` `selectedWord` `word` | `R` | verified |
| `GetGroupWordMeaningByLang` | POST | `lang` `selectedWord` `word` | `R` | verified |
| `GetPlattsDictionaryMeanings` | POST | `keyword` | `R` | verified |
| `GetRekhtaDictionaryMeanings` | POST | `keyword` `lang` | `R` | live, returned null; params wrong |
| `GetContentTypeTabByCollectionType` | POST | `collectionType` | `R` | verified |
| `GetCollectionListByCollectionType` | POST | `collectionType` `contentTypeId` `keyword` `lang` | | **fails**, param combination unknown |
| `AppInfo` | POST | `deviceType` | `R` | verified |
| `GetImageDictionaryMeanings` | POST | `keyword` | | transcription only |

User-scoped or write endpoints, transcribed but deliberately not called:
`DeviceRegisterForPush`, `GetUserSettings`, `SetUserSetting`, `Critique`, `UserAppInfo`,
`GetAllFavoriteId`, `GetAllFavoriteListWithPaging`, `GetFavoriteListWithPaging`,
`GetFavoriteListContentWithPaging`, `GetFavoriteListWithSpecificContent`, `MarkAllFavorite`,
`RemoveAllFavorite`, `RemoveAllFavoriteListByType`.

Two sibling namespaces on `world.rekhta.org`, all user-scoped and untouched:
`api/V5_ApiAccount/` (Login, Register, ForgotPassword, DeleteProfile and so on) and
`api/v1/forum/` (GetAllCommentsByTargetId, GetReplyByParentId, SetUserComments,
MarkLikeDislike, SetUserComplain and so on). The forum surface is entirely unexplored.

> **Do not use `GetYouTubeKey`.** It returns a live Google API key in plaintext to any
> unauthenticated caller. That is Rekhta's key and their billing. It is recorded here as a
> finding, not as a capability.

Client-hardcoded values seen in transcription: `deviceType=android`, `host=rekhta`,
`sourceRef=rekhta-plus-app`. Note that `host`, `UserId`, and `Authorization` are **headers**
in the client, not query parameters.

### `poetId` and `targetId` are not interchangeable

On both paging endpoints, set `poetId` and leave `targetId` **empty**. Setting both to the
same GUID returns `TC: 0`. `targetId` is a tag or entity id, not a content id, and passing a
content id there returns `TC: 0` as well.

### `AppConfig`, the server's own topology

Takes no parameters, returns instantly rather than hanging, and is therefore the cheapest
liveness check against this host.

```
GET/POST https://app-rekhta.rekhta.org/rekhta-api/v1/AppConfig
```

```json
{"WU": "https://world.rekhta.org",
 "CU": "https://app-rekhta.rekhta.org/rekhta-api/v1/",
 "MU": "https://rekhta.pc.cdn.bitgravity.com",
 "AU": "https://world.rekhta.org/api/V5_ApiAccount/",
 "FU": "https://world.rekhta.org/api/v1/forum/",
 "APU": "https://app-rekhta.rekhta.org/rekhta-api/v1/",
 "IC": false, "EORC": 3}
```

Two things follow from this.

**`CU` and `APU` both declare `/rekhta-api/v1/` as the current content base.** So v1 is not a
legacy path that merely still answers; it is what the server advertises to clients, even
though the 5.0.3 app calls content handlers under `/api/v6|v7/shayari/` instead. That is a
materially better footing for anything built on it.

**`MU` names a media host we have not used**, `rekhta.pc.cdn.bitgravity.com`, which matches
the audio CDN recorded during the 2026-08-03 HTML recon. The audio URLs returned by
`GetAudioListByPoetIdWithPaging` are on `www.rekhta.org/Images/SiteImages/Audio/` instead, so
there are two media hosts and the bulk audio job should establish which to prefer.

`FU` exposes a forum API at `world.rekhta.org/api/v1/forum/` that none of this work has
touched. Unexplored.

## Content types and the routing rule

`GetContentTypeList` returns 67 types, each with `I` (GUID), `NE`/`NH`/`NU` (name in three
scripts), `SS` (slug), `S` (sort order), `DM` (modified timestamp), `LT`, and `CT`.

**`LT` selects which endpoint serves that type.** This is the rule to encode:

| `LT` | Types | Endpoint |
|---|---|---|
| `2` | Doha, Quote, Sher (the fragment types) | `GetCoupletListWithPaging` |
| `1` | the other 64 whole-content types | `GetContentListWithPaging` |

`CT` splits poetry (51 types) from prose (16: Novel, Drama, Letter, Article, Short story and
so on).

Common GUIDs: SHER `f722d5dc-45da-41ec-a439-900df702a3d6`, GHAZAL
`43d60a15-0b49-4caf-8b74-0fcdddeb9f83`, NAZM `c54c4d8b-7e18-4f70-8312-e1c2cc028b0b`.

The `DM` timestamps are real and span 2014-07-15 to 2026-06-18. They are exposed as data on
content types only, never on poet or content rows.

## Corpus-wide enumeration

`GetContentListWithPaging` with **`poetId` empty** returns the entire corpus for a content
type, ordered by popularity. Verified: nazms give `TC = 14424`, 50 per page, 16 distinct
poets on page one, in about 12 seconds.

Two caveats:

- **`PI` (poet id) is null in corpus-wide mode**, on all 50 items. `PE`/`PH`/`PU` still carry
  the poet's name, and the slug `S` embeds it, so the poet is recoverable but not by id.
- The same trick on `GetCoupletListWithPaging` **hangs**. Couplets cannot be enumerated
  corpus-wide and must be walked per poet.

So there are two viable enumeration strategies: per poet via the 8,839-row poet list, or
per content type corpus-wide for everything except fragments.

## Field naming system

Almost every field is two or three letters. There is a system, and knowing it removes most
of the guesswork.

**The trailing letter is the language.** A field ending `E`, `H`, or `U` is the same value in
three renderings:

| Suffix | Language | Script | Example (`NE`/`NH`/`NU`) |
|---|---|---|---|
| `E` | English | Roman transliteration | `Mirza Ghalib` |
| `H` | Hindi | Devanagari | `मिर्ज़ा ग़ालिब` |
| `U` | Urdu | Nastaliq | `مرزا غالب` |

These are **not** translations of each other. `E` is a romanised transliteration of the same
Urdu text, not an English translation. Store all three; they are the point of the corpus.

**The leading letters are the field.** Confirmed prefix families:

| Prefix | Meaning | Triple |
|---|---|---|
| `N` | Name | `NE` `NH` `NU` |
| `T` | Title | `TE` `TH` `TU` |
| `P` | Poet name | `PE` `PH` `PU` |
| `D` | Description | `DE` `DH` `DU` |
| `L` | Location | `Le` `Lh` `Lu` (**lowercase suffix**, the one exception) |
| `U` | URL, short permalink | `UE` `UH` `UU` |
| `S` | Subtitle | `SE` `SH` `SU` (empty on every sample) |
| `A` | Artist / reciter name | `AE` `AH` `AU` (audio records only) |
| `R` | Rendered text tree | `RE` `RH` `RU` (couplets only) |
| `SP` | unknown, poet records | `SPE` `SPH` `SPU` (empty on every sample) |
| `FT` | unknown | `FTE` `FTH` `FTU` (null on every sample) |
| `HF` | unknown boolean | `HFE` `HFH` `HFU` (false on every sample) |
| `CA` | unknown boolean | `CAE` `CAH` `CAU` (false on every sample) |

The short permalinks follow a fixed pattern: `UE` is the base, `UH` is the same id with `/2`,
`UU` with `/3`. So `https://rek.ht/a/0z5a`, `/0z5a/2`, `/0z5a/3`.

### Hazard: the same abbreviation means different things in different records

This is the single biggest trap when writing a parser. Key on the record type, never on the
field name alone.

| Field | In this record | Means |
|---|---|---|
| `CS` | poet (`R.P[]`) | **content summary**, a list of per-type counts |
| `CS` | `GetContentById` `R` | **content slug**, a string |
| `CS` | `Poet` sub-object | **poet slug**, a string |
| `CT` | content type (`GetContentTypeList`) | **category type**, int: 1 poetry, 2 prose |
| `CT` | `GetContentById` `R` | **content title**, transliterated string |
| `TS` | couplet (`R.CD[]`) | **tag list**, an array of tag objects |
| `TS` | `GetContentById` `R` | **type slug**, e.g. `ghazals` |
| `TS` | `Tags[]` sub-object | **tag slug**, e.g. `jagjit-singh` |
| `T` | content / couplet | **content type GUID** |
| `T` | tag object in `TS[]` | an int, purpose unknown |
| `S` | content / couplet | **slug**, a long string |
| `S` | content type | **sort order**, an int |
| `S` | audio (`R.A[]`) | **sequence**, an int |
| `SC` | poet | **sher count** |
| `SC` | content / `GetContentById` | `0` or `''`, purpose unknown |
| `AU` | content (`R.CS[]`) | **has audio**, boolean |
| `AU` | audio record, `Audios[]` | an **audio URL** |
| `AU` | poet audio (`R.A[]`) | **reciter name in Urdu** |
| `P` | poet record | boolean, unknown |
| `P` | content / couplet | null on every sample |
| `P` | inside a `CR` tree | **stanza** (paragraph) |
| `FC` | list records | favourite count, **int** (`21023`) |
| `FC` | `GetContentById` | favourite count, **formatted string** (`'22.6K'`) |

## Response shapes

Every field below was read from a live response. Where a meaning is marked *inferred* it is
read from context; *unknown* means the field was present but its purpose could not be
established from the samples.

### `R.P[]`, poet (from `GetPoetsListWithPaging`)

| Field | Type | Meaning |
|---|---|---|
| `I` | GUID | poet id, the `poetId` for every other call |
| `NE` `NH` `NU` | string | name, three scripts |
| `SL` | string | slug, e.g. `a-g-josh` |
| `DF` | string | date from, birth year |
| `DT` | string | date to, death year |
| `Le` `Lh` `Lu` | string | birthplace, three scripts (lowercase suffix) |
| `DE` `DH` `DU` | string | description, three scripts (empty on most poets) |
| `GC` | int | **ghazal count** |
| `NC` | int | **nazm count** |
| `SC` | int | **sher count** |
| `HI` | bool | has image |
| `P` | bool | unknown |
| `N` | bool | unknown |
| `SPE` `SPH` `SPU` | string | unknown, empty on every sample |
| `CS` | array | content summary, one row per content type the poet has |

`GC`/`NC`/`SC` are confirmed rather than guessed: for `A G Josh`, `GC=18` and `SC=7` match
exactly the `Ghazal` count 18 and `Sher` count 7 in that poet's own `CS` array.

`CS[]` item, which is what makes a per-poet crawl plan possible without probing:

| Field | Type | Meaning |
|---|---|---|
| `I` | GUID | content type id, pass as `contentTypeId` |
| `TN` | string | type name, e.g. `Ghazal` |
| `TS` | string | type slug, e.g. `ghazals` |
| `C` | int | how many the poet has of this type |
| `S` | int | sort order |
| `LT` | int | listing type, selects the endpoint (see routing rule) |
| `CT` | int | 1 poetry, 2 prose |

### `R.CS[]`, whole content (from `GetContentListWithPaging`)

| Field | Type | Meaning |
|---|---|---|
| `I` | GUID | content id, the `contentId` for `GetContentById` |
| `T` | GUID | content type id |
| `PI` | GUID | poet id. **null in corpus-wide mode** |
| `PE` `PH` `PU` | string | poet name, three scripts |
| `TE` `TH` `TU` | string | title, three scripts |
| `SE` `SH` `SU` | string | subtitle, empty on every sample |
| `BE` `BH` `BU` | null | body. **Always null here**, use `GetContentById` |
| `S` | string | slug, with poet name and type appended |
| `SI` | int | legacy numeric id, e.g. `35550` |
| `R` | string | radeef (the ghazal refrain) then a comma then the Urdu title (*inferred*) |
| `UE` `UH` `UU` | string | short permalinks |
| `PP` | float | popularity score, e.g. `190905.0` |
| `FC` | int | favourite count |
| `LC` | string/null | favourite count preformatted, e.g. `4.5K` |
| `AU` | bool | has audio |
| `VI` | bool | has video |
| `AC` | int | audio count |
| `VC` | int | video count |
| `LI` | int | unknown |
| `SC` | int | unknown, `0` on every sample |
| `N` `EC` `PC` | bool | unknown |
| `HE` `HH` `HU` | bool | unknown, false on content, true on couplets |
| `CAE` `CAH` `CAU` | bool | unknown, false on every sample |
| `FTE` `FTH` `FTU` | null | unknown |
| `HFE` `HFH` `HFU` | bool | unknown, false on every sample |

### `R.CD[]`, couplets (from `GetCoupletListWithPaging`)

Shares the poet, title, slug, permalink, and counter fields above. Additionally:

| Field | Type | Meaning |
|---|---|---|
| `RE` `RH` `RU` | string | **the couplet text**, a JSON-encoded tree, see below |
| `TS` | array | tag objects, `{I, NE, NH, NU, S (slug), T (int, unknown)}` |
| `A` | int | unknown, `1` on sample |
| `RF` | int | unknown, `0` on sample |
| `IJ` | bool | unknown |
| `IH` | bool | is HTML |
| `HT` | bool | unknown |

### The text tree, in `RE`/`RH`/`RU` and in `CR`

These are **JSON-encoded strings, not objects**. Decode the string, then walk it:

```json
{"P": [{"L": [{"W": [{"M": "\\1nn2", "W": "hazāroñ", "S": "hazaron"},
                     {"M": "\\12od", "W": "ḳhvāhisheñ", "S": "khvaahishen"}]}]}],
 "CH": "", "CTH": "", "TT": false}
```

| Key | Level | Meaning |
|---|---|---|
| `P` | root | **stanzas** (paragraphs). A ghazal has one entry per couplet |
| `L` | stanza | **lines** |
| `W` | line | **words** |
| `W` | word | surface form in the requested script |
| `S` | word | plain roman transliteration, no diacritics |
| `M` | word | **dictionary word code**, resolvable, see below |
| `CH` `CTH` | root | unknown, empty on every sample |
| `TT` | root | unknown, false on every sample |

Rejoin a line by joining its `W[].W` values with spaces. Each script has its own independent
tree, so `RE` is not a transliteration generated from `RU`; both are stored.

### `R.A[]`, audio (from `GetAudioListByPoetIdWithPaging`)

| Field | Type | Meaning |
|---|---|---|
| `I` | GUID | audio id, and the filename stem of the media URL |
| `CI` | GUID | parent content id |
| `TI` | GUID | content type id |
| `PI` | GUID | poet id |
| `NE` `NH` `NU` | string | poet name, three scripts |
| `PS` | string | poet slug |
| `PSN` | string | poet name, lowercased |
| `TE` `TH` `TU` | string | content title, three scripts |
| `CS` | string | content slug |
| `AI` | GUID | artist (reciter) id |
| `AE` `AH` `AU` | string | reciter name, three scripts |
| `AS` | string | reciter slug |
| `ASN` | string | reciter name, lowercased |
| `AD` | string | duration, `HH:MM:SS` |
| `AMF` | URL | **mp3** |
| `AOF` | URL | **ogg** |
| `HA` `HP` | bool | unknown |
| `AIU` `PIU` `FAB` | null | unknown, artist and poet image URLs (*inferred*) |
| `S` | int | sequence |
| `ST` | null | unknown |
| `IL` `IB` | bool | unknown |
| `LC` `BC` | int | unknown |

Media URLs are both returned and derivable, since the stem is the item's own `I`:

```
https://www.rekhta.org/Images/SiteImages/Audio/{I}.mp3
https://www.rekhta.org/Images/SiteImages/Audio/{I}.ogg
```

Note the path is `Audio/`, distinct from the dictionaries' `DictionaryAudio/` and
`HindwiDictionaryAudio/`, and the GUID is **lowercase** here where the dictionaries use
uppercase. Content and couplet rows carry only flags and counts, never URLs, so audio
requires this endpoint or `GetContentById`.

### `GetContentById` `R`, the full record

| Field | Type | Meaning |
|---|---|---|
| `I` | GUID | content id |
| `SI` | int | legacy numeric id |
| `TI` | GUID | content type id |
| `CTN` | string | content type name, e.g. `Ghazal` |
| `TS` | string | content type slug, e.g. `ghazals` |
| `CS` | string | content slug |
| `CT` | string | content title, transliterated |
| `ST` `FT` | string | unknown, empty on sample |
| `CR` | string | **the full text tree**, JSON-encoded |
| `RFP` | string | first paragraph, same tree format |
| `IH` | string | is HTML, the **string** `"false"` for all poetry |
| `UE` `UH` `UU` | string | short permalinks |
| `FC` | string | favourite count, **preformatted** e.g. `22.6K` |
| `TN` | string | translator/contributor name, e.g. `Sanjiv Saraf` (*inferred*) |
| `CTS` | string | that contributor's slug |
| `TD` | string | unknown, empty |
| `Poet` | object | see below |
| `Audios` | array | see below |
| `Videos` | array | see below |
| `Tags` | array | `{TI (id), TN (name), TS (slug)}` |
| `FPMappings` `FPParaMappings` `ParaInfo` | array | unknown, first-para mappings (*inferred*) |
| `Banner` `VideoList` | null | unknown |
| `HN` `HH` `HU` `HT` | bool | unknown, all true on sample |
| `LT` `RF` `RA` `LI` | int | unknown |
| `DT` `IJ` `NF` `EC` `PC` `IsPopular` | bool | unknown |
| `AS` `ATS` `P` `PT` `PS` `PTS` | null | unknown |
| `SC` | string | unknown, empty |
| `Rating` | int | `0` on sample |
| `HFE` `HFH` `HFU` | bool | unknown |

`Poet` sub-object: `PI` poet id, `PN` poet name, `CS` poet slug, `IU` round image URL, `DS`
unknown (empty), `LI` bool unknown.

`Audios[]` item: `I` audio id, `AN` reciter name, `ASS` reciter slug, `IU` reciter image,
`AMF`/`AOF` mp3 and ogg, `AU` a third URL form with an **uppercase** GUID, `SQ` sequence,
`HI` has image, `AD` `ADS` `AT` unknown.

`Videos[]` item: `YI` **YouTube video id**, `VT` video title, `AN` performer name, `ASS`
performer slug, `IU` performer image, `AU` a rekhta.org performer page URL (note it is
malformed as `https:rekhta.org//poets/...`), `SQ` sequence, `HI` has image, `ST` `ADS`
unknown.

### `GetContentTypeList` `R[]`, content types

| Field | Type | Meaning |
|---|---|---|
| `I` | GUID | content type id |
| `NE` `NH` `NU` | string | type name, three scripts |
| `SS` | string | slug, e.g. `afsanche` |
| `S` | int | sort order |
| `DM` | timestamp | **date modified**, the field `lastFetchDate` filters on |
| `LT` | int | listing type, `1` whole content, `2` fragment |
| `CT` | int | `1` poetry (51 types), `2` prose (16 types) |

### Resolving `M` word codes

Each word in a text tree carries `M`, e.g. `\1nn2` (a literal backslash, so it appears as
`\\1nn2` in raw JSON and must be URL-encoded as `%5C1nn2`).

```bash
curl -sS -m 25 --http1.1 -X POST \
  -H 'Temptoken: <UUID>' -H 'User-Agent: Mozilla/5.0' -H 'Content-Length: 0' \
  'https://app-rekhta.rekhta.org/rekhta-api/v1/GetWordMeaningByLang?lang=1&word=%5C1nn2&selectedWord=hazaron'
```

Returns the dictionary entry for that exact word: forms in three scripts, English, Hindi and
Urdu meanings, and mp3/ogg pronunciation URLs. `GetGroupWordMeaningByLang` takes the same
parameters and handles compound forms.

This is what makes the corpus word-level annotated: every word of every poem joins to a
dictionary entry and its audio.

## `lastFetchDate`: a real filter on one endpoint, a failure switch elsewhere

Behaviour is per endpoint, which is why it looked broken at first.

**`GetContentTypeList` genuinely filters.** Verified by count:

| `lastFetchDate` | `S` | items | oldest `DM` returned |
|---|---|---|---|
| (empty) | 1 | 67 | `2014-07-15T16:24:26.513` |
| `2020-01-01` | 1 | 55 | `2020-11-05T14:19:33.32` |
| `2024-01-01` | 1 | 41 | `2024-08-07T12:12:53.093` |

Exactly the records with `DM` older than the cutoff are dropped and nothing older than the
cutoff comes back. Plain `YYYY-MM-DD` is enough; the full
`2020-01-01T00:00:00.0000000+05:30` form is accepted and equivalent. The natural cursor to
feed back is the envelope's own `T`, which is the server's clock in that format.

**Everywhere else it does not work.** `GetPoetsListWithPaging` returns `{"S": 0, "R": null}`
for any non-empty value, and `GetCoupletListWithPaging` and `GetHomePageCollection` accept
the parameter and ignore it, returning byte-identical responses. On those, pass it empty.

So this is a **reference-data delta, not a content delta**. It tells you when a content type
changed, not when a poem did. Content-level delta still has to be client-side diffing on
content ids.

Worth noting how this was found: the 2.2.6 client hardcodes `lastFetchDate=""` at all six of
its call sites, so the old client never revealed the format either. It was found by feeding
the envelope's own `T` shape back in. The parameter has presumably worked this whole time
with no client exercising it.

## Full poem text: `GetContentById`

The whole corpus is reachable in one GET per poem.

```bash
curl -sS -m 25 --http1.1 -X GET \
  -H 'Temptoken: <any UUID>' -H 'User-Agent: Mozilla/5.0' \
  'https://app-rekhta.rekhta.org/rekhta-api/v1/GetContentById?contentId=<GUID>&lang=1'
```

Verified: Ghalib's `hazāroñ ḳhvāhisheñ aisī`
(`7bb5d7aa-2cc6-4375-89bd-e02dbd55c30c`) returns all 9 couplets in 0.48 s / 22 KB.
Confirmed across ghazal, nazm and sher, and across all three `lang` values.

The body is **not** in `BE`/`BH`/`BU`, which do not exist on this response. It is in **`CR`**,
a JSON-encoded stanza/line/word tree in the same format the couplet endpoint uses. `lang`
switches the script of the whole tree. Full field list under
[`GetContentById` `R`](#getcontentbyid-r-the-full-record); tree format under
[The text tree](#the-text-tree-in-rerhru-and-in-cr).

The response also inlines `Poet`, `Audios`, `Videos` and `Tags`, so one call gets the poem,
its poet, its recitations, its YouTube performances, and its tags together. The verified
Ghalib call returned 2 audio and 4 video joins alongside the text.

Because each word carries a resolvable `M` code, the corpus is **word-level annotated**: every
word of every poem joins to a dictionary entry and its pronunciation audio. That connects
this corpus to the one in [rekhta-dictionary-api.md](rekhta-dictionary-api.md) and is a
considerably better artifact than plain text.

## What this does not cover

hindwi.org and sufinama.org. This was tested rather than assumed: no `hindwi` or `sufinama`
string appears anywhere in the client, the only property-scoping parameter (`WebsiteId`) is
hardcoded to `1` and appears only on user-scoped writes, and passing `host=rekhta`,
`host=hindwi`, and `host=sufinama` to a reachable endpoint returned byte-identical payloads,
so `host` is ignored. Nothing here reaches hindwi's 64,717 works and entities or sufinama's
107,565.

## Where the handler list came from

The 2.2.6 client (`org.Rekhta` versionCode 10662, source package `com.example.sew`, not
obfuscated) calls 46 handlers plus `AppConfig` against `CU`, which by its own `AppConfig`
response **is** `/rekhta-api/v1/`. So that list is the literal v1 set for that generation
rather than an inference.

Diffed against 5.0.3, **30 handlers exist in 2.2.6 and are absent from the current client**,
including `AppConfig`, `GetPoetsListWithPaging`, `GetTagsList`, `GetExplore`,
`GetHomePageCollection`, `GetOccasionList`, `GetT20`, `WordOfTheDay`, `GetStreamingListByType`,
`GetVideoListByPoetIdWithPaging`, `GetWordMeaningByLang`, `GetPlattsDictionaryMeanings` and
`GetYouTubeKey`. All of them still answer.

Two of those, `GetPoetProfile` and `GetTagsList`, are constants in 2.2.6 that **no 2.2.6 code
path ever calls**. They were dead constants in a five-year-old client, and both work live
today.

18 handlers appear in both generations. 25 exist only in 5.0.3 and are the v6/v7-era
additions: feed, onboarding, follow graph, and tag-scoped browsing.

The practical consequence is the one already stated at the top: handler names are the scarce
artifact. An old client is a better source for them than a new one, and neither is complete.

## Confirmed, and not

Verified live on 2026-08-04, across roughly 75 requests including the subagent runs: the
calling convention and the 411 without `Content-Length`, the hang on both missing parameters
and wrong verbs, every endpoint marked verified in the table, full poem text via
`GetContentById` as a GET, `M` word codes resolving to dictionary entries, page size 50,
`TC` totals (8,839 poets; Ghalib with 397 couplets, 233 ghazals, 82 audio, 307 videos),
corpus-wide nazm enumeration at `TC=14424` with null `PI`, `lastFetchDate` filtering on
`GetContentTypeList` and only there, and `sortBy` changing order (`0` popularity,
`1` alphabetical) without changing `TC`.

Unverified or unknown:

- `GetCollectionListByCollectionType`. Three attempts, two 25 s timeouts and one server-side
  TLS abort, across `collectionType` 1 and 2. The handler is real and the parameter names are
  certain from source, but the working combination is unknown. This is the collection
  browsing surface and is worth one more look.
- `GetRekhtaDictionaryMeanings` returns `R: null` for a plain keyword, so its parameters are
  wrong rather than the handler being absent.
- `targetType` enum values. `1` returns empty on both `GetContentTypeTabByType` and
  `GetShayariImagesWithSearch`, so the mapping is not what it appears.
- What other handler names exist. The namespace is larger than any single client, and misses
  hang, so it cannot be enumerated safely by probing.
- Whether `sortBy` accepts values above 1.
- Rate limits. Nothing observed across roughly 75 requests, which is still far too small a
  sample to conclude anything.
- The `world.rekhta.org/api/v1/forum/` surface, entirely unexplored.
