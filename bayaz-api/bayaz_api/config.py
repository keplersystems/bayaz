"""Runtime configuration, read from the environment like the rest of the project."""

import os
from pathlib import Path

from bayaz import config as core

SERVE_DB = Path(os.getenv("BAYAZ_SERVE_DB", core.DATA_DIR / "serve.db"))

# The site is a static bundle served from another origin, so the browser needs to be told
# this api will answer it. Empty in production behind one hostname, where there is no
# cross-origin request to allow.
CORS_ORIGINS = [origin for origin in os.getenv("BAYAZ_CORS_ORIGINS", "").split(",") if origin]
