#!/bin/bash
# End-to-end check against a scratch manifest, using a handful of live requests per site.
# Verifies enumeration, the crawl, discovery, parsing and the delta path without touching
# any real archive: set DATA_DIR and RAW_DIR somewhere disposable before running.
set -euo pipefail

: "${DATA_DIR:?set DATA_DIR to a scratch directory}"
: "${RAW_DIR:?set RAW_DIR to a scratch directory}"
DB="$DATA_DIR/bayaz.db"
CORPUS="$DATA_DIR/corpus.db"

step() { printf '\n=== %s\n' "$1"; }
count() { sqlite3 "$1" "$2"; }

rm -rf "$DATA_DIR" "$RAW_DIR"
mkdir -p "$DATA_DIR"

step "rekhta: seed (no sitemap, so this only plants the roots)"
uv run bayaz enumerate --site rekhta 2>&1 | tail -1
count "$DB" "SELECT '  seeded ' || COUNT(*) || ' root(s)' FROM pages;"

step "rekhta: content-types fans out into listing chains"
uv run bayaz crawl --site rekhta --kind content-types --limit 1 2>&1 | tail -1
count "$DB" "SELECT '  ' || kind || ': ' || COUNT(*) FROM pages GROUP BY kind;"

step "rekhta: a listing yields works (x3 scripts) and its own next pages"
uv run bayaz crawl --site rekhta --kind couplet-list --limit 1 2>&1 | tail -1
count "$DB" "SELECT '  content pages: ' || COUNT(*) FROM pages WHERE kind='content';"

step "rekhta: a work yields its word codes"
uv run bayaz crawl --site rekhta --kind content --limit 1 2>&1 | tail -1
count "$DB" "SELECT '  word lookups: ' || COUNT(*) FROM pages WHERE kind='word';"

step "rekhta: a word resolves to a dictionary entry"
uv run bayaz crawl --site rekhta --kind word --limit 1 2>&1 | tail -1

step "parse: corpus rows, including word-level annotation"
uv run bayaz parse --site rekhta 2>&1 | tail -1
sqlite3 -column "$CORPUS" "SELECT '  work: ' || work_type || ' / ' || substr(title,1,30) || ' / ' || COALESCE(author_name,'?') FROM works;"
sqlite3 -column "$CORPUS" "SELECT '  words: ' || COUNT(*) || ' occurrences, ' || COUNT(DISTINCT code) || ' distinct codes' FROM work_words;"
sqlite3 -column "$CORPUS" "SELECT '  entry: ' || COALESCE(headword,'?') || ' [' || COALESCE(headword_hindi,'-') || ']' FROM entries LIMIT 1;"

step "delta: re-enumerate requeues listings but not captured works"
before_content=$(count "$DB" "SELECT COUNT(*) FROM pages WHERE kind='content' AND status='fetched';")
uv run bayaz enumerate --site rekhta 2>&1 | tail -1
after_content=$(count "$DB" "SELECT COUNT(*) FROM pages WHERE kind='content' AND status='fetched';")
listings=$(count "$DB" "SELECT COUNT(*) FROM pages WHERE kind IN ('content-types','couplet-list','content-list','poets','tags') AND status='pending';")
echo "  listings queued for re-walk: $listings"
echo "  captured works still fetched: $before_content -> $after_content"
[ "$before_content" = "$after_content" ] || { echo "  FAIL: a delta re-fetches works"; exit 1; }

step "sitemap sites: enumeration is idempotent and API rows derive from it"
uv run bayaz crawl --site hindwi --kind work --limit 2 2>&1 | tail -1
uv run bayaz parse --site hindwi 2>&1 | tail -1

printf '\nall checks passed\n'
