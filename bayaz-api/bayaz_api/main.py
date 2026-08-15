"""The application.

Read-only over `serve.db`, so there is nothing to start but the database handle and nothing
to shut down. Endpoints are synchronous on purpose: sqlite reads block, and starlette's
thread pool is where blocking work belongs.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bayaz_api import config, db
from bayaz_api.routers import catalog, entries, poets, search, tags, works

DESCRIPTION = """
The parsed corpus of the Rekhta Foundation's literary sites: rekhta.org, hindwi.org and
sufinama.org, plus the rekhtadictionary.com dictionary.

Every work carries its title and body in up to three scripts. Poetry additionally carries
word-level positions, and each poetry word resolves to a dictionary entry through
`/entries/lookup`, which is what makes a tap-a-word reader possible.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.configure(config.SERVE_DB)
    catalog.warm()
    yield


app = FastAPI(
    title="bayaz",
    version="0.1.0",
    description=DESCRIPTION,
    lifespan=lifespan,
)

if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

for module in (catalog, works, poets, entries, tags, search):
    app.include_router(module.router)


@app.get("/health", tags=["catalog"])
def health():
    return {"status": "ok", "works": db.scalar("SELECT count(*) FROM works")}
