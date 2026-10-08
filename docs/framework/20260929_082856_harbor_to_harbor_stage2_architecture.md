# Harbor-to-Harbor Stage 2 Conversion Architecture

- Generated: 2026-09-29 08:28:56 UTC
- Status: current implementation contract
- Scope: SWE-bench Pro V2 Harbor tasks that passed Stage 1

## 1. Objective and authority

Stage 2 keeps the Harbor task shape and converts only the verifier. The
converter must preserve the historical F2P scope while changing assertions to
check functional behavior through public or observable surfaces.

The authority order is fixed:

1. `source/problem_statement.md` defines functional semantics;
2. historical F2P defines which behavior is in scope;
3. Requirements, Interface, historical tests, P2P, repository and Gold are
   construction or validation evidence;
4. the Base repository establishes whether a referenced surface already exists;
5. Gold can provide a known-good construction and replay state, but cannot add
   requirements to the specification.

The final Harbor instruction is derived by removing only the `## Requirements`
and `## New Interfaces` sections from the original instruction. Other text is
retained verbatim, including the repository preamble, PR wrapper and
constraints.

## 2. Runtime roles and gate ownership

The model and deterministic controller have different responsibilities:

```text
mini-swe Converter
  ├─ inspect evidence in a disposable sandbox
  ├─ write one revision
  └─ perform local self-review
       │
       ▼
controller (host process, canonical project root)
  ├─ artifact/schema/F2P accounting
  ├─ external Semantic Judge
  ├─ Docker hard replay: Base FAIL, Gold PASS
  ├─ Docker P2P replay: Base PASS, Gold PASS
  ├─ repeated stability replay
  ├─ Positive QA: alternative valid implementation
  ├─ Negative QA: targeted near-correct mutant
  └─ acceptance and final packaging
```

The external Semantic Judge and deterministic gates are authoritative. A
mini-swe self-review is useful feedback, but cannot waive a controller gate.
When a gate fails, the controller writes structured evidence, allocates the
next revision in the same attempt, invokes mini-swe with that feedback, and
replays all gates from Semantic Judge onward. The loop is bounded by
`--max-revisions`.

The controller never changes verifier semantics to hide an infrastructure
failure. Failures are classified before changing shared code.

## 3. Single path contract

There are two host-side roots with distinct ownership:

```text
tasks/<instance_id>/original/       immutable Stage 1 Harbor task
runs/<instance_id>/source/          selected Stage 1 evidence, one owner
runs/<instance_id>/attempts/        isolated framework attempts
```

A run has this shape:

```text
runs/<id>/
├── source/
├── attempts/
│   └── attempt_NNN/
│       ├── intermediate/
│       │   ├── converter/revisions/rev_NNN/
│       │   ├── converter/trajectory/
│       │   ├── validation/
│       │   │   ├── sanity/
│       │   │   ├── semantic/
│       │   │   ├── hard_replay/
│       │   │   ├── stability/
│       │   │   ├── pipeline_runs/
│       │   │   ├── qa/positive/
│       │   │   ├── qa/negative/
│       │   │   └── acceptance.json
│       │   ├── packaging/
│       │   └── control/
│       ├── review/
│       ├── final/                 created only after acceptance
│       └── layout_manifest.json
├── latest_attempt.json
└── run_manifest.json
```

`TaskPaths` is the only source of task and artifact paths. Every CLI path
argument is canonicalized once at the command boundary. Defaults for `.env`
and YAML configuration are project-root anchored. Controller subprocesses
receive absolute paths and inherit `PROJECT_ROOT/src` in `PYTHONPATH`.
Modules must not reinterpret a relative path after changing cwd.

Docker receives only absolute mounts generated from `TaskPaths`; the image's
`/app` or `/testbed` is discovered by the task's runner. The host controller
and the image runtime are separate boundaries: Docker isolation does not remove
the need for a host-side path contract.

## 4. Revision artifact contract

A submitted revision contains only the Harbor verifier and conversion evidence:

```text
rev_NNN/
├── tests/test.sh
├── tests/run_script.sh
├── tests/parser.py
├── tests/config.json
├── conversion_trace.json
├── self_review.md
└── manifest.json
```

`conversion_trace.json` accounts for every original F2P selector exactly once.
P2P selectors remain separate and are retained as regression scope. Extra
controller feedback files may exist in a failed repair revision, but are never
published into `final/`.

## 5. Gate order

Each revision follows this order and does not skip earlier gates:

```text
artifact/schema/accounting
        ↓
Semantic Judge + Base observability/binding checks
        ↓
F2P hard replay: Base FAIL, Gold PASS
        ↓
P2P hard replay: Base PASS, Gold PASS
        ↓
repeat F2P/P2P stability checks
        ↓
Positive QA and Negative QA
        ↓
acceptance
        ↓
final Harbor package + human review projection
```

The F2P and P2P suites use the task's own `tests/test.sh`, `run_script.sh`,
`parser.py`, image and network policy. Stage 2 does not invent language-specific
runners.

## 6. QA and repair semantics

Positive QA asks mini-swe to construct a materially different correct
implementation. A fresh Judge checks semantic validity and structural
non-equivalence; paired replay records both the original and functional
verifier results.

Negative QA asks mini-swe to create a near-correct implementation that violates
one F2P-supported semantic. A fresh Judge confirms the intended defect, and the
functional verifier must reject it. Generation retries are bounded per branch.

For any failed gate, `validation/repair_feedback.json` contains the failed
stage and compact structured evidence. The controller allocates a new
`rev_NNN`, passes the feedback to mini-swe, and stores one history report under
`validation/pipeline_runs/`. This keeps repair auditable without mixing failed
revisions with the published artifact.

## 7. Review and publication

`attempt_NNN/review/` is a read-only human projection containing metrics, F2P
mapping and a conversion report. It cannot override acceptance. `final/` is
created only when artifact, Semantic Judge, hard F2P/P2P replay, stability,
positive QA and negative QA all pass for the same revision.

Stage 1 failures remain in Stage 1 data and do not receive a `runs/<id>`
entry. No `problem_case` directory is used by Stage 2.

## 8. Failure classification rule

Before changing shared code, record:

- observed phenomenon and evidence;
- failure category (semantic, artifact, path, Docker, execution, QA or
  packaging);
- why it is framework-level rather than instance-specific;
- the generalized rule and affected modules;
- regression validation and residual risk.

These records live in `docs/process/` with UTC timestamps.
