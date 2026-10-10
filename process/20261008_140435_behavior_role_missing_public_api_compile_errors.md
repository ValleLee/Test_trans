# Behavior-role gate: Base missing public API was mislabeled as ERROR

- UTC: 2026-10-08 14:04:35
- Scope: framework-level validation classification
- Affected task evidence: Vuls `instance_future-architect__vuls-54e73c2f5466ef5daec3fb30922b9ac654e4ed25`, `attempt_001/rev_009`

## Symptom

The semantic review and Base/Gold hard replay passed for `rev_009`, but `behavior_roles` rejected 11 converted F2P selectors. Base's Go test package did not compile because the Base `VulnInfos` type lacks the filter methods invoked by the emitted tests; Gold compiled and passed all 11 selectors. The parser marked Base selectors `ERROR`, while the role gate only accepted `FAILED` as functional-delta evidence.

## Evidence and root cause

`hard_replay/result.json` shows `returncode=1` for Base and compiler diagnostics such as `input.FilterByCvssOver undefined (type VulnInfos has no field or method FilterByCvssOver)`. The diagnostic source lines map to calls inside the matching emitted test functions. Gold has `returncode=0` and all 11 selectors pass. P describes moving the filtering helpers onto the `VulnInfos` collection, which is the public surface exercised by those tests.

The role audit compared status labels literally and did not distinguish a product API absent on Base from a Docker/runner failure or unrelated test compile error. The converter had already exhausted eight revisions; this was a false rejection in the shared role gate, not a new converter defect.

## Generic repair

`src/swepro_trans/validation/behavior_roles.py` now recognizes a missing-Go-method compile diagnostic as `MISSING_PUBLIC_API` only when all of these hold: Base returned nonzero; the compiler diagnostic points to a Go source file emitted under the current revision's `tests`; the diagnostic line is inside the same emitted test function as the selector; and that function contains the named method call. All other `ERROR` statuses remain errors. Raw statuses and the diagnostic evidence are preserved in the audit JSON.

## Verification

- `PYTHONPATH=src .venv/bin/pytest -q tests/test_behavior_roles.py`: 10 passed. Tests cover a matching missing API diagnostic, a diagnostic in the wrong test function, and a Docker/environment error.
- Re-ran behavior-role audit on Vuls `54e73c2f` `rev_009`: PASS; 11 functional-delta selectors, all 11 Gold PASS, Base statuses supported by matching missing-public-method diagnostics.

## Next action and residual risk

The existing Vuls `rev_009` still needs the downstream stability, Positive/Negative QA, packaging, final audit, and framework-external audit gates. It is queued for a no-auto-repair pipeline revalidation after a task slot opens; no converter regeneration is planned. This classifier currently recognizes Go missing-member compiler diagnostics only. Other language adapters remain conservative: their `ERROR` results are not reclassified without equivalent source-mapped evidence and tests.
