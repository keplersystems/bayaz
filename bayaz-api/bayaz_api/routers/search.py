"""Full-text search across works and dictionary entries."""

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from bayaz_api import db
from bayaz_api.listing import Pages, match_expression
from bayaz_api.models import Page, SearchHit

router = APIRouter(tags=["search"])


@dataclass(frozen=True, slots=True)
class _Target:
    kind: str
    index: str
    source: str
    title: str


_TARGETS = {
    "works": _Target(
        kind="work",
        index="works_fts",
        source="works_fts JOIN works t ON t.id = works_fts.rowid",
        title="coalesce(t.title, t.title_hindi, t.title_urdu)",
    ),
    "entries": _Target(
        kind="entry",
        index="entries_fts",
        source="entries_fts JOIN entries t ON t.id = entries_fts.rowid",
        title="coalesce(t.headword, t.headword_hindi, t.headword_urdu)",
    ),
    "poets": _Target(
        kind="poet",
        index="entities_fts",
        source="entities_fts JOIN entities t ON t.id = entities_fts.rowid",
        title="coalesce(t.name, t.name_hindi, t.name_urdu)",
    ),
}


@router.get("/search", response_model=Page[SearchHit])
def search(
    paging: Pages,
    q: Annotated[str, Query(min_length=2, description="words to search for, in any script")],
    kind: Annotated[Literal["works", "entries", "poets"], Query(description="what to search")] = "works",
    site: Annotated[str | None, Query(description="restrict to one site")] = None,
):
    expression = match_expression(q)
    if not expression:
        return Page(items=[], total=0, limit=paging.limit, offset=paging.offset)

    target = _TARGETS[kind]
    clause = f"{target.index} MATCH ?" + (" AND t.site = ?" if site else "")
    parameters = [expression, site] if site else [expression]

    total = db.scalar(f"SELECT count(*) FROM {target.source} WHERE {clause}", parameters)
    found = db.rows(
        # Column -1 snippets whichever column matched. It is null when that column is null,
        # which happens on the 116,529 entries that have no senses.
        f"SELECT t.site, t.slug, '{target.kind}' kind, {target.title} title,"
        f"       coalesce(snippet({target.index}, -1, '', '', ' ... ', 24), '') snippet"
        f" FROM {target.source} WHERE {clause} ORDER BY rank LIMIT ? OFFSET ?",
        [*parameters, paging.limit, paging.offset],
    )
    return Page(
        items=[SearchHit(**dict(row)) for row in found],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )
