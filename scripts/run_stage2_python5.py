#!/usr/bin/env python3
"""Run the selected Stage 2 Python conversions with five isolated workers."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
IDS = [line.strip() for line in (ROOT / os.environ.get('STAGE2_IDS_FILE', 'task_list/stage2_python5.txt')).read_text().splitlines() if line.strip()]
OUT = ROOT / 'data/stage2_python5'
OUT.mkdir(parents=True, exist_ok=True)
ENV = os.environ.copy()
ENV['PYTHONPATH'] = str(ROOT / 'src')


def agent_active(task: Path) -> bool:
    marker = str(task).encode()
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            parts = (proc / 'cmdline').read_bytes().split(b'\0')
        except (OSError, PermissionError):
            continue
        if b'agent' in parts and b'swepro_trans' in parts and marker in parts:
            return True
    return False


def run_one(instance_id: str) -> dict:
    task = ROOT / 'tasks' / instance_id
    revision = ROOT / 'runs' / instance_id / 'attempts/attempt_001/intermediate/converter/revisions/rev_001'
    log_dir = OUT / instance_id
    log_dir.mkdir(parents=True, exist_ok=True)
    result = {'instance_id': instance_id, 'started_at_utc': datetime.now(timezone.utc).isoformat()}
    agent_report = revision / 'agent_session.json'
    if not agent_report.exists() and agent_active(task):
        result['agent_origin'] = 'resumed_existing_process'
        while not agent_report.exists() and agent_active(task):
            time.sleep(5)
    if agent_report.exists():
        report = json.loads(agent_report.read_text())
        result['agent_status'] = report.get('status')
        result['agent_exit_code'] = 0 if report.get('status') == 'submitted' else 1
    else:
        cmd = [sys.executable, '-m', 'swepro_trans', 'agent', '--task-root', str(task), '--revision', str(revision)]
        with (log_dir / 'agent.log').open('a') as log:
            proc = subprocess.run(cmd, cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT, check=False)
        result['agent_exit_code'] = proc.returncode
    result['agent_log'] = str((log_dir / 'agent.log').relative_to(ROOT))
    (log_dir / 'status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    if result['agent_exit_code'] == 0:
        pipeline_report = ROOT / 'runs' / instance_id / 'attempts/attempt_001/intermediate/validation/stage2_pipeline.json'
        if pipeline_report.exists() and json.loads(pipeline_report.read_text()).get('status') == 'complete':
            result['pipeline_exit_code'] = 0
        else:
            cmd = [sys.executable, '-m', 'swepro_trans', 'pipeline', '--task-root', str(task), '--revision', str(revision)]
            with (log_dir / 'pipeline.log').open('a') as log:
                proc = subprocess.run(cmd, cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT, check=False)
            result['pipeline_exit_code'] = proc.returncode
            result['pipeline_log'] = str((log_dir / 'pipeline.log').relative_to(ROOT))
    result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    (log_dir / 'status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=int(os.environ.get('STAGE2_WORKERS', '5'))) as pool:
        jobs = {pool.submit(run_one, id_): id_ for id_ in IDS}
        for job in as_completed(jobs):
            result = job.result()
            print(json.dumps(result, ensure_ascii=False), flush=True)
