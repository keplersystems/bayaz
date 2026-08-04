"""How a page kind must be requested.

Most captures are a plain GET, but Rekhta's poetry API takes its parameters in the query
string while still requiring a JSON body, and omitting that body does not fail: the server
holds the connection for about 36 seconds and then closes it, exactly as it does for a
missing parameter. Declaring the shape per kind keeps that knowledge beside the API
definitions rather than inside the crawl loop.
"""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Request:
    method: str = "GET"
    body: dict | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    # A client-generated UUID with no server-side registration. Rekhta's app sends its
    # device id; any value is accepted, and a fresh one per request avoids presenting a
    # stable identity we were never issued.
    temptoken: bool = False

    def headers(self) -> dict[str, str]:
        headers = dict(self.extra_headers)
        if self.temptoken:
            headers["temptoken"] = str(uuid.uuid4())
        return headers


GET = Request()

# Rekhta poetry API: parameters stay in the query string, the body is a fixed placeholder
# the server never reads but does require.
REKHTA_POST = Request(method="POST", body={"a": "a"}, temptoken=True)
REKHTA_GET = Request(temptoken=True)


def request_for(site: str, kind: str) -> Request:
    from bayaz.rekhta import request_for_kind

    return request_for_kind(kind) if site == "rekhta" else GET
