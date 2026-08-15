"""Poets and the other contributor types the sites distinguish: authors, translators,
editors, publishers, artists, contributors."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bayaz_api import db
from bayaz_api.models import EntityDetail, EntitySummary, Page, WorkSummary
from bayaz_api.pagination import Pages, where

router = APIRouter(tags=["poets"])

_COLUMNS = "site, slug, entity_type, name, name_hindi, name_urdu, name_translit, born, died"


@router.get("/poets", response_model=Page[EntitySummary])
def list_poets(
    paging: Pages,
    site: Annotated[str | None, Query(description="rekhta, hindwi or sufinama")] = None,
    entity_type: Annotated[str | None, Query(description="poets, authors, translators, ...")] = None,
):
    conditions, parameters = [], []
    if site:
        conditions.append("site = ?")
        parameters.append(site)
    if entity_type:
        conditions.append("entity_type = ?")
        parameters.append(entity_type)

    clause = where(conditions)
    total = db.scalar(f"SELECT count(*) FROM entities{clause}", parameters)
    rows = db.rows(
        f"SELECT {_COLUMNS} FROM entities{clause} ORDER BY name_translit, id LIMIT ? OFFSET ?",
        [*parameters, paging.limit, paging.offset],
    )
    return Page(
        items=[EntitySummary(**dict(row)) for row in rows], total=total, limit=paging.limit, offset=paging.offset
    )


@router.get("/poets/{site}/{slug}", response_model=EntityDetail)
def get_poet(site: str, slug: str):
    row = db.row(f"SELECT id, {_COLUMNS}, description FROM entities WHERE site = ? AND slug = ?", (site, slug))
    if row is None:
        raise HTTPException(status_code=404, detail=f"no poet {site}/{slug}")
    fields = dict(row)
    works = db.scalar("SELECT count(*) FROM works WHERE author_id = ?", (fields.pop("id"),))
    return EntityDetail(**fields, works=works)


@router.get("/poets/{site}/{slug}/works", response_model=Page[WorkSummary])
def get_poet_works(site: str, slug: str, paging: Pages):
    entity_id = db.scalar("SELECT id FROM entities WHERE site = ? AND slug = ?", (site, slug))
    if entity_id is None:
        raise HTTPException(status_code=404, detail=f"no poet {site}/{slug}")

    total = db.scalar("SELECT count(*) FROM works WHERE author_id = ?", (entity_id,))
    rows = db.rows(
        "SELECT w.site, w.slug, w.work_type, w.title, w.title_translit, w.title_hindi, w.title_urdu,"
        "       w.author_name, ? AS author_slug"
        " FROM works w WHERE w.author_id = ? ORDER BY w.work_type, w.id LIMIT ? OFFSET ?",
        (slug, entity_id, paging.limit, paging.offset),
    )
    return Page(items=[WorkSummary(**dict(row)) for row in rows], total=total, limit=paging.limit, offset=paging.offset)
