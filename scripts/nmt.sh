#!/usr/bin/env bash
# T5: P from the kernel-counted non-heap of B-full (heap committed AND touched from the start, NMT on).
#   1. B-full at P0=50, 3 reps: non-heap_kernel = cgroup memory.peak - NMT "Java Heap" committed
#   2. P = largest multiple of 5 with P% x 768 + max non-heap_kernel + 76.8 <= 768
#   3. B-full at P, 5 reps: must survive 5/5 with memory.peak <= 691.2 MiB; their non-heap joins the max;
#      if P no longer holds or a rep fails, lower P by 5 and repeat.
# Writes out/fix.json.
set -uo pipefail
source "$(dirname "$0")/reps.sh"
load_env
export SESSION=t5-$(date -u +%Y%m%dT%H%M%SZ)
P0=50
run_bfull() {  # run_bfull <P> <dir prefix> <reps>
  local p=$1 pre=$2 n=$3 i d
  for i in $(seq 1 "$n"); do
    d=$pre/rep$i
    [ -n "${KEEP_DONE:-}" ] && [ -f "$d/result.json" ] && continue   # resume: a finished rep is kept
    for try in 1 2 3; do
      P=$p JAVA_OPTS="$(P=$p; source scripts/variants.sh; opts_of b-full)" LAB_PROBE=true \
        bash scripts/cell.sh b-full "$d" compose.sweep.yaml
      grep -q '"disturbed": true' "$d/result.json" || break
      mkdir -p evidence/runs-disturbed; rm -rf "evidence/runs-disturbed/$(basename "$pre")-rep$i-try$try"
      mv "$d" "evidence/runs-disturbed/$(basename "$pre")-rep$i-try$try"; log "b-full rep$i disturbed, re-running"; sleep 60
    done
  done
}
analyze() {  # prints "P ok" from every b-full result so far
  py - "$@" <<'EOF'
import json, glob, re, sys, math
LIM = 768
nh, runs = [], []
for f in sorted(glob.glob('evidence/runs/t5-p*/rep*/result.json') + glob.glob('evidence/runs/b-full/rep*/result.json')):
    r = json.load(open(f))
    d = f.rsplit('/', 1)[0]
    out = open(d + '/stdout.txt', encoding='utf-8', errors='replace').read()
    # PrintNMTStatistics (at exit) prints bytes; jcmd prints KB: accept both
    m = re.search(r'Java Heap \(reserved=\d+(?:KB)?, committed=(\d+)(KB)?\)', out)
    heap = (int(m.group(1)) * (1024 if m.group(2) else 1)) if m else None
    peak = r['memory_peak_bytes']
    row = {'run': d, 'outcome': r['outcome'], 'peak_bytes': peak, 'heap_committed_bytes': heap,
           'java_tool_options': r['java_tool_options']}
    if peak and heap:
        row['non_heap_kernel_mib'] = round((peak - heap) / 2**20, 1)
        nh.append(row['non_heap_kernel_mib'])
    runs.append(row)
mx = max(nh)
P = int(math.floor((LIM - 76.8 - mx) / 7.68 / 5) * 5)
fx = {'P': P, 'non_heap_kernel_mib': nh, 'max_non_heap_kernel_mib': mx,
      'inequality': f'{P}% x 768 + {mx} + 76.8 = {round(P*7.68 + mx + 76.8, 1)} <= 768',
      'rule': 'P = largest multiple of 5 with P% x 768 + max non-heap_kernel + 10% x 768 <= 768 (PLAN rev. 2 T5)',
      'runs': runs}
json.dump(fx, open('out/fix.json', 'w'), indent=1)
print(P)
EOF
}
mkdir -p evidence/runs
KEEP_DONE=1 run_bfull $P0 evidence/runs/t5-p$P0 3
P=$(analyze)
for attempt in 1 2 3 4; do
  log "T5: candidate P=$P"
  rm -rf evidence/runs/b-full
  run_bfull "$P" evidence/runs/b-full 5
  NEWP=$(analyze)
  bad=$(py - <<'EOF'
import json, glob
bad = 0
for f in glob.glob('evidence/runs/b-full/rep*/result.json'):
    r = json.load(open(f))
    if r['outcome'] != 'survived' or not r['memory_peak_bytes'] or r['memory_peak_bytes'] > 0.9 * 805306368:
        bad += 1
print(bad)
EOF
)
  if [ "$bad" = 0 ] && [ "$NEWP" -gt "$P" ]; then P=$NEWP; continue; fi
  if [ "$bad" = 0 ] && [ "$NEWP" -eq "$P" ]; then
    py - "$P" <<'EOF'
import json, sys
fx = json.load(open('out/fix.json')); P = int(sys.argv[1])
mx = fx['max_non_heap_kernel_mib']
fx['P'] = P; fx['inequality'] = f'{P}% x 768 + {mx} + 76.8 = {round(P*7.68 + mx + 76.8, 1)} <= 768'
fx['b_full_5_of_5'] = True
json.dump(fx, open('out/fix.json', 'w'), indent=1)
EOF
    log "T5: P=$P holds (B-full 5/5)"; exit 0
  fi
  P=$(( NEWP < P - 5 ? NEWP : P - 5 ))
done
log "T5: no P held after 4 attempts"; exit 1
