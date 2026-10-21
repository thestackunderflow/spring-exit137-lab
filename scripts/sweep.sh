#!/usr/bin/env bash
# M-sweep after T3 (a, a2, d already run) and T5 (b-full already run at P): a85, a85s, b, c x 5, probe on.
# C = B-full + DIRECT_MB of retained direct buffers, DIRECT_MB = 768 - P% x 768 - min non-heap_kernel + 32, rounded
# up to 16 (so that heap + direct + non-heap > 768 while direct <= the heap max, J8). Writes out/direct.json.
set -uo pipefail
source "$(dirname "$0")/reps.sh"
load_env
[ -f out/fix.json ] || { log "run scripts/nmt.sh first"; exit 1; }
export SESSION=sweep-$(date -u +%Y%m%dT%H%M%SZ)
for cell in a85 a85s b; do run_reps "$cell"; done
DIRECT_MB=$(py - <<'EOF'
import json, math
fx = json.load(open('out/fix.json'))
P = fx['P']; nh = min(fx['non_heap_kernel_mib'])
need = 768 - P * 7.68 - nh
mb = int(math.ceil((need + 32) / 16) * 16)
heap_max = P * 7.68
assert mb <= heap_max, (mb, heap_max)
json.dump({'direct_mb': mb, 'P': P, 'min_non_heap_kernel_mib': nh, 'needed_mib': round(need, 1),
           'rule': 'ceil16(768 - P% x 768 - min non-heap_kernel + 32), <= heap max'}, open('out/direct.json', 'w'), indent=1)
print(mb)
EOF
)
log "C: DIRECT_MB=$DIRECT_MB"
export DIRECT_MB
run_reps c
unset DIRECT_MB
