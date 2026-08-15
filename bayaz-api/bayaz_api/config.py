"""Runtime configuration, from the environment like the rest of the project."""

import os
from pathlib import Path

from bayaz import config as core

SERVE_DB = Path(os.getenv("BAYAZ_SERVE_DB", core.DATA_DIR / "serve.db"))

# Only needed while the site is served from a different origin than the api.
CORS_ORIGINS = [origin for origin in os.getenv("BAYAZ_CORS_ORIGINS", "").split(",") if origin]
