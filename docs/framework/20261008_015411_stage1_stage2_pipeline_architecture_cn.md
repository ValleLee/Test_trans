# SWE-bench Pro V2 Stage 1/2 当前流水线与框架架构

> 架构快照：2026-10-08 01:54:11 CST。本文描述当前仓库的执行逻辑和已经落盘的结果；Stage 3 不在本文范围内。当前批量转换与修复按用户要求暂停。

## 1. 一页理解框架

本项目把官方 SWE-bench Pro V2 的 Harbor 任务转换成另一份仍可由 Harbor 执行的任务。**Stage 1** 选择并冻结原任务，验证原始测试确实能区分 Base 和 Gold。**Stage 2** 只改写历史 `fail_to_pass`（F2P）测试对应的 verifier 断言，保留原始 `pass_to_pass`（P2P）回归测试，最后发布新的 Harbor `final/` 包。

```mermaid
flowchart LR
    A[官方 V2 数据行及 Harbor 任务] --> B[Stage 1: 选样、下载、镜像、原始 oracle]
    B -->|READY| C[不可变 original 与来源证据]
    C --> D[Stage 2: 单任务、单 attempt、多个 revision]
    D --> E[转换器生成测试及 F2P 映射]
    E --> F[语义、Docker 重放、角色、稳定性、正负 QA]
    F -->|全部通过| G[accepted + final Harbor 包]
    G --> H[最终审计 + 框架外独立审计]
    H -->|合格| I[check/qualified_tasks.txt]
    F -->|可修复失败| E
```

三个边界决定了框架的行为：

1. **规范与证据分开。** `source/problem_statement.md` 来自官方 `instruction.md`，仅移除 `Requirements` 和 `New Interfaces` 两节；保留其余 Harbor 包装和任务描述。R/I、原测试、Gold、仓库与环境可供转换器理解历史行为，但不能单独成为新测试的正确性要求。当前代码还允许控制器针对历史 F2P 中确有产品行为、而原问题描述遗漏的情况，生成经过后续门禁的行为级 `specification_addendum.md`；它是最终 instruction 的唯一可选增补，转换器的 `functional_specification.md` 本身不进入 instruction。
2. **转换范围由历史 F2P 限定。** 每个原 F2P selector 必须在 `conversion_trace.json` 中有一条可追溯的处理记录。问题描述中另有要求、但历史 F2P 没有测试的行为，不属于本轮“测试转换”的补测任务。
3. **原始 P2P 原样保留。** 原 `tests/config.json` 的 P2P selector 字符串及顺序不得删改或排除。由历史 F2P 改写出的、Base 已满足的回归 selector 可以追加在原列表之后；它们不算“改写原 P2P”。

## 2. Stage 1：官方任务与 oracle 的准备层

### 2.1 输入、选样与来源固定

选样脚本 [`task_list/select_v2_100.py`](../../task_list/select_v2_100.py) 从缓存的 V2 dataset rows 中保留原有 pilot，并按语言、仓库和 Gold patch 规模选择其余任务。`task_list/selected_100.txt` 是执行列表，`task_list/selection_report.json` 记录来源、语言、HARD 标记及选择理由。当前配额为 Python 40、Go 36、JavaScript 22、TypeScript 2；前三类各含 2 条官方 HARD，TypeScript 没有 HARD。Gold patch 行数只用于非 HARD 样本的跨度选择，不是模型通过率。

[`dataprepare/prepare_swebench_pro_v2.py`](../../dataprepare/prepare_swebench_pro_v2.py) 固定 `scaleapi/SWE-bench_Pro-os` 的 commit `66f92766bba642462d4bbe5479e83f91f9211862`，稀疏检出 `v2/tasks/<id>`，把原任务复制到 `tasks/<id>/original/`。官方数据行保存在 `data/dataset_rows.json`；每个任务另有来源 commit、数据行 hash、原任务树 hash 等 provenance。`original/` 此后是只读基准，不是转换器的输出目录。

### 2.2 环境与原始 oracle

[`dataprepare/pull_selected_images.py`](../../dataprepare/pull_selected_images.py) 复用已存在的官方任务镜像，缺失时拉取，并记录 registry digest。本机 Docker 数据根为 `/data/docker`。

[`dataprepare/preflight_selected.py`](../../dataprepare/preflight_selected.py) 在原镜像内调用**原任务**的 `tests/test.sh`，分别重放未打 Gold patch 的 Base 和应用 `solution/gold_patch.diff` 的 Gold。任务通过 Stage 1 的必要结果是 **Base FAIL、Gold PASS**；预检还记录原任务结构、镜像及各次日志。这里使用本地 Docker 执行官方测试脚本，并记录原任务的 verifier 网络策略；它是当前 Stage 1/2 的可复现执行路径，不等同于已在完整官方 Harbor 执行器中重新跑过每条任务。

预检失败的 ID 进入 `task_list/rejected_ids.txt`；[`dataprepare/reselect_oracle_failures.py`](../../dataprepare/reselect_oracle_failures.py) 保留已通过的样本并补选，再重复下载、拉镜像和预检。最终由 [`dataprepare/audit_stage1.py`](../../dataprepare/audit_stage1.py) 核查 100 个唯一 ID、语言/HARD 配额、`tasks/` 精确集合、原任务 hash、数据行 hash、镜像 digest 和 Base/Gold 结果。

当前 `data/stage1/final_100_report.json` 记录 `status=READY`、`ready_count=100/100`。**只有 READY 才应被调度到 Stage 2**；Stage 2 的 `init` 自身主要检查 `original/` 与来源文件是否存在，并不替代 Stage 1 的完整审计。

### 2.3 Stage 1 输出

```text
task_list/selected_100.txt                 100 个 instance_id
task_list/selection_report.json           选样依据、语言/HARD 与仓库统计
tasks/<id>/original/                       原始 Harbor task.toml、instruction、tests、solution、environment
data/stage1/<id>/source/                   P-only instruction、R/I、数据行、provenance
data/stage1/<id>/preflight/report.json     原始 Base/Gold oracle 结论
data/stage1/final_100_report.json          全样本 READY 审计
```

进入 Stage 2 时，`init` 将该任务的 `data/stage1/<id>/source/` **移入** `runs/<id>/source/`，使同一份来源证据由所选 run 持有；原任务仍在 `tasks/<id>/original/`。

## 3. Stage 2：一次转换 attempt 的闭环

### 3.1 Pipeline 图

```text
Stage 1 READY Original Harbor Task
P / R / I / F2P / P2P / Gold / Repo / Env
                         │
                         ▼
             INIT → attempt_NNN
             original 不变；source 固定
                         │
                         ▼
             ┌──────── REPAIR / new revision loop ───────────────────┐
             │                                                       │
             ▼                                                       │
① FUNCTIONAL CONVERTER [mini-swe-agent]                              │
   P = 基础规范；其他材料 = construction evidence                    │
   逐条分析历史 F2P → 找到公共可观察行为                             │
   保留原始 P2P selector → 编写测试和 conversion_trace               │
   对私有入口、Gold 形状、mock 耦合做 self-review                    │
             │                                                       │
             ▼                                                       │
② ARTIFACT CONTRACT [SCRIPT]                                         │
   文件/schema 齐全；每条 F2P 都有去向                               │
   原始 P2P 字符串和顺序不变；不打包历史 test_patch                  │
   历史 F2P 有重要 P 缺口                                            │
      └→ 控制器写行为级 addendum → 新 revision ──────────────────────┤
             │ PASS                                                  │
             ▼                                                       │
③ SEMANTIC JUDGE [LLM + deterministic checks]                        │
   P 依据、公共输出、Base 可观察性、Gold-only 绑定                   │
   必要时做反事实复审；不得要求未测的 P-only 新覆盖                  │
             │ PASS                                                  │
             ▼                                                       │
④ HARD REPLAY [Docker + 原 Harbor tests/test.sh]                     │
   convertible: Base FAIL / Gold PASS                                │
   原始 test_patch 只临时进入回放容器，让 P2P 源码可执行             │
             │ PASS                                                  │
             ▼                                                       │
⑤ BEHAVIOR ROLE AUDIT [SCRIPT]                                       │
   functional delta 在 Base FAIL                                     │
   F2P 转成的 regression 在 Base PASS；Gold 均符合角色               │
             │ PASS                                                  │
             ▼                                                       │
⑥ STABILITY [Docker，至少两轮 Base/Gold]                             │
   每轮逐条核对原始 P2P 在 Base 和 Gold 均 PASS                      │
   non_discriminative → Base/Gold 均 PASS → 记录，不发布             │
             │ convertible + PASS                                    │
             ▼                                                       │
⑦ POSITIVE QA [mini-swe-agent + fresh Judge + paired replay]         │
   构造不同于 Gold、但满足 P 的实现 → 新 verifier 必须 PASS          │
   原 verifier PASS/FAIL 只记录为对照证据                            │
             │ PASS                                                  │
             ▼                                                       │
⑧ NEGATIVE QA [mini-swe-agent + fresh Judge + replay]                │
   1 个相关且非等价的 mutant → 新 verifier 必须 FAIL                 │
             │ PASS                                                  │
             ▼                                                       │
   任一可修复 FAIL → 结构化反馈 → REPAIR rev_NNN+1 ──────────────────┘
             │ 全部 PASS
             ▼
⑨ ACCEPTANCE [SCRIPT] → 核对同一 revision 的全部门禁
   FAIL → feedback → 新 revision → ①
             │
             ▼
⑩ PACKAGE FINAL [SCRIPT]
   FAIL → feedback → 新 revision → ①
   原 task.toml / environment / solution + 新 tests
   instruction = 去掉 Requirements/New Interfaces 的原描述
                 + 可选的已审计行为级 addendum
             │
             ▼
发布后：框架 final audit + 框架外 independent audit
             │ 两者 PASS，原始 P2P 排除数 = 0
             ▼
       check/qualified_tasks.txt
```

正负 QA 在当前控制器中依次执行；任一失败会回到新 revision，而不会直接打包。

### 3.2 目录和模块职责

[`src/swepro_trans/paths.py`](../../src/swepro_trans/paths.py) 定义原任务、共享来源、attempt 与 revision 的路径契约；[`layout.py`](../../src/swepro_trans/layout.py) 执行 `init`、分配新 `attempt_NNN`、写清单，并在验收后打包。一个 task 可以有多个 attempt；一个 attempt 可以有多轮 `rev_NNN`。旧文档中 `runs/<id>/intermediate/` 或 `runs/<id>/final/` 的平铺路径只是历史布局，当前正式路径是：

```text
tasks/<id>/original/                         # 官方输入，不可变
runs/<id>/
├── source/                                  # 多个 attempt 共享的 Stage 1 来源证据
├── run_manifest.json
├── latest_attempt.json
└── attempts/attempt_NNN/
    ├── layout_manifest.json
    ├── intermediate/
    │   ├── converter/revisions/rev_NNN/    # 候选测试、trace、自审、manifest
    │   ├── validation/                     # schema、语义、重放、角色、稳定性、验收
    │   ├── qa/positive/ 与 qa/negative/     # 候选补丁、Judge、配对重放
    │   ├── control/state.json              # attempt 状态
    │   └── packaging/package_report.json
    ├── final/                               # 验收后才发布的 Harbor 任务
    └── review/                              # 可读审计、指标、独立审计
```

主要代码按职责分板块：

| 板块 | 当前实现 | 负责什么 |
|---|---|---|
| 批量入口与 CLI | `scripts/run_stage2_batch.py`、`src/swepro_trans/verifier_conversion.py` | 任务列表、有限并发、`init/agent/pipeline/package/final-audit` 命令；已获合格审计的包会被跳过 |
| Converter 执行 | `agents/runner.py`、`agents/mini_swe_session.py` | 在官方镜像的仓库中让 mini-swe-agent BUILD 或 REPAIR，挂载来源证据，提交 revision |
| F2P 契约 | `conversion_schema.py`、`validation/revision.py` | 历史 selector 逐条映射、分类、P2P 原样保留、生成测试存在性与 Harbor bundle 结构 |
| 语义检查 | `validation/semantic.py`、`validation/binding_signals.py`、`validation/counterfactual.py` | P 支持、公共可观察边界、Gold-only 绑定、反事实风险和 Judge 结论 |
| 执行检查 | `validation/revision.py`、`validation/behavior_roles.py`、`validation/stability.py` | Base/Gold 回放、逐 selector 角色证明、重复运行和 P2P 通过证据 |
| 正负 QA | `qa/session.py`、`qa/runner.py`、`qa/replay.py`、`agents/judge.py` | 生成候选实现/变异，Judge 判定，原始与新 verifier 配对重放 |
| 控制、修复与发布 | `pipeline/orchestrator.py`、`pipeline/repair.py`、`validation/acceptance.py`、`layout.py` | 门禁顺序、结构化反馈、新 revision、验收及最终打包 |
| 人审与最终检查 | `reporting/human_review.py`、`validation/final_audit.py` | 生成 review 文件；核查正式包、映射、P2P、instruction 和门禁记录 |

`configs/experiment.yaml` 管模型与 Judge 预算、prompt 路径、重复次数和 QA 候选上限；`prompts/` 存放 Converter、Semantic Judge、Positive/Negative 角色规则。`.env` 只由宿主机读取 endpoint 凭据，不复制到任务工作区或 Docker 挂载。

### 3.3 Converter 的输入与提交契约

Converter 可读：保留的 P、R/I、原 `tests/config.json` 与 `test_patch.patch`、Gold patch、原仓库和任务元数据。P 是基础规范；其余是 construction evidence。mini-swe 的容器使用官方镜像、`--network none`，只将 `/solution` 作为正式可写输出；证据、设计参考和控制器反馈是只读挂载。verifier 后续在任务镜像中执行，按原 `task.toml` 的 verifier 网络策略使用 Docker 网络。

每个 revision 至少提交 `tests/{test.sh,run_script.sh,parser.py,config.json}`、`conversion_trace.json`、`functional_specification.md`、`self_review.md` 和 `manifest.json`。`functional_specification.md` 是转换过程的提案/审计记录，不能直接定义 solver instruction。转换器还必须以 `SELF_REVIEW: PASS` 结束自审；硬门禁会拒绝占位符和缺失文件。

`conversion_trace.json` 对**每个历史 F2P**记录行为意图、原断言、分解后的行为义务、P 依据、可观察接口、Base 状态、处理决定和新 selector。当前四种分类及处理是：

| 分类 | 何时使用 | 处理 |
|---|---|---|
| `p_supported_behavior` | 历史 F2P 的行为有 P 依据 | `rewrite/merge` 到公共或可观察边界；若 Base 缺失/不同，新 selector 属于 functional delta |
| `base_regression_behavior` | 历史 F2P 有产品行为，Base 的公共边界已满足，P 未把它作为本次新功能 | `rewrite/merge`，新 selector 作为 converted regression 追加到原 P2P 列表之后 |
| `missing_product_behavior` | 历史 F2P 确有重要可观察产品行为，原 P 没写明 | 暂记 `specification_gap`，只提出行为级补充；控制器写 addendum 后要求下一轮 revision 转成实际测试 |
| `implementation_detail` | 剥离实现机制后没有独立产品行为 | 有具体证据地 `drop`，不能用“其他测试可能覆盖”代替证据 |

一个历史 F2P 可以同时包含产品行为与实现细节；trace 在义务级别分别记录保留或排除。`task_disposition=convertible` 还要求至少一个被保留的行为在 Base 上确有功能差异。全部只是 Base 已有回归或不可保留的实现细节时，任务进入 `non_discriminative`，不会发布 `final/`。

### 3.4 最终包与“合格”的额外条件

验收后的 `final/` 保持 Harbor 格式：`task.toml`、`instruction.md`、`environment/`、`tests/`、`solution/`。`task.toml`、环境和 Gold solution 复制自原任务；`tests/` 来自被接受的 revision；`instruction.md` 由控制器从 `source/problem_statement.md` 写出，可附带已审计的行为级 addendum，**不会写入原 Requirements/New Interfaces 或转换器提案文档**。

框架的 `accepted`/`packaged` 只表示自动门禁通过。团队当前的“合格数据”还要求：正式包完整、`final_audit.json` 为 PASS、**框架外** `independent_audit.json` 为 PASS、原 P2P 排除数为 0，且人工核对历史 F2P 的公共行为转换和 instruction 清理。独立审计应针对明确的 `attempt_NNN` 与 accepted revision，不能只看最高编号的目录或旧的流水线状态。自动 `final-audit` 会把明确的独立审计 FAIL 作为失败，但仅运行自动命令本身**不会生成独立审计 PASS**。

批量脚本为了避免重复运行，也可能复用未被明确否决的历史 `accepted` 包；`already_converted` 不是“合格”的同义词。当前 `final-audit --task-root` 查看的是最新 attempt；如果合格包属于更早的 attempt，应按清单指定路径核对那一轮已保存的审计记录。

当前 [合格清单](../../check/qualified_tasks.txt) 记录 20 条任务：Python 19、TypeScript 1。这个数字是本次架构快照，不代表全部 100 条都已完成 Stage 2；任务级状态应以各 attempt 的 acceptance、final、review 证据为准。

## 4. 失败、重试与幂等性

- 一轮 revision 的硬门禁失败、语义 FAIL、QA 误拒正确实现或误收 mutant，都会作为 REPAIR 反馈。控制器保留旧 revision 和日志，复制完整产物到新 revision，有限次数内重试；基础设施/endpoint 故障与语义缺陷分开记录。
- 新一次实验分配新的 `attempt_NNN`。已经发布且独立审计通过的任务由批量入口跳过；框架小改动本身不是重跑已合格数据的理由。terminal 的 complete 或 non-discriminative attempt 不复用为新实验。
- `runs/<id>/attempts/<attempt>/intermediate/control/state.json` 反映该 attempt 的最新状态，`validation/stage2_pipeline.json`、`validation/acceptance.json`、`packaging/package_report.json` 和 `review/` 给出原因与证据。中断时可能留下 `pipeline_running` 等旧状态；仅凭状态字段不能断言进程仍在运行。

## 5. 交接时从哪里看、怎么复现

阅读顺序：先看本文件和 [总览](../../README.md)，再看 [Stage 1 操作说明](../../dataprepare/README.md)、[`configs/experiment.yaml`](../../configs/experiment.yaml)、[`prompts/converter.md`](../../prompts/converter.md)、当前 [主控制器](../../src/swepro_trans/pipeline/orchestrator.py)，最后用一个合格任务的 `original/ → source/ → rev_NNN/ → validation/ → final/ → review/` 顺着证据走一遍。

以下命令是当前入口示例；本次只编写文档，**没有恢复已暂停的转换任务**：

```bash
# Stage 1 全量结果（已生成）
python3 dataprepare/audit_stage1.py

# Stage 2 单任务：先核查 data/stage1/final_100_report.json 对该 ID 的 READY
PYTHONPATH=src .venv/bin/python -m swepro_trans init \
  --tasks-root tasks --instance-id <instance_id>
PYTHONPATH=src .venv/bin/python -m swepro_trans agent \
  --task-root runs/<instance_id>/attempts/attempt_NNN \
  --revision runs/<instance_id>/attempts/attempt_NNN/intermediate/converter/revisions/rev_001
PYTHONPATH=src .venv/bin/python -m swepro_trans pipeline \
  --task-root runs/<instance_id>/attempts/attempt_NNN \
  --revision runs/<instance_id>/attempts/attempt_NNN/intermediate/converter/revisions/rev_001

# 批量入口只做计划检查时不会创建 attempt
.venv/bin/python scripts/run_stage2_batch.py \
  --ids-file task_list/<cohort>.txt --workers 5 --plan
```

若要统计可用任务，直接按 `check/qualified_tasks.txt` 给出的明确 attempt 核查 `final/`、`review/final_audit.json` 和 `review/independent_audit.json`。旧的设计文档仍可解释动机，但出现路径或门禁顺序差异时，以本文件列出的当前代码、配置和具体 attempt 证据为准。
