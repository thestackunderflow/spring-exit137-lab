#!/usr/bin/env bash
# T10 (optional evidence): the kernel's own OOM lines, read from the WSL 2 VM's ring buffer by a privileged alpine.
# Run right after the r-oom capture. Saves the full raw dmesg and r-oom's two OOM lines (the PID is the VM's, not 1).
set -uo pipefail
source "$(dirname "$0")/lib.sh"
mkdir -p evidence/t10
if docker run --rm --privileged "$ALPINE_IMAGE" dmesg > evidence/t10/dmesg-raw.txt 2> evidence/t10/dmesg-err.txt; then
  # only r-oom's kill: the oom-kill summary names the container's cgroup (its full ID); the next line is the kill
  id=$(grep -o '"Id": "[0-9a-f]*"' evidence/runs/r-oom/inspect.json | head -1 | grep -o '[0-9a-f]\{64\}')
  [ -n "$id" ] || { log "T10: no r-oom container ID"; exit 1; }
  grep -A1 "cpuset=$id" evidence/t10/dmesg-raw.txt > evidence/t10/dmesg-oom.txt
  [ -s evidence/t10/dmesg-oom.txt ] || rm -f evidence/t10/dmesg-oom.txt
  log "T10: $(wc -l < evidence/t10/dmesg-oom.txt 2>/dev/null || echo 0) OOM lines for r-oom ($id)"
else
  log "T10: dmesg not readable ($(cat evidence/t10/dmesg-err.txt))"
fi
