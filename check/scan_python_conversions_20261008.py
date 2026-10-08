import ast
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path('/lg-home/cog8/lwli6/Swepro_test_trans')
IDS = ROOT / 'task_list/python_remaining_20261008.txt'


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def selectors(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                result = parser(value)
                if isinstance(result, (list, tuple)):
                    return list(result)
            except (ValueError, SyntaxError, TypeError):
                pass
    return None


def scan(instance_id):
    attempts = ROOT / 'runs' / instance_id / 'attempts'
    accepted = []
    for attempt in sorted(attempts.glob('attempt_*')):
        state = load(attempt / 'intermediate/control/state.json') or {}
        if state.get('status') == 'accepted' and (attempt / 'final/task.toml').is_file():
            accepted.append(attempt)
    if not accepted:
        return {'instance_id': instance_id, 'status': 'no_accepted_package'}
    attempt = accepted[-1]
    source = ROOT / 'runs' / instance_id / 'source/problem_statement.md'
    original = load(ROOT / 'tasks' / instance_id / 'original/tests/config.json') or {}
    final = load(attempt / 'final/tests/config.json') or {}
    metrics = load(attempt / 'review/metrics.json') or {}
    revision = str(metrics.get('revision') or '').split('/')[-1]
    trace = load(attempt / 'intermediate/converter/revisions' / revision / 'conversion_trace.json') or {}
    old_p2p = selectors(original.get('pass_to_pass'))
    new_p2p = selectors(final.get('pass_to_pass'))
    old_f2p = selectors(original.get('fail_to_pass'))
    new_f2p = selectors(final.get('fail_to_pass'))
    instruction = (attempt / 'final/instruction.md').read_text() if (attempt / 'final/instruction.md').is_file() else ''
    statement = source.read_text() if source.is_file() else ''
    audit1 = (load(attempt / 'review/final_audit.json') or {}).get('status')
    audit2 = (load(attempt / 'review/independent_audit.json') or {}).get('status')
    mapping = attempt / 'review/f2p_mapping.csv'
    mapped = []
    emitted = []
    if mapping.is_file():
        with mapping.open(newline='') as stream:
            for row in csv.DictReader(stream):
                mapped.append(row.get('source_f2p'))
                raw = row.get('emitted_tests') or '[]'
                try:
                    emitted.extend(json.loads(raw))
                except ValueError:
                    pass
    excluded = (trace.get('p2p_accounting') or {}).get('excluded')
    report = {
        'instance_id': instance_id,
        'attempt': attempt.name,
        'revision': revision,
        'state': 'accepted',
        'final_audit': audit1,
        'independent_audit': audit2,
        'original_f2p': len(old_f2p) if old_f2p is not None else None,
        'mapped_f2p': len(mapped),
        'original_p2p': len(old_p2p) if old_p2p is not None else None,
        'final_p2p': len(new_p2p) if new_p2p is not None else None,
        'p2p_excluded': len(excluded) if isinstance(excluded, list) else None,
        'checks': {
            'p2p_exact_prefix': old_p2p is not None and new_p2p is not None and new_p2p[:len(old_p2p)] == old_p2p,
            'p2p_no_exclusions': excluded == [],
            'instruction_source_retained': bool(statement) and statement.strip() in instruction,
            'instruction_no_requirements_interface': not re.search(r'^\s*#{1,6}\s*(?:Requirements|New Interfaces)\b', instruction, re.I | re.M),
            'f2p_rows_accounted': old_f2p is not None and sorted(mapped) == sorted(old_f2p),
            'emitted_tests_configured': all(t in (new_f2p or []) + (new_p2p or []) for t in emitted),
            'final_package_present': (attempt / 'final/tests/test.sh').is_file() and (attempt / 'final/task.toml').is_file(),
        },
    }
    report['structurally_qualified'] = audit1 == 'PASS' and audit2 == 'PASS' and all(report['checks'].values())
    return report

ids=[line.strip() for line in IDS.read_text().splitlines() if line.strip() and not line.startswith('#')]
reports=[scan(i) for i in ids]
out=ROOT / 'check/external_scan_python_20261008.json'
out.write_text(json.dumps(reports, ensure_ascii=False, indent=2)+'\n')
for report in reports:
    print(report['instance_id'].split('-')[1][:8], report.get('attempt'), report.get('structurally_qualified'), report.get('checks',{}))
print('structurally qualified',sum(r.get('structurally_qualified',False) for r in reports),'of',len(ids),'report',out)
