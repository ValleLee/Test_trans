# Verifier conversion stage execution contract

The V2 adapter keeps the Harbor task as the source of truth. The Converter sees
`problem_statement.md`, raw requirements/interface, historical test patch and
selectors, Gold patch, repository and environment. The solver-facing instruction
is always copied from `problem_statement.md`; no instruction rewrite is emitted.

A revision is submitted under `runs/<instance_id>/intermediate/converter/revisions/rev_NNN/` and
must contain `tests/` plus a conversion trace accounting for every historical
F2P seed. The model-driven Converter is launched through the project-local
Python 3.12 environment:

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans agent \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN
```

It uses `mini-swe-agent==2.4.6`, the copied `.env` endpoint profile, the
official Harbor image's `/app`, and read-only P-only construction evidence
mounts. `scripts/validate_verifier_revision.py` performs the deterministic
artifact gate.
Only an accepted revision can be passed to `swepro_trans package`; that command
copies the original Harbor environment/solution and the P-only instruction into
`runs/<instance_id>/final/` and installs the functional verifier tests.

## Deterministic gate order

For `runs/<instance_id>/intermediate/converter/revisions/rev_NNN/`:

```bash
python3 scripts/validate_verifier_revision.py \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN \
  --execute

# After semantic review, positive QA, and negative QA have each written a
# status=pass summary:
python3 scripts/accept_verifier_revision.py \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN

PYTHONPATH=src python3 -m swepro_trans package \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN
```

The validator fails closed if any F2P seed lacks a conversion-trace entry or if
required verifier files are missing. `--execute` runs the candidate tests once
against Base and Gold in Docker and records `hard_replay/result.json`. Packaging
also requires `validation/acceptance.json` with all deterministic, semantic,
positive-QA and negative-QA statuses set to `pass`.

## Semantic-first gate

The recommended Stage 2 order is now the following:

```bash
# 1. cheap artifact/F2P contract (no Docker replay)
PYTHONPATH=src .venv/bin/python scripts/validate_verifier_revision.py \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN

# 2. read-only LLM semantic Judge, including a Base-repository symbol probe
PYTHONPATH=src .venv/bin/python scripts/run_semantic_review.py \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN

# 3. only after verdict=PASS, run the expensive Base/Gold replay
PYTHONPATH=src .venv/bin/python scripts/validate_verifier_revision.py \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN \
  --execute
```

The combined controller is:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_stage2_pipeline.py \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN
```

Requirements and interface can identify a useful public surface, but the Judge
accepts it only when the surface is already observable in the Base repository
and the behavior is supported by the Problem Statement. A class/function
explicitly introduced by P may be new, but the verifier must exercise its
specified behavior; existence/type alone is insufficient. A Gold-only symbol
or a historical-test-only serialization/API contract remains a conversion
defect.
