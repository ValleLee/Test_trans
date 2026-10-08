# Canonical path contract and controller subprocess repair

- Time: 2026-09-29 08:35:00 UTC
- Scope: shared Stage 2 framework
- Classification: framework-level orchestration/path defect

## Observed phenomenon

A full pipeline launched from the workspace parent could import the top-level
package, but a controller child process could not import `swepro_trans`. After
that was fixed, a relative `--env-file` and `--config` was resolved once by the
caller and then resolved again under the controller's project-root cwd, creating
paths such as `Swepro_test_trans/Swepro_test_trans/configs/experiment.yaml`.
The resulting failures happened before Docker verifier execution.

## Evidence

- The initial pipeline artifact subprocess returned
  `ModuleNotFoundError: No module named 'swepro_trans'`.
- The next run reached artifact validation but Semantic Judge startup failed
  with a duplicated relative configuration path.
- Direct artifact validation, Semantic Judge, hard replay and stability replay
  succeeded when invoked with an explicit project `PYTHONPATH` and absolute
  paths.
- No task image, repository code or verifier test caused either failure.

## Root cause

The framework had multiple command entrypoints with different cwd assumptions.
The parent process used the caller's environment while controller children used
the project root as cwd. Relative CLI arguments were treated as if their base
were stable even though the base changed between processes.

## Generalized repair

- Added `canonical_path` and project-root anchored defaults to the shared path
  module.
- Canonicalized task, revision, env and config paths at every direct CLI
  boundary; the public CLI canonicalizes before forwarding.
- Controller subprocesses now receive absolute paths and inherit
  `PROJECT_ROOT/src` in `PYTHONPATH`.
- Kept Docker mount construction in `TaskPaths`; Docker receives only absolute
  mounts and does not become a second path authority.
- Added an attempt-local `pipeline_runs/` history so controller repair does not
  overwrite the audit trail of a failed revision.

This rule applies to every task and does not inspect instance IDs, repository
names, commits, test names or task-specific paths.

## Changed files

- `src/swepro_trans/paths.py`
- `src/swepro_trans/verifier_conversion.py`
- `src/swepro_trans/pipeline/orchestrator.py`
- `src/swepro_trans/agents/runner.py`
- `src/swepro_trans/validation/semantic.py`
- `src/swepro_trans/qa/runner.py`
- `src/swepro_trans/pipeline/repair.py`
- `docs/framework/20260929_082856_harbor_to_harbor_stage2_architecture.md`

## Validation

- `compileall` passes for the package.
- `swepro-trans pipeline --help` exposes bounded repair controls.
- Artifact validation succeeds from the canonical run root.
- F2P hard replay passes with Base FAIL / Gold PASS.
- Independent P2P replay passes with Base PASS / Gold PASS for two repeats.
- A full pipeline was rerun after the repair; its current trajectory is recorded
  under the active task attempt.

## Residual risk

A caller that bypasses the public CLI and directly invokes an older compatibility
script may still provide its own cwd assumptions. Those wrappers now delegate to
the package; direct module entrypoints normalize their paths as well. New code
must use `canonical_path` instead of resolving relative paths after changing cwd.
