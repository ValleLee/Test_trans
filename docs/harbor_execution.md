# Harbor execution contract

The pinned official Harbor source is `upstream/harbor` at tag `v0.22.0`, commit
`4407eb5227a2ff4f0d3f16b2eb48849382fdf276`. The release task tree is pinned
separately in `upstream/SWE-bench_Pro-os`.

The official V2 release gate uses Harbor 0.22 with the `oracle` agent. The
local equivalent command is:

```bash
# Requires Python >= 3.12 and the Harbor v0.22.0 CLI.
harbor run -p Swepro_test_trans/tasks \\
  -i <instance_id> -e docker -n 1 -a oracle \\
  --job-name swepro-v2-oracle
```

The wrapper [`scripts/run_official_harbor_oracle.py`](../scripts/run_official_harbor_oracle.py)
constructs this command and fails explicitly when the official CLI is absent.
It does not silently replace Harbor with another runner.

The current host has Python 3.10 and no Harbor CLI, so the five representative checks
(the original four plus the OpenLibrary replacement) used the task-provided official `tests/test.sh`, `run_script.sh`, `parser.py`
and `config.json` inside the published task image. Stage 1 evidence is stored under `data/stage1/<id>`; it is copied to a run only when Stage 2 starts. The fallback now reads each
task's `[verifier].network_mode`; `public` maps to Docker `bridge` and `none`
remains isolated. This makes the local check close to Harbor's verifier phase,
but it is still not a claim that the Harbor CLI itself ran. Stage 3 should use
the pinned Harbor command above.

## Navidrome replay finding

The Navidrome task remains a Stage 1 rejected task and is excluded from Stage 2 `runs/`. With the task's declared
`[verifier] network_mode = "public"` mapped to Docker `bridge`, the official
`tests/test.sh` applies the test patch but its `run_script.sh` exits with
`go: command not found` inside the published image. Base and Gold therefore
both fail before executing `TestCache`; the Gold patch applies cleanly. This is
recorded as `published_image_missing_go_runtime` in the Stage 1 preflight report and is
not converted into a false Oracle pass. Since it is not Stage 1 READY, no Stage 2
run directory is created for it.
