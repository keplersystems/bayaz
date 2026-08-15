"""Works: the poems, couplets and prose, and the word positions a reader annotates them with."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bayaz_api import db
from bayaz_api.models import Page, Word, WorkDetail, WorkSummary, WorkWords
from bayaz_api.pagination import Pages, where

router = APIRouter(tags=["works"])

_SUMMARY_COLUMNS = """
    w.site, w.slug, w.work_type, w.title, w.title_translit, w.title_hindi, w.title_urdu,
    w.author_name, e.slug AS author_slug
"""

_DETAIL_COLUMNS = f"""
    {_SUMMARY_COLUMNS.strip()},
    w.id, w.body, w.body_hindi, w.body_urdu, w.explanation, w.translation, w.source
"""

_FROM = " FROM works w LEFT JOIN entities e ON e.id = w.author_id"


@router.get("/works", response_model=Page[WorkSummary])
def list_works(
    paging: Pages,
    site: Annotated[str | None, Query(description="rekhta, hindwi or sufinama")] = None,
    work_type: Annotated[str | None, Query(description="ghazals, nazms, stories, ...")] = None,
    author: Annotated[str | None, Query(description="`entities.slug` of the poet")] = None,
    has_body: Annotated[bool | None, Query(description="only works whose text was captured")] = None,
):
    conditions, parameters = [], []
    if site:
        conditions.append("w.site = ?")
        parameters.append(site)
    if work_type:
        conditions.append("w.work_type = ?")
        parameters.append(work_type)
    if author:
        conditions.append("w.author_id = (SELECT id FROM entities WHERE slug = ? LIMIT 1)")
        parameters.append(author)
    if has_body is not None:
        keyword = "NOT NULL" if has_body else "NULL"
        conditions.append(f"coalesce(w.body, w.body_hindi, w.body_urdu) IS {keyword}")

    clause = where(conditions)
    total = db.scalar(f"SELECT count(*) FROM works w{clause}", parameters)
    rows = db.rows(
        f"SELECT {_SUMMARY_COLUMNS}{_FROM}{clause} ORDER BY w.id LIMIT ? OFFSET ?",
        [*parameters, paging.limit, paging.offset],
    )
    return Page(items=[WorkSummary(**dict(row)) for row in rows], total=total, limit=paging.limit, offset=paging.offset)


# `{slug:path}` is greedy and platform-site slugs genuinely contain slashes (88,925 of them),
# so the word route has to be declared before the work route or it is never reached.
@router.get("/works/{site}/{slug:path}/words", response_model=list[WorkWords])
def get_work_words(site: str, slug: str):
    """Word positions, grouped into lines and then into the script variants a work has.

    `lang` is the site's own variant id rather than a language code, because that is what
    the source supplies and mapping it would invent a fact the archive does not hold.
    """
    work_id = db.scalar("SELECT id FROM works WHERE site = ? AND slug = ?", (site, slug))
    if work_id is None:
        raise HTTPException(status_code=404, detail=f"no work {site}/{slug}")

    variants: dict[str, list[list[Word]]] = {}
    current: tuple[str, int] | None = None
    for row in db.rows(
        "SELECT lang, line_ord, word_ord, word, code FROM work_words"
        " WHERE work_id = ? ORDER BY lang, line_ord, word_ord",
        (work_id,),
    ):
        lines = variants.setdefault(row["lang"], [])
        if current != (row["lang"], row["line_ord"]):
            current = (row["lang"], row["line_ord"])
            lines.append([])
        lines[-1].append(Word(line=row["line_ord"], ord=row["word_ord"], word=row["word"], code=row["code"]))
    return [WorkWords(lang=lang, lines=lines) for lang, lines in variants.items()]


@router.get("/works/{site}/{slug:path}", response_model=WorkDetail)
def get_work(site: str, slug: str):
    row = db.row(f"SELECT {_DETAIL_COLUMNS}{_FROM} WHERE w.site = ? AND w.slug = ?", (site, slug))
    if row is None:
        raise HTTPException(status_code=404, detail=f"no work {site}/{slug}")
    fields = dict(row)
    work_id = fields.pop("id")
    tags = [tag for (tag,) in db.rows("SELECT tag FROM work_tags WHERE work_id = ? ORDER BY tag", (work_id,))]
    has_words = db.scalar("SELECT EXISTS (SELECT 1 FROM work_words WHERE work_id = ?)", (work_id,))
    return WorkDetail(**fields, tags=tags, has_words=bool(has_words))
