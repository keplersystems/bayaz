"""Offset pagination, shared by every listing.

Offset rather than keyset because the listings are browsable rather than streamed: a reader
jumps to page 400 of the ghazals, which a cursor cannot express. Every listing is covered by
an index that carries its sort column, so the offset walk stays in the index.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query


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


def where(conditions: list[str]) -> str:
    return f" WHERE {' AND '.join(conditions)}" if conditions else ""
