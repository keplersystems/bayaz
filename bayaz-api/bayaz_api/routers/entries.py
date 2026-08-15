"""The dictionary: headwords in three scripts, their senses, relations and example couplets."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bayaz_api import db
from bayaz_api.models import EntryDetail, EntrySummary, Page, Relation, Sense, Sher
from bayaz_api.pagination import Pages, where

router = APIRouter(tags=["dictionary"])

_COLUMNS = "site, slug, headword, headword_hindi, headword_urdu"


@router.get("/entries", response_model=Page[EntrySummary])
def list_entries(
    paging: Pages,
    site: Annotated[str | None, Query(description="rekhtadictionary, hindwi, rekhta or sufinama")] = None,
):
    conditions, parameters = ([], [])
    if site:
        conditions.append("site = ?")
        parameters.append(site)

    clause = where(conditions)
    total = db.scalar(f"SELECT count(*) FROM entries{clause}", parameters)
    rows = db.rows(
        f"SELECT {_COLUMNS} FROM entries{clause} ORDER BY id LIMIT ? OFFSET ?",
        [*parameters, paging.limit, paging.offset],
    )
    return Page(
        items=[EntrySummary(**dict(row)) for row in rows], total=total, limit=paging.limit, offset=paging.offset
    )


@router.get("/entries/lookup", response_model=EntrySummary)
def lookup_entry(code: Annotated[str, Query(description="a `code` from a work's word positions")]):
    """Resolve a word code to its entry, which is what a reader calls when a word is tapped.

    Only the poetry corpus carries codes that resolve: rekhta.org's own pages encode the
    same words differently, so prose recovered from the website returns 404 here by design
    rather than by omission.
    """
    row = db.row(f"SELECT {_COLUMNS} FROM entries WHERE slug = ? LIMIT 1", (code,))
    if row is None:
        raise HTTPException(status_code=404, detail=f"no entry for code {code}")
    return EntrySummary(**dict(row))


@router.get("/entries/{site}/{slug:path}", response_model=EntryDetail)
def get_entry(site: str, slug: str):
    row = db.row(
        f"SELECT id, {_COLUMNS}, vazn, trivia, audio_url, video_url FROM entries WHERE site = ? AND slug = ?",
        (site, slug),
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"no entry {site}/{slug}")
    fields = dict(row)
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
