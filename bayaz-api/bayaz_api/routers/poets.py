"""Poets, and the other contributor types the sites distinguish: authors, translators,
editors, publishers, artists, contributors."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bayaz_api import db
from bayaz_api.listing import Filters, Pages, page
from bayaz_api.models import EntityDetail, EntitySummary, Page, WorkSummary

router = APIRouter(tags=["poets"])

_COLUMNS = "site, slug, entity_type, name, name_hindi, name_urdu, name_translit, born, died"


@router.get("/poets", response_model=Page[EntitySummary])
def list_poets(
    paging: Pages,
    site: Annotated[str | None, Query(description="rekhta, hindwi or sufinama")] = None,
    entity_type: Annotated[str | None, Query(description="poets, authors, translators, ...")] = None,
):
    filters = Filters()
    filters.add("site = ?", site)
    filters.add("entity_type = ?", entity_type)
    return page(EntitySummary, _COLUMNS, "entities", "name_translit, id", paging, filters)


@router.get("/poets/{site}/{slug}", response_model=EntityDetail)
def get_poet(site: str, slug: str):
    found = db.row(f"SELECT id, {_COLUMNS}, description FROM entities WHERE site = ? AND slug = ?", (site, slug))
    if found is None:
        raise HTTPException(status_code=404, detail=f"no poet {site}/{slug}")
    fields = dict(found)
    works = db.scalar("SELECT count(*) FROM works WHERE author_id = ?", (fields.pop("id"),))
    return EntityDetail(**fields, works=works)


@router.get("/poets/{site}/{slug}/works", response_model=Page[WorkSummary])
def get_poet_works(site: str, slug: str, paging: Pages):
    entity_id = db.scalar("SELECT id FROM entities WHERE site = ? AND slug = ?", (site, slug))
    if entity_id is None:
        raise HTTPException(status_code=404, detail=f"no poet {site}/{slug}")

    filters = Filters()
    filters.add("w.author_id = ?", entity_id)
    columns = (
        "w.site, w.slug, w.work_type, w.title, w.title_translit, w.title_hindi, w.title_urdu,"
        " w.author_name, e.slug AS author_slug"
    )
    source = "works w JOIN entities e ON e.id = w.author_id"
    return page(WorkSummary, columns, source, "w.work_type, w.id", paging, filters)
