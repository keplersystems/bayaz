import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Relative to wherever bayaz runs (normally the repo root), since the library ships in a
# wheel and has no stable location of its own. Set DATA_DIR/RAW_DIR to pin them elsewhere.
DATA_DIR = Path(os.getenv("DATA_DIR") or "data")
RAW_DIR = Path(os.getenv("RAW_DIR") or "raw")
DATABASE_PATH = DATA_DIR / "bayaz.db"

# A browser string by default: it is what every probe was verified with, and a WAF rule
# added later is likelier to spare it. Override to identify yourself to the sites.
USER_AGENT = os.getenv(
    "BAYAZ_USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
)

# Pacing is per site: the sites crawl in parallel, each at its own gentle rate. These are a
# nonprofit's servers; the crawl taking days is the accepted cost of not hammering them.
REQUEST_DELAY = float(os.getenv("BAYAZ_REQUEST_DELAY", "0.35"))
CONCURRENCY = int(os.getenv("BAYAZ_CONCURRENCY", "3"))

# Rekhta's app origin answers ~5 KB of JSON where the websites serve 90-460 KB pages, so an
# identical request rate costs it a fraction of the bytes. It carries its own faster budget.
APP_REQUEST_DELAY = float(os.getenv("BAYAZ_APP_REQUEST_DELAY", "0.20"))
APP_CONCURRENCY = int(os.getenv("BAYAZ_APP_CONCURRENCY", "6"))
TIMEOUT = float(os.getenv("BAYAZ_TIMEOUT", "30"))
MAX_ATTEMPTS = int(os.getenv("BAYAZ_MAX_ATTEMPTS", "3"))
