# QA effective specification and repair-feedback consistency (20261007T095941Z)

## Symptom

OpenLibrary `attempt_008/rev_015` failed Negative QA because a candidate removed the English Wikipedia fallback and the judge classified that implementation as equivalent to the task. The effective instruction for that revision includes a controller-approved addendum requiring English fallback when the requested-language sitelink is absent. The candidate therefore violated the effective contract.

## Evidence

- `runs/instance_internetarchive__openlibrary-5fb312632097be7e9ac6ab657964af115224d15d-v0f5aece3601a5b4419f7ccec1dbda2071be28ee4/attempts/attempt_008/intermediate/qa/negative/summary.json`: candidate was classified `verifier_false_positive` with judge verdict `EQUIVALENT`.
- Its `judge.json` says the candidate may omit English fallback because the base PR text did not require it.
- `qa/session.py` staged only `source/problem_statement.md` for the candidate generator; `qa/runner.py` also supplied only base P in Judge evidence, adding the controller addendum only after a `RELEVANT_NON_EQUIVALENT` verdict for quote validation.
- The candidate patch removes English fallback, while the effective addendum explicitly requires it.
- Existing P2P accounting for this task records all 7 original P2P selectors retained with zero exclusions.

## Failure classification

Framework-level. Positive and Negative QA must judge candidates against the same effective solver contract used by packaging and semantic review. Supplying only base P can produce a false positive from an addendum-violating candidate.

## Root cause

QA generation and the initial candidate Judge evidence did not compose the controller-approved behavior addendum into `problem_statement.md`. The post-judge quote check used the addendum only for one verdict class, too late to prevent an incorrect `EQUIVALENT` judgment.

## General repair

- Added a shared effective-Problem-Statement composer in `qa/session.py`.
- Stage both base P and the effective P into the QA sandbox; candidate generators read the effective file.
- Candidate Judge evidence now uses that same effective text, and grounding no longer appends the addendum a second time.
- Updated Positive/Negative Judge prompts to identify controller-approved addenda as normative.
- REPAIR instructions now treat prior repair objectives as historical evidence and revalidate them against current P/schema/gate evidence.
- P2P selector mismatch diagnostics explicitly forbid fabricating PASS from a same-file/same-leaf name match.

## Files changed

- `src/swepro_trans/qa/session.py`
- `src/swepro_trans/qa/runner.py`
- `src/swepro_trans/pipeline/repair.py`
- `prompts/judges/positive.md`
- `prompts/judges/negative.md`
- `tests/test_qa_judge_evidence.py`
- `tests/test_repair_feedback.py`

## Verification

`PYTHONPATH=src .venv/bin/pytest -q tests/test_qa_judge_evidence.py tests/test_qa_judge_gate.py tests/test_repair_feedback.py tests/test_p2p_native_selector_mapping.py` — 14 passed.

## Residual risk

QA candidates generated before this repair were judged under incomplete P in tasks with a controller addendum. New repairs must generate and judge fresh candidates under the effective P. Existing attempts and their artifacts remain unchanged.
