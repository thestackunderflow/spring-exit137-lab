#!/usr/bin/env bash
# T1 / T4: what the JVM sees inside the 768m container, per cell, started by Compose with the cell's JAVA_TOOL_OPTIONS.
#   bash scripts/basics.sh a a2 d [b a-swap ...]
# -XshowSettings:system -> evidence/t4/<cell>-system.txt ; -XX:+PrintFlagsFinal -> evidence/t4/<cell>-flags.txt
# out/basics.json collects MaxHeapSize and UseSerialGC per cell (merged with earlier runs).
set -euo pipefail
source "$(dirname "$0")/lib.sh"
source scripts/variants.sh
mkdir -p evidence/t4 out
for cell in "$@"; do
  cf=compose.sweep.yaml; opts_cell=$cell
  if [ "$cell" = a-swap ]; then cf=compose.swap.yaml; opts_cell=$(sed -n 's/^BUG=//p' load.env 2>/dev/null || echo a2); fi
  export JAVA_OPTS="$(opts_of "$opts_cell" | sed "s/ $NMT_FLAGS//")" LAB_PROBE=false
  jrun() { docker compose -p exit137-t4 -f "$LAB_W/$cf" run --rm --no-deps -T --entrypoint java app "$@"; }
  jrun -XshowSettings:system -version > "evidence/t4/$cell-system.txt" 2>&1
  jrun -XX:+PrintFlagsFinal -version > "evidence/t4/$cell-flags.txt" 2>&1
  docker compose -p exit137-t4 -f "$LAB_W/$cf" down -t 0 >/dev/null 2>&1 || true
  log "$cell: $(grep -E ' MaxHeapSize | UseSerialGC ' "evidence/t4/$cell-flags.txt" | tr -s ' ' | tr '\n' ';')"
done
docker run --rm "$JDK_IMAGE" stat -fc %T /sys/fs/cgroup > evidence/t4/cgroup-fs.txt
py - <<'EOF'
import json, os, re, glob
out = {'cgroup_fs': open('evidence/t4/cgroup-fs.txt').read().strip(), 'max_heap_size': {}, 'use_serial_gc': {}}
for f in sorted(glob.glob('evidence/t4/*-flags.txt')):
    cell = os.path.basename(f)[:-len('-flags.txt')]
    t = open(f).read()
    m = re.search(r'size_t MaxHeapSize\s+= (\d+)', t)
    g = re.search(r'bool UseSerialGC\s+= (\w+)', t)
    if m: out['max_heap_size'][cell] = int(m.group(1))
    if g: out['use_serial_gc'][cell] = g.group(1) == 'true'
json.dump(out, open('out/basics.json', 'w'), indent=1)
print(json.dumps(out))
EOF
