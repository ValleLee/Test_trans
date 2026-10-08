#!/usr/bin/env python3
"""Run deterministic artifact and optional Base/Gold gates for a verifier revision.

The script never invents a conversion.  It checks the revision contract first;
``--execute`` then runs the candidate Harbor verifier in the task image using
the same Docker fallback used by the Stage 1 preflight.  Official Stage 3
runs should use pinned Harbor v0.22.0 instead.
"""
from __future__ import annotations
import argparse, ast, json, sys
from pathlib import Path

from ..runtime.stage1 import image_name, run_docker_preflight, write_json
from swepro_trans.paths import PROJECT_ROOT, resolve_task  # noqa: E402
from ..conversion_schema import (
    REQUIRED_F2P_FIELDS, classification_errors, converted_selector_groups, canonical_retained_p2p, append_f2p_regressions, replay_expectation,
    trace_disposition_errors, specification_provenance_errors,
    specification_addendum_errors,
    UNRESOLVED_MARKER, UNRESOLVED_EXACT_VALUES,
)

REQUIRED_TEST_FILES = ("test.sh", "run_script.sh", "parser.py", "config.json")
REQUIRED_REVISION_FILES = ("conversion_trace.json", "functional_specification.md", "self_review.md", "manifest.json")

def parse_list(value):
    if isinstance(value, list):
        return [str(x) for x in value]
    for fn in (json.loads, ast.literal_eval):
        try:
            result = fn(value)
            return [str(x) for x in result] if isinstance(result, (list, tuple)) else []
        except Exception:
            pass
    return []

def _selector_is_emitted(selector: str, tests_root: Path) -> bool:
    """Check that an accounting selector names code present in this revision.

    This is deliberately syntax-light so it works across Python, Go,
    JavaScript and other task languages. The file component must exist in the
    emitted bundle and the terminal test name must occur in that file. Runtime
    collection remains the authority in hard replay.
    """
    selector = str(selector).strip()
    if not selector:
        return False
    parts = selector.split("::")
    file_part = parts[0]
    candidate = tests_root / Path(file_part).name
    if not candidate.is_file():
        candidate = tests_root / file_part
    if candidate.is_file():
        artifact_text = candidate.read_text(encoding="utf-8", errors="replace")
    else:
        # Some language runners materialize tests from an embedded heredoc in
        # test.sh.  Such source is part of the emitted bundle, so inspect the
        # executable bundle files instead of assuming a standalone test file.
        # A selector listed in config.json is only a claim, not emitted test
        # code. Exclude the config from this fallback scan so native historical
        # F2P selectors cannot masquerade as converted tests merely because
        # their names are present in the selector list. Embedded tests in the
        # executable harness remain discoverable through test.sh/run_script.sh.
        artifact_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in tests_root.rglob("*")
            if path.is_file() and path.name != "config.json"
        )
        if Path(file_part).name not in artifact_text:
            return False
    if len(parts) == 1:
        return True
    terminal = parts[-1].split("[", 1)[0].strip()
    if not terminal:
        return True
    return terminal in artifact_text


def artifact_contract(root: Path, rev: Path) -> dict:
    paths = resolve_task(root)
    original = paths.original
    errors=[]
    if not original.is_dir(): errors.append('missing original task')
    if not paths.source.joinpath('problem_statement.md').is_file(): errors.append('missing problem_statement evidence')
    if paths.specification_addendum_path.is_file():
        errors.extend(specification_addendum_errors(
            paths.specification_addendum_path.read_text(encoding='utf-8', errors='replace')
        ))
    tests=rev/'tests'
    for name in REQUIRED_TEST_FILES:
        if not (tests/name).is_file(): errors.append(f'missing revision tests/{name}')
    for name in REQUIRED_REVISION_FILES:
        if not (rev/name).is_file(): errors.append(f'missing revision {name}')
    self_review=rev/'self_review.md'
    if self_review.is_file():
        self_review_text = self_review.read_text(encoding='utf-8', errors='replace')
        if not self_review_text.rstrip().endswith('SELF_REVIEW: PASS'):
            errors.append('self_review.md must end with SELF_REVIEW: PASS')
        if UNRESOLVED_MARKER.search(self_review_text):
            errors.append('self_review.md contains an unresolved scaffold marker')
    functional_specification = rev/'functional_specification.md'
    if functional_specification.is_file() and UNRESOLVED_MARKER.search(functional_specification.read_text(encoding='utf-8', errors='replace')):
        errors.append('functional_specification.md contains an unresolved scaffold marker')
    manifest=rev/'manifest.json'
    if manifest.is_file():
        try:
            manifest_data=json.loads(manifest.read_text())
            if not isinstance(manifest_data, dict):
                errors.append('manifest.json must contain an object')
            else:
                for field in ('revision', 'status'):
                    value = str(manifest_data.get(field, '')).strip()
                    if value.casefold() in UNRESOLVED_EXACT_VALUES or UNRESOLVED_MARKER.search(value):
                        errors.append(f'manifest.json {field} contains an unresolved scaffold marker')
        except Exception as exc: errors.append(f'invalid manifest.json: {exc}')
    cfg=original/'tests/config.json'; trace=rev/'conversion_trace.json'
    source=[]
    original_p2p=[]
    if cfg.is_file():
        try: source=parse_list(json.loads(cfg.read_text()).get('fail_to_pass', []))
        except Exception: errors.append('invalid original tests/config.json')
    if not trace.is_file():
        errors.append('missing conversion_trace.json')
    else:
        try:
            payload=json.loads(trace.read_text())
            rows = payload.get("f2p_accounting", [])
            errors.extend(trace_disposition_errors(payload))
            addendum_text = (
                paths.specification_addendum_path.read_text(encoding="utf-8", errors="replace")
                if paths.specification_addendum_path.is_file() else ""
            )
            errors.extend(specification_provenance_errors(payload, addendum_text))
            original_config = json.loads(cfg.read_text()) if cfg.is_file() else {}
            original_p2p = parse_list(original_config.get('pass_to_pass', original_config.get('pass_to_pass_tests', [])))
            candidate_config_path = tests / 'config.json'
            candidate_config = json.loads(candidate_config_path.read_text()) if candidate_config_path.is_file() else {}
            candidate_f2p = parse_list(candidate_config.get('fail_to_pass', []))
            candidate_p2p = parse_list(candidate_config.get('pass_to_pass', candidate_config.get('pass_to_pass_tests', [])))
            delta_selectors, regression_selectors = converted_selector_groups(payload)
            if set(candidate_f2p) != set(delta_selectors):
                missing_from_trace = sorted(set(candidate_f2p) - set(delta_selectors))
                missing_from_config = sorted(set(delta_selectors) - set(candidate_f2p))
                errors.append(
                    'functional delta selector provenance mismatch: '
                    f'config_only={missing_from_trace[:10]}, trace_only={missing_from_config[:10]}'
                )
            p2p_accounting = payload.get('p2p_accounting', {})
            excluded_items = p2p_accounting.get('excluded', []) if isinstance(p2p_accounting, dict) else []
            excluded = [str(item.get('selector')) for item in excluded_items if isinstance(item, dict)]
            if len(excluded) != len(set(excluded)):
                errors.append('duplicate selectors in p2p_accounting.excluded')
            unknown_excluded = sorted(set(excluded) - set(original_p2p))
            if unknown_excluded:
                errors.append('unknown excluded P2P selectors: ' + ', '.join(unknown_excluded[:10]))
            retained_native_p2p, mapping_errors = canonical_retained_p2p(original_p2p, p2p_accounting)
            errors.extend(mapping_errors)
            expected_p2p = append_f2p_regressions(retained_native_p2p, regression_selectors)
            if candidate_p2p != expected_p2p:
                errors.append(
                    'candidate P2P must equal the original P2P list verbatim followed only by converted F2P regressions'
                )
            if (tests / 'test_patch.patch').exists():
                errors.append('historical test_patch.patch must not be bundled into a functional verifier')
            tests_text = '\n'.join(
                path.read_text(encoding='utf-8', errors='replace')
                for path in tests.rglob('*') if path.is_file() and path.name != 'config.json'
            )
            if 'test_patch.patch' in tests_text or 'historical_tests/test_patch' in tests_text:
                errors.append('functional verifier must not apply or depend on the historical test patch')
            accounted_list=[str(x.get("source_f2p")) for x in rows if isinstance(x, dict)]
            accounted=set(accounted_list)
            missing=[x for x in source if x not in accounted]
            if missing: errors.append(f'unaccounted F2P seeds: {len(missing)}')
            duplicates = sorted({item for item in accounted_list if accounted_list.count(item) > 1})
            if duplicates: errors.append(f'duplicate F2P accounting rows: {len(duplicates)}')
            extra = sorted(accounted - set(source))
            if extra: errors.append(f'unknown F2P accounting seeds: {len(extra)}')
            allowed_decisions = {"rewrite", "merge", "drop", "specification_gap"}
            required_row = set(REQUIRED_F2P_FIELDS)
            for row in rows:
                if not isinstance(row, dict):
                    errors.append('F2P accounting row must be an object')
                    continue
                missing_fields = sorted(required_row - set(row))
                if missing_fields:
                    errors.append(f"F2P row {row.get('source_f2p', '<unknown>')} missing fields: {', '.join(missing_fields)}")
                decision = row.get("decision")
                if decision not in allowed_decisions:
                    errors.append(f"unsupported F2P decision: {decision!r}")
                for classification_error in classification_errors(row):
                    errors.append(classification_error)
                if decision in {"rewrite", "merge"} and not row.get("emitted_tests"):
                    errors.append(f"{decision} F2P row has no emitted_tests: {row.get('source_f2p', '<unknown>')}")
                elif decision in {"rewrite", "merge"}:
                    emitted = row.get("emitted_tests")
                    emitted_list = emitted if isinstance(emitted, list) else [emitted]
                    missing_emitted = [
                        str(selector) for selector in emitted_list
                        if not _selector_is_emitted(str(selector), tests)
                    ]
                    if missing_emitted:
                        errors.append(
                            f"{decision} F2P row references absent emitted tests: "
                            + ", ".join(missing_emitted[:10])
                        )
                elif decision == "drop":
                    for field in ("drop_justification", "drop_evidence"):
                        if not str(row.get(field, "")).strip():
                            errors.append(f"drop row {row.get('source_f2p', '<unknown>')} missing {field}")
                elif decision == "specification_gap":
                    for field in ("specification_gap", "specification_proposal", "planned_observable_surface"):
                        if not str(row.get(field, "")).strip():
                            errors.append(f"specification_gap row {row.get('source_f2p', '<unknown>')} missing {field}")
            # Mini-SWE works inside a container and may echo its mounted
            # evidence path. Normalize that equivalent spelling at the
            # controller boundary; the canonical host contract remains stable.
            if payload.get('specification_source') == 'evidence/problem_statement.md':
                payload['specification_source'] = 'source/problem_statement.md'
                trace.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if payload.get('specification_source') != 'source/problem_statement.md':
                errors.append('trace specification source is not problem_statement.md')
        except Exception as exc: errors.append(f'invalid conversion_trace.json: {exc}')
    result={'status':'PASS' if not errors else 'FAIL','errors':errors,'task_root':str(root),'revision':str(rev),'revision_relative':str(rev.relative_to(root)) if rev.is_relative_to(root) else str(rev),'trace':str(trace.relative_to(root)) if trace.is_relative_to(root) else str(trace),'required_test_files':list(REQUIRED_TEST_FILES), 'required_revision_files':list(REQUIRED_REVISION_FILES)}
    write_json(paths.artifact_contract_path, result)
    return result

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--task-root',type=Path,required=True)
    ap.add_argument('--revision',type=Path,required=True)
    ap.add_argument('--execute',action='store_true',help='after artifact checks, run Base/Gold candidate verifier in Docker')
    args=ap.parse_args(argv); paths=resolve_task(args.task_root); root=paths.run_root; original=paths.original; rev=args.revision.resolve()
    contract=artifact_contract(root,rev)
    result={'status':contract['status'],'contract':contract}
    if args.execute and contract['status']=='PASS':
        row_path=paths.source / 'dataset_row.json'
        try:
            row=json.loads(row_path.read_text())
            image=image_name(original,row)
            trace_payload = json.loads((rev / "conversion_trace.json").read_text(encoding="utf-8"))
            expectation = replay_expectation(trace_payload)
            replay=run_docker_preflight(root,image,tests_dir=rev/'tests',log_root=paths.hard_replay_root / 'docker',original_root=original,evidence_root=paths.validation_root,write_compat_results=False,expectation=expectation,stage_original_test_patch=True)
            replay['revision']=str(rev.relative_to(root)) if rev.is_relative_to(root) else str(rev)
            write_json(paths.hard_replay_path,replay)
            result['hard_replay']=replay
            result['status']='PASS' if replay.get('status')=='pass' else 'FAIL'
        except Exception as exc:
            result['status']='FAIL'; result['hard_replay']={'status':'error','error':repr(exc),'revision':str(rev.relative_to(root)) if rev.is_relative_to(root) else str(rev)}
            write_json(paths.hard_replay_path,result['hard_replay'])
    elif args.execute:
        result['hard_replay']={'status':'not_run','revision':str(rev.relative_to(root)) if rev.is_relative_to(root) else str(rev),'reason':'artifact contract failed'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
