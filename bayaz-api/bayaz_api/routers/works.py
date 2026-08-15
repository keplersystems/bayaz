"""Works: the poems, couplets and prose, and the word positions a reader annotates them with."""

from itertools import groupby
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bayaz_api import db
from bayaz_api.listing import Filters, Pages, page
from bayaz_api.models import Page, Word, WorkDetail, WorkSummary, WorkWords

router = APIRouter(tags=["works"])

_SUMMARY = """
    w.site, w.slug, w.work_type, w.title, w.title_translit, w.title_hindi, w.title_urdu,
    w.author_name, e.slug AS author_slug
"""
_DETAIL = f"{_SUMMARY.strip()}, w.id, w.body, w.body_hindi, w.body_urdu, w.explanation, w.translation, w.source"
_SOURCE = "works w LEFT JOIN entities e ON e.id = w.author_id"


@router.get("/works", response_model=Page[WorkSummary])
def list_works(
    paging: Pages,
    site: Annotated[str | None, Query(description="rekhta, hindwi or sufinama")] = None,
    work_type: Annotated[str | None, Query(description="ghazals, nazms, stories, ...")] = None,
    author: Annotated[str | None, Query(description="`entities.slug` of the poet")] = None,
):
    filters = Filters()
    filters.add("w.site = ?", site)
    filters.add("w.work_type = ?", work_type)
    filters.add("w.author_id = (SELECT id FROM entities WHERE slug = ? LIMIT 1)", author)
    return page(WorkSummary, _SUMMARY, _SOURCE, "w.id", paging, filters)


# `{slug:path}` is greedy and 88,925 slugs contain slashes, so this route has to be declared
# before the work route or it is never reached.
@router.get("/works/{site}/{slug:path}/words", response_model=list[WorkWords])
def get_work_words(site: str, slug: str):
    """Word positions, grouped into lines and then into the script variants a work has.

    `lang` is the site's own variant id rather than a language code: that is what the source
    supplies, and mapping it would invent a fact the archive does not hold.
    """
    work_id = db.scalar("SELECT id FROM works WHERE site = ? AND slug = ?", (site, slug))
    if work_id is None:
        raise HTTPException(status_code=404, detail=f"no work {site}/{slug}")

    occurrences = db.rows(
        "SELECT lang, line_ord, word_ord, word, code FROM work_words"
        " WHERE work_id = ? ORDER BY lang, line_ord, word_ord",
        (work_id,),
    )
    return [
        WorkWords(
            lang=lang,
            lines=[
                [Word(line=row["line_ord"], ord=row["word_ord"], word=row["word"], code=row["code"]) for row in line]
                for _, line in groupby(variant, key=lambda row: row["line_ord"])
            ],
        )
        for lang, variant in groupby(occurrences, key=lambda row: row["lang"])
    ]


@router.get("/works/{site}/{slug:path}", response_model=WorkDetail)
def get_work(site: str, slug: str):
    found = db.row(f"SELECT {_DETAIL} FROM {_SOURCE} WHERE w.site = ? AND w.slug = ?", (site, slug))
    if found is None:
        raise HTTPException(status_code=404, detail=f"no work {site}/{slug}")
    fields = dict(found)
    work_id = fields.pop("id")
    return WorkDetail(
        **fields,
        tags=[tag for (tag,) in db.rows("SELECT tag FROM work_tags WHERE work_id = ? ORDER BY tag", (work_id,))],
        has_words=bool(db.scalar("SELECT EXISTS (SELECT 1 FROM work_words WHERE work_id = ?)", (work_id,))),
    )
