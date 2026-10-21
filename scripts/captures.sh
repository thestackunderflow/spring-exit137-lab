#!/usr/bin/env bash
# The video's captures, all in ONE session, probe off (the log a user really sees):
#   r-oom    compose.bug.yaml, standard load          -> ch. 0 terminal, ch. 2 replay
#   s-stop   compose.fix.yaml, a 20 s request in flight, then `docker stop` (default 10 s) -> who-killed row
#   s-kill   compose.fix.yaml, `docker kill` 3 s after ready                                  -> who-killed row
#   r-proof  compose.fix.yaml, standard load, then the lab's `docker stop -t 30`             -> ch. 6
#   j / j2   -Xmx128m (+ ExitOnOutOfMemoryError), /lab/hold?mb=200                          -> ch. 5 row, README
#   a-swap   the bug flags, memswap_limit unset                                               -> README
# Then mcp-canvas tools/logcap/logcap.ts (with E-trail: reads State.FinishedAt from inspect.json) writes
# evidence/replays/<run>/run.jsonl + run.meta.json for r-oom, r-proof and s-stop.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
source scripts/variants.sh
load_env
[ -f compose.fix.yaml ] || { log "compose.fix.yaml missing (T5)"; exit 1; }
export SESSION=${SESSION:-captures-$(date -u +%Y%m%dT%H%M%SZ)}
ONLY="${*:-r-oom s-stop s-kill r-proof j j2 a-swap}"
cap() {  # cap <name> <compose file> <mode> [opts cell]
  local name=$1 cf=$2 mode=$3 oc=${4:-}
  local d=evidence/runs/$name try
  for try in 1 2 3; do
    JAVA_OPTS="$( [ -n "$oc" ] && opts_of "$oc" )" LAB_PROBE=false MODE=$mode bash scripts/cell.sh "$name" "$d" "$cf"
    grep -q '"disturbed": true' "$d/result.json" || return 0
    mkdir -p evidence/runs-disturbed; rm -rf "evidence/runs-disturbed/$name-try$try"
    mv "$d" "evidence/runs-disturbed/$name-try$try"; log "$name disturbed, re-running"; sleep 60
  done
}
for run in $ONLY; do
  case $run in
    r-oom) cap r-oom compose.bug.yaml load ;;
    s-stop) cap s-stop compose.fix.yaml stop ;;
    s-kill) cap s-kill compose.fix.yaml kill ;;
    r-proof) cap r-proof compose.fix.yaml load ;;
    j) cap j compose.sweep.yaml j j ;;
    j2) cap j2 compose.sweep.yaml j2 j2 ;;
    a-swap) cap a-swap compose.swap.yaml load "$BUG" ;;
  esac
done
for run in r-oom r-proof s-stop; do
  case " $ONLY " in *" $run "*) ;; *) continue ;; esac
  d="$LAB_W/evidence/runs/$run"
  code=$(sed -n 's/.*"exit_code": \([0-9]*\).*/\1/p' "$d/result.json" | head -1)
  cf=$(sed -n 's/.*"compose_file": "\([^"]*\)".*/\1/p' "$d/result.json")
  mkdir -p "evidence/replays/$run"
  (cd "$MCP_CANVAS" && npx tsx tools/logcap/logcap.ts from-docker --raw "$d" --out "$LAB_W/evidence/replays/$run" \
     --scenario "$run" --exit "$code" -- docker compose -f "$cf" up app) | tee "evidence/replays/$run/logcap.txt"
  grep -q '"finishedAt"' "evidence/replays/$run/run.meta.json" || log "WARNING: $run meta has no finishedAt (E-trail)"
done
