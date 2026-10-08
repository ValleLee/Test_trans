# SWE-bench Pro V2 Functional Verifier

本项目把 Harbor 格式的 SWE-bench Pro V2 historical verifier 转换为面向
Problem Statement 的 functional verifier。

- 原始 Harbor `instruction.md` 仅删除 `Requirements` 和 `New Interfaces`；其余内容完整保留在最终 instruction 中。
- `requirements`、`interface`、historical tests 和 Gold 只作为 Converter 的 construction evidence。
- Agent 使用 mini-swe-agent；deterministic validator、semantic Judge、Positive/Negative QA 和 package gate 由控制器编排。

## 目录约定

```text
tasks/<instance_id>/
└── original/                       # 官方 Harbor 原任务，只读

runs/<instance_id>/
├── source/                         # 本次转换的固定输入证据，由 Stage 1 移入
├── intermediate/                   # 本次转换的过程产物
│   ├── converter/                  # revisions、trace、trajectory
│   ├── validation/                # artifact、semantic、hard replay、acceptance
│   ├── qa/                         # positive / negative QA
│   └── packaging/
└── attempts/attempt_NNN/          # 每次转换尝试
    ├── final/                      # 只有完整通过后才生成的 Harbor 任务
    └── review/                     # 人审指标和自动审计

upstream/SWE-bench_Pro-os/          # 固定 commit 的官方上游
src/swepro_trans/                   # 路径、mini-SWE、pipeline 和 package
scripts/                            # 当前阶段使用的确定性入口
prompts/                            # converter / judges / qa 分类 prompt
configs/                            # experiment.yaml tuned budgets and prompt map
docs/references/                    # DeepSWE verifier taxonomy 等参考资料
```

`tasks/<id>/original` 永远不被转换器写入。`runs/<id>/attempts/attempt_NNN/final` 只有完整通过后才生成；不存在时，表示当前
revision 尚未完成全部 gate。失败或阻塞结果直接记录在对应 attempt 的 `review/`。Stage 1 未通过或未进入转换的任务不会出现在 `runs/`。

## 仓库内容

Git 仓库包含项目代码、配置模板、测试、完整的 `docs/` 文档，以及 `check/stage3/deepseek_miniswe_20_20261008/` 中 20 条 Stage 3 实验的输入快照、逐项结果和分析。体积较大的 `harbor_jobs/` 原始作业副本和无效的首轮复判目录 `regrade_before_uniform_reset/` 不随仓库发布。其他本地数据、任务副本和结果目录（`data/`、`tasks/`、`runs/`、`jobs/`、`task_list/`）以及第三方代码 `upstream/` 也不发布。新环境需要按 `dataprepare/README.md` 获取数据，并准备官方上游和 Harbor 环境。`.env` 应从 `.env.example` 复制并在本地填写。

## 环境

- `.env`：复用上一版项目的 endpoint 配置，权限为 `600`，不提交到版本库。
- `.venv`：已验证的 Python 3.12 / `mini-swe-agent==2.4.6` 环境。
- `docs/references/deepswe_verifier_taxonomy.md`：挂载给 Converter 的只读 verifier 设计参考，不增加 P 的语义要求。

```bash
PYTHONPATH=src .venv/bin/python scripts/runtime_check.py
```

## Stage 1：100 条 V2 数据

当前选择见 `task_list/selected_100.txt` 与 `task_list/selection_report.json`；
包含原有 20 条。语言数为 Python 40、Go 36、JavaScript 22、TypeScript 2。
下载、镜像和 Base/Gold 预检命令见 `dataprepare/README.md`。
只有 `data/stage1/<id>/preflight/report.json` 通过的任务可进入 Stage 2。

## 阶段二入口

Stage 1 准备任务后，原始任务写入 `tasks/<id>/original`，Stage 1 证据写入 `data/stage1/<id>`；只有选中的任务执行 Stage 2 init 后才会将证据移入 `runs/<id>/source`：

```bash
python3 dataprepare/prepare_swebench_pro_v2.py
PYTHONPATH=src .venv/bin/python -m swepro_trans init --tasks-root tasks --instance-id <instance_id>
```

运行 Converter，原任务路径和 revision 路径分开：

```bash
TASK=tasks/<instance_id>
RUN=runs/<instance_id>
PYTHONPATH=src .venv/bin/python -m swepro_trans agent \
  --task-root "$TASK" \
  --revision "$RUN/intermediate/converter/revisions/rev_001"
```

完整 Stage 2 顺序为：artifact contract → semantic Judge → Base/Gold hard replay
→ Positive QA → Negative QA → acceptance → package。每次 pipeline 运行会把旧
revision 的下游结果标记为 `not_run`，并更新 `runs/<id>/review/`：

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans pipeline \
  --task-root "$TASK" \
  --revision "$RUN/intermediate/converter/revisions/rev_001"
```

成功后正式任务位于：

```text
runs/<instance_id>/attempts/attempt_NNN/final/
├── task.toml
├── instruction.md                  # 原始 Harbor instruction，仅去除 R/I 章节
├── environment/
├── tests/                          # functional verifier
└── solution/
```

人审文件位于：

```text
runs/<instance_id>/attempts/attempt_NNN/review/
├── conversion_report.md
├── f2p_mapping.csv
├── metrics.json
├── summary.json
└── final_audit.json
```

## Docker 边界

Harbor/Docker 镜像提供任务运行环境；宿主机保存不可变的
`tasks/<id>/original`、Stage 1 的 `data/stage1/<id>` 和 Stage 2 的 `runs/<id>`。
Converter 容器使用镜像内的 `/app` 或 `/testbed` 仓库，只把候选 revision 以
`/solution` 作为唯一正式可写挂载；`evidence`、`reference` 和 `run` 均为只读，
`scratch` 是临时目录。`workspace` 仅是 mini-swe-agent 的临时工作目录。

## 官方 Harbor

官方 Harbor `v0.22.0` 固定在 `upstream/harbor`。Stage 3 使用官方 Harbor
执行器；本地 Docker fallback 只用于可重复的 Stage 1/2 检查，并在报告中记录网络策略。

## Specification gaps, legacy packages, and automatic audit

The converter decisions are `rewrite`, `merge`, and `specification_gap`. A
`specification_gap` records an important behavior that is not authorized by the
retained Problem Statement; it triggers an audited behavior-level addendum and
requires a fresh revision before acceptance. `functional_specification.md` is
only a proposal record and is never merged into the final instruction without
that revision.

Run the same audit locally or in CI for all published runs:

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans final-audit --all-runs --write
```

The audit reports old accepted artifacts as `legacy` when they predate the
current F2P classification schema. It does not invent missing semantics; new
revisions must pass the current strict schema.
