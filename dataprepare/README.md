# SWE-bench Pro V2 Stage 1

The active 100-task selection is `../task_list/selected_100.txt`. It retains
all 20 pilot IDs and tracks the official language mix with Python 40, Go 36, JavaScript 22,
and TypeScript 2. The selection method and per-task HARD-51 labels are in
`../task_list/selection_report.json`. The sample includes two official HARD tasks in each main language and
no TypeScript HARD task. HARD-51 is based on frontier-run failure modes; a non-HARD label is not evidence that a particular model solved a task.

The official Harbor tasks are fixed to
`scaleapi/SWE-bench_Pro-os@66f92766bba642462d4bbe5479e83f91f9211862`.
The cached structured rows are `../data/dataset_rows.json` (V2 version 2.0.0).
Each original is copied to `../tasks/<id>/original/`; per-task source hashes,
row hashes, image digests, and Base/Gold evidence are stored under
`../data/stage1/<id>/`. Originals are not rewritten by the preparer.

Run from the project root:

```bash
python3 task_list/select_v2_100.py
python3 dataprepare/prepare_swebench_pro_v2.py --ids-file task_list/selected_100.txt
python3 dataprepare/pull_selected_images.py --workers 4
python3 dataprepare/preflight_selected.py --workers 4
python3 dataprepare/reselect_oracle_failures.py # rerun selection/fetch/pull/preflight if needed
python3 dataprepare/prepare_swebench_pro_v2.py --ids-file task_list/selected_100.txt
python3 dataprepare/archive_unselected.py
python3 dataprepare/audit_stage1.py
```

The image downloader reuses images already in the Docker daemon and records
registry digests. The preflight runs the published `tests/test.sh` on an empty
repository state and after `solution/gold_patch.diff`; it reuses existing pass
evidence on reruns. Both tools write progress and per-task artifacts under
`data/stage1/`. Docker's configured root on this machine is `/data/docker`.

A task is Stage 1 READY only when its original and metadata are present, its
image is local, Base fails, Gold passes, and its source/image hashes are
recorded. A local preflight failure remains visible in the report for review.

Rejected local-oracle tasks go in `task_list/rejected_ids.txt`; already passing
selections are retained via `task_list/retained_ids.txt`. Repeat the fetch, pull,
and preflight commands after replacement until `audit_stage1.py` reports READY.
