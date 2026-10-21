#!/usr/bin/env bash
# The JAVA_TOOL_OPTIONS of every cell (README "Intent"). P comes from out/fix.json (T5) once it exists.
if [ -z "${P:-}" ] && [ -f out/fix.json ]; then P=$(sed -n 's/^ *"P": *\([0-9]*\).*/\1/p' out/fix.json | head -1); fi
P=${P:-}
NMT_FLAGS="-XX:NativeMemoryTracking=summary -XX:+UnlockDiagnosticVMOptions -XX:+PrintNMTStatistics"
opts_of() {  # opts_of <cell>
  case "$1" in
    a) echo "-Xmx768m" ;;
    a2) echo "-Xms768m -Xmx768m" ;;
    a85) echo "-XX:MaxRAMPercentage=85" ;;
    a85s) echo "-XX:MaxRAMPercentage=85 -XX:InitialRAMPercentage=85" ;;
    d) echo "" ;;
    b) echo "-XX:MaxRAMPercentage=$P" ;;
    # worst case for the fix: heap committed AND touched from the start; NMT on (its own overhead only adds to the peak)
    b-full|c) echo "-XX:MaxRAMPercentage=$P -XX:InitialRAMPercentage=$P -XX:+AlwaysPreTouch $NMT_FLAGS" ;;
    j) echo "-Xmx128m" ;;
    j2) echo "-Xmx128m -XX:+ExitOnOutOfMemoryError" ;;
    *) echo "unknown cell $1" >&2; return 1 ;;
  esac
}
