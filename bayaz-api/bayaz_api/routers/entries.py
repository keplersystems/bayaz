"""The dictionary: headwords in three scripts, their senses, relations and example couplets."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bayaz_api import db
from bayaz_api.listing import Filters, Pages, page
from bayaz_api.models import EntryDetail, EntryGloss, EntrySummary, Page, Relation, Sense, Sher

router = APIRouter(tags=["dictionary"])

_COLUMNS = "site, slug, headword, headword_hindi, headword_urdu"


@router.get("/entries", response_model=Page[EntrySummary])
def list_entries(
    paging: Pages,
    site: Annotated[str | None, Query(description="rekhtadictionary, hindwi, rekhta or sufinama")] = None,
):
    filters = Filters()
    filters.add("site = ?", site)
    return page(EntrySummary, _COLUMNS, "entries", "id", paging, filters)


@router.get("/entries/lookup", response_model=EntryGloss)
def lookup_entry(code: Annotated[str, Query(description="a `code` from a work's word positions")]):
    """Resolve a word code to its entry and what it means.

    The senses come back with it because this is the tap-a-word route: the headword's three
    scripts are three spellings of the word the reader is already looking at, so a response
    without definitions answers nothing.

    Only rekhta's poetry codes resolve, all 262,030 of them. The 592,351 codes carried by
    hindwi and sufinama works match no entry, and neither does the prose recovered from
    rekhta.org's own pages, which encodes the same words differently. Those 404 by design.
    """
    found = db.row(f"SELECT id, {_COLUMNS} FROM entries WHERE slug = ? ORDER BY id LIMIT 1", (code,))
    if found is None:
        raise HTTPException(status_code=404, detail=f"no entry for code {code}")
    fields = dict(found)
    senses = db.rows(
        "SELECT lang, pos, definition FROM senses WHERE entry_id = ? ORDER BY lang, ord",
        (fields.pop("id"),),
    )
    return EntryGloss(**fields, senses=[Sense(**dict(row)) for row in senses])


@router.get("/entries/{site}/{slug:path}", response_model=EntryDetail)
def get_entry(site: str, slug: str):
    found = db.row(
        f"SELECT id, {_COLUMNS}, vazn, trivia, audio_url, video_url FROM entries WHERE site = ? AND slug = ?",
        (site, slug),
    )
    if found is None:
        raise HTTPException(status_code=404, detail=f"no entry {site}/{slug}")
    fields = dict(found)
    entry_id = fields.pop("id")

    senses = db.rows("SELECT lang, pos, definition FROM senses WHERE entry_id = ? ORDER BY lang, ord", (entry_id,))
    examples = db.rows("SELECT text FROM entry_examples WHERE entry_id = ? ORDER BY ord", (entry_id,))
    relations = db.rows(
        "SELECT rel_type, target_text, target_meaning FROM relations WHERE entry_id = ? ORDER BY rel_type, target_text",
        (entry_id,),
    )
    shers = db.rows("SELECT lines, lines_alt, poet FROM shers WHERE entry_id = ? ORDER BY ord", (entry_id,))

    return EntryDetail(
        **fields,
        senses=[Sense(**dict(row)) for row in senses],
        examples=[text for (text,) in examples],
        relations=[Relation(**dict(row)) for row in relations],
        shers=[Sher(**dict(row)) for row in shers],
    )
