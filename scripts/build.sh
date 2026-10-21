#!/usr/bin/env bash
# Builds the jar in the pinned Maven image and the app image; records the dependency tree for T2.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
ram_wait
docker run --rm -v "$LAB_W:/lab" -v exit137-m2:/root/.m2 -w /lab "$MAVEN_IMAGE" mvn -q -B -DskipTests package
mkdir -p out
docker run --rm -v "$LAB_W:/lab" -v exit137-m2:/root/.m2 -w /lab "$MAVEN_IMAGE" \
  mvn -q -B dependency:tree -Dscope=runtime -DoutputFile=out/dependency-tree.txt
docker build -q -t "$APP_IMAGE" -f docker/Dockerfile . >/dev/null
docker image inspect -f '{{.Id}}' "$APP_IMAGE" > out/app-image-id.txt
log "built $APP_IMAGE $(cat out/app-image-id.txt)"
