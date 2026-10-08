# Experiment design entrypoint

The authoritative design is [`260928plan1.md`](260928plan1.md). This V2
implementation keeps the task's `problem_statement` as the only final solver
instruction, uses Harbor v0.22.0 for Stage 3, and keeps requirements/interface
as converter construction evidence.

`configs/evaluation.yaml` records the A/B/C conditions; evaluation scripts are
intentionally not run until an accepted `final/` task exists.
