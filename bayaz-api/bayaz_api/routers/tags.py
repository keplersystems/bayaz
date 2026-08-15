"""Tags: the sites' own subject index over works."""

from typing import Annotated

from fastapi import APIRouter, Query

from bayaz_api import db
from bayaz_api.models import Page, TagSummary, WorkSummary
from bayaz_api.pagination import Pages

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=Page[TagSummary])
def list_tags(paging: Pages, site: Annotated[str | None, Query(description="restrict to one site")] = None):
    join = " JOIN works w ON w.id = t.work_id WHERE w.site = ?" if site else ""
    parameters = [site] if site else []
    total = db.scalar(f"SELECT count(DISTINCT t.tag) FROM work_tags t{join}", parameters)
    rows = db.rows(
        f"SELECT t.tag, count(*) c FROM work_tags t{join} GROUP BY t.tag ORDER BY c DESC, t.tag LIMIT ? OFFSET ?",
        [*parameters, paging.limit, paging.offset],
    )
    return Page(
        items=[TagSummary(tag=tag, works=count) for tag, count in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


@router.get("/tags/{tag}/works", response_model=Page[WorkSummary])
def get_tag_works(tag: str, paging: Pages):
    total = db.scalar("SELECT count(*) FROM work_tags WHERE tag = ?", (tag,))
    rows = db.rows(
        "SELECT w.site, w.slug, w.work_type, w.title, w.title_translit, w.title_hindi, w.title_urdu,"
        "       w.author_name, e.slug AS author_slug"
        " FROM work_tags t JOIN works w ON w.id = t.work_id LEFT JOIN entities e ON e.id = w.author_id"
        " WHERE t.tag = ? ORDER BY w.id LIMIT ? OFFSET ?",
        (tag, paging.limit, paging.offset),
    )
    return Page(items=[WorkSummary(**dict(row)) for row in rows], total=total, limit=paging.limit, offset=paging.offset)
