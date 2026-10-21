#!/usr/bin/env bash
# T3 calibration (blocking, first): A, A2, D x 5 with the load in load.env (K = lab.keep in application.properties).
# Stop rule (PLAN rev. 2): A killed 5/5 -> A is the bug; else A2 killed 5/5 -> use A2; else stop and re-plan.
# Writes out/bug.json and BUG=<cell> into load.env.
set -uo pipefail
source "$(dirname "$0")/reps.sh"
if [ ! -f load.env ]; then
  K=$(sed -n 's/^lab.keep=//p' src/main/resources/application.properties)
  printf 'K=%s\nMB=4\nN=2000\nC=8\n' "$K" > load.env
fi
load_env
export SESSION=calibrate-$(date -u +%Y%m%dT%H%M%SZ)
for cell in a a2 d; do run_reps "$cell"; done
py - <<'EOF'
import json, glob
def res(c):
    return [json.load(open(f)) for f in sorted(glob.glob(f'evidence/runs/{c}/rep*/result.json'))]
killed = {c: sum(r['outcome'] == 'killed' for r in res(c)) for c in ('a', 'a2')}
d = [r['outcome'] for r in res('d')]
flags = open('evidence/t4/a2-flags.txt').read()
gc = 'serial' if 'bool UseSerialGC                              = true' in flags or __import__('re').search(r'UseSerialGC\s+= true', flags) else 'other'
if killed['a'] == 5:
    bug, why = 'a', 'A killed 5/5'
elif killed['a2'] == 5:
    bug, why = 'a2', f"A killed {killed['a']}/5, A2 killed 5/5: use A2 (stop rule)"
else:
    bug, why = None, f"no cell killed 5/5 (A {killed['a']}/5, A2 {killed['a2']}/5): stop and re-plan"
out = {'bug_variant': bug, 'reason': why, 'killed': killed, 'd_outcomes': d, 'gc': gc,
       'load': open('load.env').read().split()}
json.dump(out, open('out/bug.json', 'w'), indent=1)
print(json.dumps(out))
EOF
BUG=$(sed -n 's/.*"bug_variant": "\([a-z0-9]*\)".*/\1/p' out/bug.json)
[ -n "$BUG" ] || { log "T3: no bug cell, stop"; exit 1; }
grep -q '^BUG=' load.env && sed -i "s/^BUG=.*/BUG=$BUG/" load.env || echo "BUG=$BUG" >> load.env
log "T3: bug cell $BUG"
