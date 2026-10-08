# Uncertified legacy skip hid a newer failed attempt

## Symptom
The Stage 2 plan for `task_list/stage2_python_next20.txt` marked the qutebrowser `6dd402...` task as `already_converted`, even though its latest attempt was not accepted. The older attempt had a published final package without an independent audit. This prevented the next batch from continuing a task whose latest work had failed.

## Evidence
- `runs/instance_qutebrowser__qutebrowser-6dd402c0d0f7665d32a74c43c5b4cf5dc8aff28d-v5fc38aaf22415ab0b70567368332beee7955b367` contains an accepted `attempt_001` followed by a non-accepted latest attempt.
- Read-only `final_audit.audit_task` reports the latest attempt as not accepted, with missing final files and Stage 2 gates.
- The previous batch planner nevertheless returned the `attempt_001/final` as reusable because its legacy acceptance had no explicit audit failure.

## Classification and root cause
Framework-level state-selection defect. Both batch selection helpers treated the latest *published accepted* attempt as sufficient for legacy packages, without checking whether a later attempt existed and failed. This general ordering bug can hide unresolved work for any task, independent of repository or language.

## General fix
Keep the explicit no-rerun rule for any attempt with independent audit PASS. For uncertified legacy packages, do not reuse an older accepted final if a newer attempt is incomplete or non-accepted. Apply the rule in both the batch launcher and guarded retry scheduler.

## Files changed
- `scripts/run_stage2_batch.py`
- `scripts/run_guarded_stage2_retry.py`
- `tests/test_stage2_skip_audited.py`

## Verification
`PYTHONPATH=src:. .venv/bin/pytest -q tests/test_stage2_skip_audited.py` -> 3 passed. The existing test still confirms an older independently audited PASS is reused after a later rejection.

## Residual risk
Accepted legacy packages with no newer failed attempt remain reusable by the scheduler; they still require independent audit before being reported as certified.
