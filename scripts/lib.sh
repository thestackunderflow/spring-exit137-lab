#!/usr/bin/env bash
# Shared settings and helpers. Source it from the lab root: `source scripts/lib.sh`.
# Every image is pinned by tag AND digest (PLAN 3.1); the compose files use the same references.
export MSYS_NO_PATHCONV=1
LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_W="$(cd "$LAB_ROOT" && (pwd -W 2>/dev/null || pwd))"
cd "$LAB_ROOT"

MAVEN_IMAGE=maven:3.9.16-eclipse-temurin-21@sha256:99e61abcff91a9b1333463bd8451fb18495d6eba9250ac66a338b518f8278320
JDK_IMAGE=eclipse-temurin:21.0.12.1_1-jdk-noble@sha256:107215954359f1ab0be058a247d7c64ed6e69c71c1682d471d38ef751ec8e964
OHA_IMAGE=ghcr.io/hatoo/oha:1.16.0@sha256:3ec3dbf549ea197793482d47a6324797411406bbf438c2fe8b91f244ec641a2f
CURL_IMAGE=curlimages/curl:8.11.1@sha256:c1fe1679c34d9784c1b0d1e5f62ac0a79fca01fb6377cdd33e90473c6f9f9a69
ALPINE_IMAGE=alpine:3.24.2@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6
PYTHON_IMAGE=python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
APP_IMAGE=exit137-app:1.0
PROJECT=exit137
NET=exit137-net
APP_CT=exit137-app-1
MCP_CANVAS="$LAB_ROOT/../Refream-Canvas/mcp-canvas"
# the other jobs' containers: recorded per run, never stopped
OTHER_FILTER='mcp-canvas|reframe|ollama|llama|gemma|hikari|solidcraft|ogl|lc-'

log() { echo "[$(date -u +%H:%M:%S)] $*" >&2; }

free_gb() {  # host free physical memory in GB (Windows)
  powershell.exe -NoProfile -Command "[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1)" | tr -d '\r'
}

ram_wait() {  # wait until the host has >= 4 GB free (other jobs share the machine)
  local f
  while :; do
    f=$(free_gb)
    awk -v f="$f" 'BEGIN{exit !(f>=4)}' && return 0
    log "free RAM ${f} GB < 4 GB: waiting 180 s"; sleep 180
  done
}

stats_snapshot() {  # stats_snapshot <file>: docker stats of every container + free host RAM
  { echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) free_ram_gb=$(free_gb)"
    docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'; } > "$1" 2>&1
}

load_env() {  # K, MB, N, C from load.env (frozen by T3)
  [ -f load.env ] || { log "no load.env: run scripts/calibrate.sh first"; return 1; }
  # shellcheck disable=SC1091
  source load.env
}

curl_net() { docker run --rm --network $NET $CURL_IMAGE -s "$@"; }

wait_ready() {  # readiness from OUTSIDE the app container (acc S2): the first answer from /lab/mem
  local out=$1 i
  for i in $(seq 1 120); do
    if curl_net -m 2 http://app:8080/lab/mem > "$out" 2>/dev/null && grep -q '"memory.max"' "$out"; then return 0; fi
    docker inspect -f '{{.State.Status}}' $APP_CT 2>/dev/null | grep -q exited && { log "app exited before ready"; return 1; }
    sleep 0.5
  done
  log "app not ready"; return 1
}

oha_run() {  # oha as the Compose service on the lab network (never through a host port)
  docker compose -p exit137-load -f "$LAB_W/compose.load.yaml" run --rm --no-deps -T oha "$@"
}

py() {  # python in the pinned image, lab mounted at /lab (nothing runs on the host)
  docker run --rm -i -v "$LAB_W:/lab" -w /lab -e PYTHONDONTWRITEBYTECODE=1 "$PYTHON_IMAGE" python "$@"
}

redact() {  # redact <file>: the Windows account name never leaves out/ (public repo later)
  [ -f "$1" ] && sed -i -e "s/$(whoami)/[user]/g" -e "s/${USERNAME:-__none__}/[user]/g" "$1"
}
