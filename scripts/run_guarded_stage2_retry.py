"""Launch an isolated Stage 2 retry while at most N pipelines are alive.

The scheduler may exit after its configured jobs finish. Count live pipeline
processes under a filesystem lock instead of waiting for its status timestamp.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def live_pipelines() -> int:
    """Count this workspace's live `swepro_trans pipeline` entrypoints."""
    count = 0
    root = os.fsencode(str(ROOT))
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args = path.read_bytes().split(b'\0')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if not any(root in arg for arg in args):
            continue
        if any(args[i:i + 3] == [b'-m', b'swepro_trans', b'pipeline']
               for i in range(len(args) - 2)):
            count += 1
    return count


def completed_conversion(instance: str) -> bool:
    """Preserve certified PASS and legacy accepted packages across retries."""
    attempts = sorted((ROOT / 'runs' / instance / 'attempts').glob('attempt_*'))
    published = []
    for attempt in attempts:
        final = attempt / 'final'
        if not (final / 'instruction.md').is_file() or not (final / 'task.toml').is_file():
            continue
        try:
            state = json.loads((attempt / 'intermediate/control/state.json').read_text())
        except (OSError, ValueError):
            continue
        if state.get('status') == 'accepted':
            published.append(attempt)

    def audit(attempt: Path, name: str) -> str | None:
        try:
            return json.loads((attempt / 'review' / name).read_text()).get('status')
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            return 'INVALID'

    if any(audit(attempt, 'independent_audit.json') == 'PASS'
           and audit(attempt, 'final_audit.json') != 'FAIL'
           for attempt in published):
        return True
    if not published:
        return False
    latest = published[-1]
    if not all(audit(latest, name) not in {'FAIL', 'INVALID'}
               for name in ('independent_audit.json', 'final_audit.json')):
        return False
    all_attempts = sorted((ROOT / 'runs' / instance / 'attempts').glob('attempt_*'))
    if all_attempts and all_attempts[-1].name > latest.name:
        try:
            newer_state = json.loads((all_attempts[-1] / 'intermediate/control/state.json').read_text())
        except (OSError, ValueError):
            return False
        if newer_state.get('status') != 'accepted':
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('instance')
    parser.add_argument('attempt')
    parser.add_argument('marker')
    parser.add_argument('--batch', default='stage2_python20_20261006T131302Z')
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error('--limit must be positive')
    batch = ROOT / 'data/stage2_batches' / args.batch
    attempt = ROOT / 'runs' / args.instance / 'attempts' / args.attempt
    revision = attempt / 'intermediate/converter/revisions/rev_001'
    if not revision.is_dir():
        raise FileNotFoundError(revision)
    status = batch / args.marker / 'recovery_retry/status.json'
    log = attempt / 'review/retry_pipeline.log'
    started = now()
    write(status, {'status': 'running', 'instance_id': args.instance,
                   'attempt': args.attempt, 'phase': 'slot_reserved',
                   'started_at_utc': started})
    lock_path = batch / 'guarded_slots.lock'
    lock_path.touch(exist_ok=True)
    while True:
        with lock_path.open('r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if completed_conversion(args.instance):
                write(status, {'status': 'skipped_existing_success',
                               'instance_id': args.instance, 'attempt': args.attempt})
                return 0
            if live_pipelines() < args.limit:
                env = os.environ.copy()
                env['PYTHONPATH'] = str(ROOT / 'src')
                command = [str(ROOT / '.venv/bin/python'), '-m', 'swepro_trans',
                           'pipeline', '--task-root', str(attempt),
                           '--revision', str(revision), '--max-revisions', '8',
                           '--agent-timeout-seconds', '3600']
                with log.open('w') as out:
                    proc = subprocess.Popen(command, cwd=ROOT, env=env,
                                            stdout=out, stderr=subprocess.STDOUT,
                                            start_new_session=True)
                write(status, {'status': 'running', 'instance_id': args.instance,
                               'attempt': args.attempt, 'phase': 'pipeline',
                               'pid': proc.pid, 'started_at_utc': started})
                break
        time.sleep(10)
    code = proc.wait()
    write(status, {'status': 'complete', 'instance_id': args.instance,
                   'attempt': args.attempt, 'exit_code': code,
                   'finished_at_utc': now()})
    return code


if __name__ == '__main__':
    raise SystemExit(main())
