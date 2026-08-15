"""How every listing is filtered, counted and paged.

Offset rather than cursor paging because these listings are browsed: a reader jumps to page
400 of the ghazals, which a cursor cannot address.
"""

from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel

from bayaz_api import db
from bayaz_api.models import Page


def match_expression(query: str) -> str:
    """Turn user input into an fts5 MATCH expression.

    Every token is quoted, so the fts5 query grammar never sees the user's punctuation: an
    apostrophe or a hyphen would otherwise be a syntax error rather than a search.
    """
    return " ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in query.split())


@dataclass(frozen=True, slots=True)
class Paging:
    limit: int
    offset: int


def _paging(
    limit: Annotated[int, Query(ge=1, le=100, description="items per page")] = 20,
    offset: Annotated[int, Query(ge=0, description="items to skip")] = 0,
) -> Paging:
    return Paging(limit=limit, offset=offset)


Pages = Annotated[Paging, Depends(_paging)]


@dataclass(slots=True)
class Filters:
    """Conditions and their parameters, kept together so they cannot drift apart."""

    conditions: list[str] = field(default_factory=list)
    parameters: list[Any] = field(default_factory=list)

    def add(self, condition: str, value: Any | None):
        if value is not None:
            self.conditions.append(condition)
            self.parameters.append(value)

    @property
    def where(self) -> str:
        return f" WHERE {' AND '.join(self.conditions)}" if self.conditions else ""


def page[T: BaseModel](
    model: type[T],
    columns: str,
    source: str,
    order: str,
    paging: Paging,
    filters: Filters,
) -> Page[T]:
    """One filtered slice of `source`, with the total the filters match.

    `columns` may name more than the model needs, so a join used only for display costs the
    count nothing: the count runs against `source` with the same conditions.
    """
    total = db.scalar(f"SELECT count(*) FROM {source}{filters.where}", filters.parameters)
    found = db.rows(
        f"SELECT {columns} FROM {source}{filters.where} ORDER BY {order} LIMIT ? OFFSET ?",
        [*filters.parameters, paging.limit, paging.offset],
    )
    return Page(
        items=[model(**dict(row)) for row in found],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )
