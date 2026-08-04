#!/bin/bash
# Keeps the crawl and the offload loop alive without tmux or an ssh session.
#
# Liveness checks are deliberately specific. The crawl renames its process to `bayaz`, so it
# is matched on that; the offload loop is plain bash and indistinguishable from any shell
# that merely mentions the script name, so it reports through a pidfile instead. Matching on
# a command-line pattern alone also matches this script, which is a mistake worth not
# repeating.
#
# Install to survive reboots:
#   (crontab -l 2>/dev/null; echo "@reboot sleep 30 && cd $PWD && setsid nohup bash ops/supervisor.sh >/dev/null 2>&1") | crontab -
set -u
BAYAZ_DIR="${BAYAZ_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
UV="${UV:-$HOME/.local/bin/uv}"
cd "$BAYAZ_DIR"

crawl_alive() { ps -eo comm,args | grep -E "^bayaz +" | grep -q " crawl"; }
offload_alive() { [ -f offload.pid ] && kill -0 "$(cat offload.pid)" 2>/dev/null; }

# A restore in progress must finish before offload starts moving files out again.
while pgrep -f "rclone copy s3:" >/dev/null; do sleep 30; done

while true; do
  crawl_alive || { echo "$(date -Is) starting crawl" >> supervisor.log; nohup $UV run bayaz crawl >> crawl.log 2>&1 & }
  offload_alive || { echo "$(date -Is) starting offload" >> supervisor.log; nohup bash ops/offload.sh >> offload.log 2>&1 & }
  sleep 120
done
