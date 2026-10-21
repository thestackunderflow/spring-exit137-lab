#!/usr/bin/env bash
# run_reps <cell> [first rep] [last rep]: 5 reps of a sweep cell (probe on), each in evidence/runs/<cell>/rep<i>.
# A rep whose result says "disturbed" (host RAM < 4 GB or the other jobs above half the VM's CPUs) is moved to
# evidence/runs-disturbed/ and run again (at most 3 tries).
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
source scripts/variants.sh
run_reps() {
  local cell=$1 from=${2:-1} to=${3:-5} i try d
  for i in $(seq "$from" "$to"); do
    for try in 1 2 3; do
      d=evidence/runs/$cell/rep$i
      JAVA_OPTS="$(opts_of "$cell")" LAB_PROBE=true SESSION="${SESSION:-sweep}" \
        bash scripts/cell.sh "$cell" "$d" compose.sweep.yaml
      if grep -q '"disturbed": true' "$d/result.json" 2>/dev/null; then
        mkdir -p evidence/runs-disturbed/$cell; rm -rf "evidence/runs-disturbed/$cell/rep$i-try$try"
        mv "$d" "evidence/runs-disturbed/$cell/rep$i-try$try"; log "$cell rep$i disturbed, re-running"
        sleep 60
      else
        break
      fi
    done
  done
}
