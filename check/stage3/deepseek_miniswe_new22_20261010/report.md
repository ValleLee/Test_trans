# Stage 3 run report — deepseek_miniswe_new22_20261010

Generated: 2026-10-09T19:44:35+00:00

## Two instruction cohorts

| Measure | Original instruction | Converted instruction |
|---|---:|---:|
| Planned | 22 | 22 |
| Nonempty patches | 21 | 21 |
| Two valid verifier results | 20 | 20 |
| Original verifier PASS | 20 | 12 |
| Functional verifier PASS | 20 | 17 |
| No patch | 1 | 1 |
| Replay errors | 1 | 1 |
| Input tokens | 38897032 | 48012377 |
| Cache tokens | 38080512 | 47091840 |
| Output tokens | 456215 | 428266 |
| Native vs regrade comparable | 20 | 20 |
| Native vs regrade disagreements | 0 | 0 |

## Paired verifier verdicts

### original

| Original verifier | Functional PASS | Functional FAIL |
|---|---:|---:|
| PASS | 20 | 0 |
| FAIL | 0 | 0 |

### converted

| Original verifier | Functional PASS | Functional FAIL |
|---|---:|---:|
| PASS | 12 | 0 |
| FAIL | 5 | 3 |

## Paired instruction comparison

Only tasks with valid results for both instruction cohorts enter each comparison.

| Verifier and task subset | Paired tasks | Original instruction PASS | Converted instruction PASS | Difference |
|---|---:|---:|---:|---:|
| original_verifier | 19 | 19 | 11 | -42.1% |
| functional_verifier | 19 | 19 | 16 | -15.8% |
| deletion_only_original_verifier | 19 | 19 | 11 | -42.1% |
| deletion_only_functional_verifier | 19 | 19 | 16 | -15.8% |
| clarification_original_verifier | 0 | 0 | 0 | N/A |
| clarification_functional_verifier | 0 | 0 | 0 | N/A |

## Semantic review

- Disagreements: 5
- Reviewed: 5; unreviewed: 0; uncertain: 0
- Confirmed rescues: 5
- Confirmed false rejections: 0

Harbor reports zero USD for this custom model; actual API charges are unavailable.
See `aggregate.json`, `semantic_review_queue.json`, per-task `analysis.json`, trajectories, patches, and replay logs.
