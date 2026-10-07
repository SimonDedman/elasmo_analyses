#!/usr/bin/env bash
# Build every topic in data/topic_review/*.json, serially: feature pass (skipped when features.jsonl is
# newer than the topic file and the vocabulary hash is unchanged), then pages. The shared suggestion pool
# is rebuilt once at the end, because its exclusion list is the union of every topic's vocabulary, then the
# cross-topic rules table (docs/topic_review/rules.js).
# Status for the monitor: outputs/topic_review/build_all_status.json ; log: outputs/topic_review/build_all.log
# Usage: scripts/topic_review_build_all.sh [--force-features] [topic ...]
set -u
cd "$(dirname "$0")/.."
PY=python3; [ -x venv/bin/python ] && PY=venv/bin/python
OUT=outputs/topic_review; LOG=$OUT/build_all.log; ST=$OUT/build_all_status.json
FORCE=0; TOPICS=()
for a in "$@"; do case "$a" in --force-features) FORCE=1;; *) TOPICS+=("$a");; esac; done
if [ ${#TOPICS[@]} -eq 0 ]; then for f in data/topic_review/*.json; do TOPICS+=("$(basename "$f" .json)"); done; fi
mkdir -p "$OUT"
status() { # topic stage state [seconds]
  $PY - "$ST" "$1" "$2" "$3" "${4:-}" <<'PYEOF'
import json, sys, time, os
p, topic, stage, state, secs = sys.argv[1:6]
d = json.load(open(p)) if os.path.exists(p) else {}
t = d.setdefault(topic, {}); e = t.setdefault(stage, {})
e["state"] = state; e["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
if secs: e["seconds"] = float(secs)
d["_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
json.dump(d, open(p, "w"), indent=1)
PYEOF
}
echo "=== build_all start $(date '+%F %T') topics: ${TOPICS[*]}" >> "$LOG"
for t in "${TOPICS[@]}"; do
  tj=data/topic_review/$t.json
  need=1
  if [ $FORCE -eq 0 ] && [ -s "$OUT/$t/features.jsonl" ] && [ "$OUT/$t/features.jsonl" -nt "$tj" ]; then need=0; fi
  if [ $need -eq 1 ]; then
    status "$t" features running; s0=$(date +%s)
    if $PY scripts/build_topic_features.py --topic "$tj" --workers 10 >> "$LOG" 2>&1; then status "$t" features done $(( $(date +%s) - s0 )); else status "$t" features FAILED $(( $(date +%s) - s0 )); echo "!!! $t features FAILED" >> "$LOG"; continue; fi
  else
    status "$t" features skipped
  fi
  status "$t" pages running; s0=$(date +%s)
  if $PY scripts/build_topic_review_pages.py --topic "$tj" >> "$LOG" 2>&1; then status "$t" pages done $(( $(date +%s) - s0 )); else status "$t" pages FAILED $(( $(date +%s) - s0 )); echo "!!! $t pages FAILED" >> "$LOG"; fi
done
status _shared pool running; s0=$(date +%s)
if $PY scripts/build_topic_candidates.py --workers 10 >> "$LOG" 2>&1; then status _shared pool done $(( $(date +%s) - s0 )); else status _shared pool FAILED $(( $(date +%s) - s0 )); fi
status _shared rules_table running; s0=$(date +%s)
if $PY scripts/build_topic_review_rules_table.py >> "$LOG" 2>&1; then status _shared rules_table done $(( $(date +%s) - s0 )); else status _shared rules_table FAILED $(( $(date +%s) - s0 )); fi
echo "=== build_all finished $(date '+%F %T')" >> "$LOG"
status _all chain done
