# F2P accounting metric and legacy output cleanup

- Time: 2026-09-29 09:20:51 UTC
- Scope: shared Stage 2 validation and output layout
- Classification: framework-level reporting/layout defect

## Observed phenomenon

The repaired qutebrowser verifier accounted for all 11 historical F2P seeds,
but emitted 9 functional tests because two seed behaviors were merged. The
stability report used a raw selector-count comparison and reported
`f2p_scope_preserved: false`, even though the artifact contract had verified
complete per-seed accounting. The run also contained a stale top-level
`intermediate/preflight` directory from an older pre-attempt implementation and
empty temporary session directories after sandboxes were cleaned.

## Root cause

The report treated “number of emitted tests” as equivalent to “number of
accounted F2P seeds”. The conversion contract permits `merge`/shared functional
tests, so counts can legitimately differ. Older Docker preflight code wrote
compatibility summaries relative to the run root, before the attempt artifact
root was introduced. Temporary parent directories were created eagerly and not
removed after their last sandbox disappeared.

## Generalized repair

- Stability now treats the artifact contract and `conversion_trace.json` as the
authority for F2P scope; it separately records
`f2p_selector_count_changed` and explains that merge is allowed.
- Acceptance rejects a revision if either F2P accounting or exact retained P2P
scope is not preserved.
- Stage 2 Docker calls disable legacy compatibility summaries and write only to
the active attempt's validation tree.
- Converter and QA session parents are removed when their last temporary
sandbox is gone.
- The stale compatibility directory and empty session parents were removed only
from the active qutebrowser run; no other task was touched.

## Validation

- Refreshed rev_004 stability: `pass`, F2P scope accounting `true`, selector
count changed `true`, P2P scope `true`, two repeats.
- Re-ran acceptance: `accepted` for rev_004.
- Regenerated human review: status `complete`, final packaged `true`.
- `compileall` passes.
- Active run has no empty directories and no top-level legacy intermediate.

## Residual risk

A future compatibility caller that explicitly requests legacy Stage 1 preflight
summaries may still create its own `preflight` directory. Stage 2 uses the
attempt-scoped option and the output contract documents that distinction.
