"""What the archive contains: the sites, and the work types each one uses.

These are the site's entry points, and they are counts over the whole corpus, so they are
computed once at startup rather than per request.
"""

from functools import cache

from fastapi import APIRouter, HTTPException

from bayaz_api import db
from bayaz_api.models import SiteSummary, WorkTypeSummary

router = APIRouter(tags=["catalog"])


@cache
def _sites() -> list[SiteSummary]:
    counts: dict[str, dict[str, int]] = {}
    for table, field in (("works", "works"), ("entries", "entries"), ("entities", "entities")):
        for site, count in db.rows(f"SELECT site, count(*) FROM {table} GROUP BY site"):
            counts.setdefault(site, {"works": 0, "entries": 0, "entities": 0})[field] = count
    return [SiteSummary(site=site, **fields) for site, fields in sorted(counts.items())]


@cache
def _work_types(site: str) -> list[WorkTypeSummary]:
    return [
        WorkTypeSummary(work_type=work_type, works=count)
        for work_type, count in db.rows(
            "SELECT work_type, count(*) c FROM works WHERE site = ? GROUP BY work_type ORDER BY c DESC", (site,)
        )
    ]


@router.get("/sites", response_model=list[SiteSummary])
def list_sites():
    return _sites()


@router.get("/sites/{site}/work-types", response_model=list[WorkTypeSummary])
def list_work_types(site: str):
    types = _work_types(site)
    if not types:
        raise HTTPException(status_code=404, detail=f"no site {site}")
    return types


def warm():
    """Compute the catalog before the first request, since the counts are full scans."""
    for site in _sites():
        _work_types(site.site)
