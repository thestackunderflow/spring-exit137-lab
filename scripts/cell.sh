#!/usr/bin/env bash
# One run of one cell, captured from the Compose-started app container (PLAN 3.5).
#   bash scripts/cell.sh <cell> <out dir> <compose file>
# Environment: JAVA_OPTS (compose.sweep/swap only), LAB_PROBE (true|false), DIRECT_MB, SESSION,
#   MODE = load (default) | stop (S-stop) | kill (S-kill) | j (Java OOME, keeps running) | j2 (exits on OOME)
# Writes into <out dir>: compose-up.txt (attached `docker compose up`, incl. "app-1 exited with code N"), mem-ready.json,
# oha.txt, mem-after.json + state-after.json (if still running after the load), stdout.txt / stderr.txt
# (`docker logs --timestamps`, one file per stream), inspect.json, ps.txt (`docker ps -a`), events.jsonl
# (`docker events` for the run window), stats-before/after.txt (other jobs), result.json (scripts/analyze_run.py).
set -uo pipefail
source "$(dirname "$0")/lib.sh"
load_env || exit 1
CELL=$1 D=$2 CF=$3
MODE=${MODE:-load}
export JAVA_OPTS="${JAVA_OPTS:-}" LAB_PROBE="${LAB_PROBE:-false}"
rm -rf "$D"; mkdir -p "$D"
ram_wait
stats_snapshot "$D/stats-before.txt"
capp() { docker compose -p $PROJECT -f "$LAB_W/$CF" "$@"; }
docker rm -f $APP_CT >/dev/null 2>&1
T0=$(date +%s.%N)
capp up --no-color app > "$D/compose-up.txt" 2>&1 &
UP=$!
if wait_ready "$D/mem-ready.json"; then
  date -u +%Y-%m-%dT%H:%M:%S.%NZ > "$D/ready-utc.txt"
  [ -n "${DIRECT_MB:-}" ] && curl_net -m 60 "http://app:8080/lab/direct?mb=$DIRECT_MB" > "$D/direct.txt"
  case "$MODE" in
    load)
      date -u +%Y-%m-%dT%H:%M:%S.%NZ > "$D/load-start-utc.txt"
      echo "oha -n $N -c $C --no-tui http://app:8080/report?mb=$MB" > "$D/cmd.txt"
      oha_run -n "$N" -c "$C" --no-tui "http://app:8080/report?mb=$MB" > "$D/oha.txt" 2>&1
      date -u +%Y-%m-%dT%H:%M:%S.%NZ > "$D/load-end-utc.txt"
      if [ "$(docker inspect -f '{{.State.Running}}' $APP_CT 2>/dev/null)" = true ]; then
        curl_net -m 10 http://app:8080/lab/mem > "$D/mem-after.json"
        docker inspect -f '{{json .State}}' $APP_CT > "$D/state-after.json"
        sleep 1
        docker stop -t 30 $APP_CT > /dev/null                 # the lab's polite ending (exit 143), not in the video
      fi ;;
    stop)
      docker run -d --rm --name exit137-slow --network $NET $CURL_IMAGE -s -m 60 "http://app:8080/lab/slow?seconds=20" >/dev/null
      sleep 2                                                # the slow request is now in flight
      t0=$(date +%s.%N); docker stop $APP_CT >/dev/null; t1=$(date +%s.%N)
      awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.2f\n", b-a}' > "$D/stop-seconds.txt"
      echo "docker stop $APP_CT" > "$D/cmd.txt" ;;
    kill)
      sleep 3
      docker kill $APP_CT >/dev/null
      echo "docker kill $APP_CT" > "$D/cmd.txt" ;;
    j|j2)
      echo "curl http://app:8080/lab/hold?mb=200" > "$D/cmd.txt"
      curl_net -m 60 -o "$D/hold-body.txt" -w '%{http_code}\n' "http://app:8080/lab/hold?mb=200" > "$D/hold-status.txt"
      if [ "$MODE" = j ]; then
        sleep 10
        docker inspect -f '{{.State.Running}}' $APP_CT > "$D/running-10s-after.txt" 2>&1
        curl_net -m 10 http://app:8080/lab/mem > "$D/mem-after.json"
        docker stop -t 30 $APP_CT >/dev/null
      fi ;;
  esac
fi
EXIT=$(timeout 300 docker wait $APP_CT 2>/dev/null || true)
echo "$EXIT" > "$D/docker-wait.txt"
wait $UP 2>/dev/null
docker logs --timestamps $APP_CT > "$D/stdout.txt" 2> "$D/stderr.txt"
docker inspect $APP_CT > "$D/inspect.json"
docker ps -a --filter "name=^/${APP_CT}$" --format '{{.Names}}   {{.Status}}' > "$D/ps.txt"
T1=$(date +%s.%N)
docker events --since "$T0" --until "$T1" --filter "container=$APP_CT" --format '{{json .}}' > "$D/events.jsonl"
capp down -t 0 >/dev/null 2>&1
stats_snapshot "$D/stats-after.txt"
for f in "$D"/*.txt "$D"/*.json "$D"/*.jsonl; do redact "$f"; done
py scripts/analyze_run.py "$D" "$CELL" "$MODE" "${SESSION:-none}" "$CF"
