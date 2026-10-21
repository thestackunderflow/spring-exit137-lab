#!/usr/bin/env bash
# Runs the JUnit tests (pinned Maven image), then the Python evidence tests (pinned python image).
# Nothing runs on the host but docker. Usage: bash tests/run-tests.sh [log-file] [unittest pattern]
set -uo pipefail
cd "$(dirname "$0")/.."
source scripts/lib.sh
LOG="${1:-tests/out/test-run.log}"
PATTERN="${2:-test_*.py}"
mkdir -p "$(dirname "$LOG")"
: > "$LOG"
docker run --rm -v "$LAB_W:/lab" -v exit137-m2:/root/.m2 -w /lab "$MAVEN_IMAGE" \
  mvn -q -B test 2>&1 | tail -40 | tee -a "$LOG"
grep -ho 'tests="[0-9]*" errors="[0-9]*" skipped="[0-9]*" failures="[0-9]*"' target/surefire-reports/TEST-*.xml 2>/dev/null \
  | sed 's/^/JUnit summary: /' | tee -a "$LOG"
docker run --rm -v "$LAB_W:/lab" -w /lab -e PYTHONDONTWRITEBYTECODE=1 "$PYTHON_IMAGE" \
  python -m unittest discover -s tests -p "$PATTERN" -v 2>&1 | tee -a "$LOG" | grep -E '^(FAIL|ERROR):|^Ran |^OK|^FAILED'
