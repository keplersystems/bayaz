"""What the archive contains: the sites, and the work types each one uses.

Both are counts over whole tables, and neither changes while the process runs, so they are
computed once at startup rather than per request.
"""

from functools import cache

from fastapi import APIRouter, HTTPException

from bayaz_api import db
from bayaz_api.models import SiteSummary, WorkTypeSummary

router = APIRouter(tags=["catalog"])

_SITES = """
    SELECT site, sum(works) works, sum(entries) entries, sum(entities) entities FROM (
        SELECT site, count(*) works, 0 entries, 0 entities FROM works GROUP BY site
        UNION ALL SELECT site, 0, count(*), 0 FROM entries GROUP BY site
        UNION ALL SELECT site, 0, 0, count(*) FROM entities GROUP BY site
    ) GROUP BY site ORDER BY site
"""


@cache
def _sites() -> list[SiteSummary]:
    return [SiteSummary(**dict(row)) for row in db.rows(_SITES)]


@cache
def _work_types(site: str) -> list[WorkTypeSummary]:
    return [
        WorkTypeSummary(**dict(row))
        for row in db.rows(
            "SELECT work_type, count(*) works FROM works WHERE site = ? GROUP BY work_type ORDER BY works DESC", (site,)
        )
    ]


def warm():
    for site in _sites():
        _work_types(site.site)


@router.get("/sites", response_model=list[SiteSummary])
def list_sites():
    return _sites()


@router.get("/sites/{site}/work-types", response_model=list[WorkTypeSummary])
def list_work_types(site: str):
    types = _work_types(site)
    if not types:
        raise HTTPException(status_code=404, detail=f"no site {site}")
    return types
