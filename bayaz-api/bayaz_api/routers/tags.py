"""Tags: the sites' own subject index over works."""

from typing import Annotated

from fastapi import APIRouter, Query

from bayaz_api import db
from bayaz_api.listing import Filters, Pages, page
from bayaz_api.models import Page, TagSummary, WorkSummary

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=Page[TagSummary])
def list_tags(paging: Pages, site: Annotated[str | None, Query(description="restrict to one site")] = None):
    # Grouped rather than filtered, so this is the one listing `page()` cannot express.
    source = "work_tags t JOIN works w ON w.id = t.work_id" if site else "work_tags t"
    clause = " WHERE w.site = ?" if site else ""
    parameters = [site] if site else []

    total = db.scalar(f"SELECT count(DISTINCT t.tag) FROM {source}{clause}", parameters)
    found = db.rows(
        f"SELECT t.tag, count(*) works FROM {source}{clause}"
        " GROUP BY t.tag ORDER BY works DESC, t.tag LIMIT ? OFFSET ?",
        [*parameters, paging.limit, paging.offset],
    )
    return Page(
        items=[TagSummary(**dict(row)) for row in found],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.get("/tags/{tag}/works", response_model=Page[WorkSummary])
def get_tag_works(tag: str, paging: Pages):
    filters = Filters()
    filters.add("t.tag = ?", tag)
    columns = (
        "w.site, w.slug, w.work_type, w.title, w.title_translit, w.title_hindi, w.title_urdu,"
        " w.author_name, e.slug AS author_slug"
    )
    source = "work_tags t JOIN works w ON w.id = t.work_id LEFT JOIN entities e ON e.id = w.author_id"
    return page(WorkSummary, columns, source, "w.id", paging, filters)
