#!/bin/bash
# Parse, then offload only what parse has consumed, then snapshot both databases.
#
# Selecting on parse state rather than file age is deliberate: a parse pass runs longer than
# any sane age threshold, so age alone lets pages captured mid-pass be moved before the next
# pass can read them, which silently strands them in S3 unparsed.
#
# Env: BAYAZ_DIR (repo root), BAYAZ_S3 (rclone remote:path), UV (uv binary).
set -u
BAYAZ_DIR="${BAYAZ_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
BAYAZ_S3="${BAYAZ_S3:?set BAYAZ_S3 to an rclone remote:path}"
UV="${UV:-$HOME/.local/bin/uv}"
INTERVAL="${BAYAZ_OFFLOAD_INTERVAL:-300}"

cd "$BAYAZ_DIR"
echo $$ > offload.pid

while true; do
  $UV run bayaz parse >> parse.log 2>&1

  if $UV run python ops/parsed_files.py > /tmp/parsed_list.txt 2>/dev/null && [ -s /tmp/parsed_list.txt ]; then
    rclone move raw "$BAYAZ_S3/raw" --files-from /tmp/parsed_list.txt \
      --transfers 32 --no-traverse --no-check-dest --log-level ERROR
    find raw -type d -empty -delete 2>/dev/null
  fi

  # Both databases, because the manifest alone rebuilds the crawl but not the corpus, and
  # re-parsing the corpus means restoring the whole raw store from S3 first.
  for db in bayaz corpus; do
    if [ -f "data/$db.db" ]; then
      rm -f "/tmp/$db.snap"
      if sqlite3 "data/$db.db" "VACUUM INTO '/tmp/$db.snap'"; then
        gzip -f "/tmp/$db.snap"
        rclone copyto "/tmp/$db.snap.gz" "$BAYAZ_S3/manifest/$db.db.gz" --log-level ERROR
      fi
    fi
  done

  sleep "$INTERVAL"
done
