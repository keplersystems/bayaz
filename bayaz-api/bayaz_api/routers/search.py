"""Full-text search across works and dictionary entries."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from bayaz_api import db
from bayaz_api.models import Page, SearchHit
from bayaz_api.pagination import Pages

router = APIRouter(tags=["search"])


def _match(query: str) -> str:
    """Turn user input into an fts5 MATCH expression.

    Every token is quoted, so the fts5 query grammar never sees the user's punctuation: an
    apostrophe or a hyphen would otherwise be a syntax error rather than a search. Quoting
    also makes the tokens implicit-AND terms, which is what a reader expects from a search
    box.
    """
    tokens = [token.replace('"', '""') for token in query.split()]
    return " ".join(f'"{token}"' for token in tokens)


_WORK_HITS = """
    SELECT w.site, w.slug, 'work' AS kind, coalesce(w.title, w.title_hindi, w.title_urdu) AS title,
           snippet(works_fts, -1, '', '', ' ... ', 24) AS snippet
    FROM works_fts JOIN works w ON w.id = works_fts.rowid
    WHERE works_fts MATCH ?
"""

_ENTRY_HITS = """
    SELECT e.site, e.slug, 'entry' AS kind, coalesce(e.headword, e.headword_hindi, e.headword_urdu) AS title,
           snippet(entries_fts, 3, '', '', ' ... ', 24) AS snippet
    FROM entries_fts JOIN entries e ON e.id = entries_fts.rowid
    WHERE entries_fts MATCH ?
"""


@router.get("/search", response_model=Page[SearchHit])
def search(
    paging: Pages,
    q: Annotated[str, Query(min_length=2, description="words to search for, in any script")],
    kind: Annotated[Literal["works", "entries"], Query(description="what to search")] = "works",
    site: Annotated[str | None, Query(description="restrict to one site")] = None,
):
    expression = _match(q)
    if not expression:
        return Page(items=[], total=0, limit=paging.limit, offset=paging.offset)

    hits, table, alias = (_WORK_HITS, "works_fts", "w") if kind == "works" else (_ENTRY_HITS, "entries_fts", "e")
    joined = "works w ON w.id = works_fts.rowid" if kind == "works" else "entries e ON e.id = entries_fts.rowid"

    condition, parameters = "", [expression]
    if site:
        condition = f" AND {alias}.site = ?"
        parameters.append(site)

    total = db.scalar(
        f"SELECT count(*) FROM {table} JOIN {joined} WHERE {table} MATCH ?{condition}",
        parameters,
    )
    rows = db.rows(
        f"{hits}{condition} ORDER BY rank LIMIT ? OFFSET ?",
        [*parameters, paging.limit, paging.offset],
    )
    return Page(items=[SearchHit(**dict(row)) for row in rows], total=total, limit=paging.limit, offset=paging.offset)
