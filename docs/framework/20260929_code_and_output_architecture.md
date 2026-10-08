# 2026-09-29 Code and Output Architecture

## Purpose

This document is the current architecture contract for the Harbor-to-Harbor
Stage 2 converter. It describes where behavior is implemented, which command
interfaces are stable, and which run artifacts are authoritative.

## 1. Code ownership

`src/swepro_trans` is the application package. `scripts` contains only thin
compatibility wrappers for existing shell commands. New behavior belongs in the
package, not in a script.

```text
src/swepro_trans/
├── cli.py                       public `swepro-trans` command
├── paths.py / layout.py         compatibility exports for the storage contract
├── storage/                     TaskPaths, run initialization and publication
├── agents/                      mini-swe sessions, model clients and workspace tools
├── converter/                   converter-facing public API
├── pipeline/                    ordered Stage 2 orchestration
├── validation/                  artifact, semantic, deterministic and acceptance gates
├── qa/                          positive/negative candidate generation and replay
├── reporting/                   human-review projections
├── packaging/                   final Harbor task publication API
├── runtime/                     Docker, Stage 1 bridge and environment helpers
├── evaluation/                  evaluation-facing compatibility API
└── controller/                  pipeline controller compatibility API
```

The intended dependency direction is:

```text
cli → pipeline/controller
pipeline → converter, validation, qa, packaging, reporting
converter/qa/validation → agents, runtime, storage
all domain modules → storage paths
reporting → read-only run artifacts
```

A domain module must not import a top-level script. The Stage 1 preparation
helpers are accessed only through `runtime.stage1`, which is the single adapter
boundary for that legacy preparation module.

## 2. Command boundary

The canonical command is:

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans <command> ...
```

Supported commands are `init`, `agent`, `validate`, `semantic-review`, `qa`,
`accept`, `review`, `pipeline`, and `package`. The existing files in
`scripts/` remain callable, but each is now a compatibility wrapper to the
corresponding package module.

## 3. Run ownership and output contract

Only tasks selected for Stage 2 have a directory under `runs/`. The immutable
source task stays under `tasks/<id>/original`; Stage 1 evidence is promoted once
into `runs/<id>/source` when `init` selects the task.

```text
runs/<id>/
├── source/                         fixed Stage 1 evidence for this run
├── intermediate/
│   ├── converter/
│   │   ├── revisions/rev_NNN/      submitted verifier revisions
│   │   ├── trajectory/             mini-swe trajectories
│   │   └── conversion_trace.json   F2P/P2P accounting
│   ├── validation/
│   │   ├── sanity/                 artifact contract
│   │   ├── semantic/               semantic Judge and binding gate
│   │   ├── hard_replay/             Base/Gold and deterministic replay
│   │   ├── stage2_pipeline.json    ordered gate report
│   │   └── acceptance.json          authoritative acceptance decision
│   ├── qa/
│   │   ├── positive/                alternative correct solution evidence
│   │   └── negative/                near-correct mutant evidence
│   ├── packaging/                   package report
│   └── control/                     state and event log
├── review/                          compact human audit projection
├── final/                            published Harbor task, only after acceptance
└── layout_manifest.json             schema and ownership declaration
```

Directories for candidates, sessions, and replay logs are created only by the
stage that emits them. `init` does not create speculative empty folders.

## 4. Authoritative records

- `source/` is input evidence, never a generated verdict.
- `intermediate/validation/acceptance.json` decides whether publication is allowed.
- `final/` is the only distributable converted task.
- `review/metrics.json`, `review/f2p_mapping.csv`, and
  `review/conversion_report.md` are human-readable projections; they do not
  override gate results.
- `layout_manifest.json` documents ownership and relative paths for tooling.

## 5. Compatibility policy

The old script paths are intentionally retained for one transition period. They
must remain thin wrappers and must not acquire new business logic. New callers
should use `swepro-trans` or import the package APIs.
