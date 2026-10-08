# Stage 2 pipeline contract

The Stage 1 Harbor task remains the source and destination format. Stage 2
changes only the verifier test bundle and writes the solver instruction from
`runs/<instance_id>/source/problem_statement.md`; `requirements.md` and
`interface.md` never enter `final/instruction.md`.

## Roles

| Role | Implementation | Writable output | Gate |
|---|---|---|---|
| Converter / Repair | mini-swe-agent in the official task image | `revisions/rev_NNN/` | trace + tests submitted |
| Semantic Judge | read-only LLM call | `validation/semantic/review.json` | P support + Base observability |
| Hard Validator | deterministic Docker script | `validation/hard_replay/` | Base FAIL, Gold PASS |
| Positive Generator | mini-swe-agent | `qa/positive/candidates/` | patch submitted |
| Positive Judge | fresh read-only LLM call | `qa/positive/candidates/*/judge.json` | `VALID` |
| Negative Generator | mini-swe-agent | `qa/negative/candidates/` | one semantic mutant |
| Negative Judge | fresh read-only LLM call | `qa/negative/candidates/*/judge.json` | `RELEVANT_NON_EQUIVALENT` |
| QA Replay | deterministic Docker script | `qa/*/replay/` | functional verdict matches kind |

The mini-SWE Docker session has one writable bind mount, `/solution`. The
container creates `/workspace/output`, `/workspace/verifier`, and `/verifier`
as symlinks to that path for compatibility. No role receives a host path.

## Gate order

`run_stage2_pipeline.py` executes the following and stops at the first failed
gate:

1. artifact/schema/F2P accounting check;
2. semantic Judge, including a whole-repository Base probe and Gold-only
   binding gate. A new class/function explicitly named by P may be introduced,
   but an existence-only assertion cannot satisfy P when it also states behavior;
3. Base/Gold Docker replay using the task's declared verifier network policy;
4. Positive mini-SWE generation, fresh Judge, and paired original/functional
   replay;
5. Negative mini-SWE generation, fresh Judge, and functional replay;
6. acceptance and final Harbor package.

A semantic rejection is a converter repair signal. A positive false negative or
negative false positive is also a converter repair signal. A malformed Judge
response is `UNCERTAIN` after one strict JSON retry and never counts as a pass.
Every gate result carries the revision-relative path. Starting a new run marks
old hard-replay, QA, and acceptance files as `not_run`, so results from an older
revision cannot be reused accidentally. The Base repository probe searches the
whole Harbor worktree; it does not assume a repository-specific source path.

## Reproducible command

```bash
PYTHONPATH=src .venv/bin/python scripts/run_stage2_pipeline.py \
  --task-root tasks/<instance_id> \
  --revision runs/<instance_id>/intermediate/converter/revisions/rev_NNN
```

Use `--no-qa` only for a diagnostic hard replay. It never creates an accepted
package.
