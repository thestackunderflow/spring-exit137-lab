#!/usr/bin/env bash
# T0: image digests, Docker Engine / Desktop / containerd versions, the VM's kernel, MemTotal, SwapTotal, cgroup fs,
# docker info warnings, CPU model. Everything read from a container or the docker CLI, never from the plan.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
mkdir -p out
refs="$MAVEN_IMAGE $JDK_IMAGE $OHA_IMAGE $CURL_IMAGE $ALPINE_IMAGE $PYTHON_IMAGE"
for r in $refs; do docker image inspect "$r" >/dev/null 2>&1 || docker pull -q "$r" >/dev/null; done
meminfo=$(docker run --rm "$ALPINE_IMAGE" cat /proc/meminfo)
{
  echo '{"images": {'
  first=1
  for r in $refs; do
    tag=${r%@*}
    d=$(docker image inspect -f '{{range .RepoDigests}}{{println .}}{{end}}' "$r" | sed -n 's/.*@//p' | head -1)
    [ $first = 1 ] || echo ','; first=0
    printf '  "%s": {"digest": "%s"}' "$tag" "$d"
  done
  echo '},'
  printf '"docker_server_version": "%s",\n' "$(docker version --format '{{.Server.Version}}')"
  printf '"docker_client_version": "%s",\n' "$(docker version --format '{{.Client.Version}}')"
  printf '"docker_desktop": "%s",\n' "$(docker version --format '{{.Server.Platform.Name}}')"
  printf '"containerd_version": "%s",\n' "$(docker version --format '{{range .Server.Components}}{{if eq .Name "containerd"}}{{.Version}}{{end}}{{end}}')"
  printf '"kernel": "%s",\n' "$(docker run --rm "$ALPINE_IMAGE" uname -r)"
  printf '"vm_memtotal_kb": %s,\n' "$(echo "$meminfo" | awk '/^MemTotal:/{print $2}')"
  printf '"vm_swaptotal_kb": %s,\n' "$(echo "$meminfo" | awk '/^SwapTotal:/{print $2}')"
  printf '"cgroup_fs": "%s",\n' "$(docker run --rm "$JDK_IMAGE" stat -fc %T /sys/fs/cgroup)"
  printf '"docker_info_warnings": %s,\n' "$(docker info --format '{{json .Warnings}}')"
  printf '"ncpu": %s,\n' "$(docker info --format '{{.NCPU}}')"
  printf '"lscpu_model": "%s",\n' "$(docker run --rm "$JDK_IMAGE" lscpu | sed -n 's/^Model name: *//p' | head -1)"
  printf '"oha_version": "%s",\n' "$(docker run --rm "$OHA_IMAGE" --version)"
  printf '"recorded_utc": "%s"\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo '}'
} > out/env.json
sed -i 's/"docker_info_warnings": null/"docker_info_warnings": []/' out/env.json
cat out/env.json
