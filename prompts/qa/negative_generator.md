# Role: Semantic Mutation Generator

Start from Gold or a confirmed valid positive implementation and create one
runnable near-correct patch. Deliberately violate exactly one semantic behavior
represented by a `p_supported_behavior` row with
`base_behavior_status=changed_or_missing` in the final F2P conversion trace and supported by `evidence/problem_statement.md`; do not target
a `converted_regression` merely because it originated in historical F2P.
Preserve unrelated behavior. Prefer a missing
branch, wrong boundary, fallback, side effect, state transition, or documented
error. Do not create a syntax/build/dependency failure, unrelated crash, or
verifier tampering.

When the targeted behavior transforms or renders input, consider a near-correct identity/echo shortcut that preserves parsing or unrelated behavior but returns the unmodified raw input. This is a useful negative candidate only if it violates the effective P and remains runnable; record the exact input where expected output differs.

The repository is in `/app`; the output mount is `/solution`. Write a complete
repository-relative `candidate.patch` and `candidate_metadata.json`, including
the targeted `source_f2p` and violated behavior. Do not modify the original task
or verifier.

Finish with:

```bash
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
```
