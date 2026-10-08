# Stage 3 实验方案：两种 instruction 生成解，双 verifier 交叉评测

## 1. 背景与目标

SWE-bench Pro V2 原任务的 instruction 包含 Problem Statement，以及 Requirements、New Interfaces 等补充内容；原始 verifier 可能依赖历史实现细节。Stage 2 已生成新的 Harbor 任务：从 instruction 中去掉 Requirements 和 New Interfaces，并将 verifier 转换为检验可观察功能行为的版本。

本实验检验两个问题：

1. 去掉 Requirements 和 New Interfaces 后，同一 solver 生成的解及其通过率如何变化？
2. 对**同一个解**，原始 verifier 与 functional verifier 的判定有何差异？新 verifier 能否接受被旧 verifier 误拒、但满足 Problem Statement 的解？

预期原始 instruction 下通过旧 verifier 的正确解大多也能通过新 verifier；转换后 instruction 可能产生更多“旧 verifier 失败、新 verifier 通过”的正确解。这是待验证的假设，不是筛选任务或判定 verifier 正确性的依据。

## 2. 实验设计

每个任务仅运行两组 solver，之后对两组中的每个 patch 做双 verifier 复判：

| 解的生成组 | Solver 读取的 instruction | 对每个 patch 执行的评测 |
|---|---|---|
| 原始 instruction 组 | `tasks/<id>/original/instruction.md` | 原始 verifier、functional verifier |
| 转换后 instruction 组 | `runs/<id>/attempts/attempt_NNN/final/instruction.md` | 原始 verifier、functional verifier |

```text
原始 instruction ──相同 Harbor + agent──> 原始组 patch ──┬─ 原始 verifier
                                                        └─ functional verifier
转换后 instruction ──相同 Harbor + agent──> 转换后组 patch ──┬─ 原始 verifier
                                                            └─ functional verifier
```

图中两种 instruction **各自**生成 patch；每个 patch 均进入右侧两套 verifier。没有第三组 solver rollout。对同一 patch 更换 verifier 是配对比较；两组 instruction 产生不同 patch，其通过率比较是 instruction 条件比较。

纳入任务以 `check/qualified_tasks.txt` 为候选清单，运行前解析并冻结具体 `instance_id` 与 `attempt_NNN`。每条还须核验 Stage 1 READY、Stage 2 accepted、final audit PASS、`original/` 和所选 `final/` 齐全。该清单当前记录 20 条；本轮冻结 manifest 固定这 20 个任务，排除项及原因须保留。

主比较只纳入两份 instruction 除删除 Requirements / New Interfaces 外没有其他规范性差异、且 base repo 和环境可对齐的任务。若 final instruction 有经审计的行为补充，单独列出，不把它的结果解释为“仅删除 R/I”的效果。

## 3. 执行配置与代码来源

两组固定同一官方 Harbor `v0.22.0`、`mini-swe-agent==2.4.6` 及其 Harbor 适配器、模型与推理参数、agent scaffold、timeout、网络策略、Docker image digest、base repo 和每任务 rollout 数。可控 seed 按任务及 rollout 编号配对；记录实际执行顺序，并交错运行两组。模型服务随时间变化的版本信息也要写入 manifest。

所需代码在项目内的分工如下：

| 路径 | 用途 |
|---|---|
| `upstream/harbor/` | 固定的官方 Harbor v0.22.0 执行器，含 `mini-swe-agent` 适配器；用于 solver rollout |
| `upstream/SWE-bench_Pro-os/` | 固定的官方 V2 任务来源；用于来源核对，不直接充当本轮评测输出 |
| `tasks/<id>/original/` | 已准备的原始 Harbor 任务与原始 verifier |
| `runs/<id>/attempts/attempt_NNN/final/` | Stage 2 接受的转换后任务与 functional verifier |
| `src/swepro_trans/qa/replay.py` | 已有的候选 patch 双 verifier Docker replay 逻辑；Stage 3 可复用其执行方式，但需独立保存 Stage 3 结果 |

`mini-swe-agent` 本体不在 `upstream/`：项目依赖锁定了 `2.4.6`，但 Harbor 会在任务环境中另行安装 agent，必须在 Harbor 配置中显式固定相同版本并记录实际安装版本。项目的 Stage 2 编排代码在 `src/swepro_trans/`。Harbor 内置 `trial regrade` 仅支持 separate mode；未声明独立 verifier 环境的任务默认是 shared mode，不能直接调用该命令复判。运行前逐任务核验模式；Stage 3 统一用独立驱动程序调度 Harbor rollout 与 Docker replay，不修改上游源码。

## 4. Pipeline

1. **冻结输入。** 从候选清单确定任务与 final attempt；验证 instruction 差异、base repo、镜像和环境一致性。保存 Harbor/任务来源 commit、镜像 digest、两份 instruction、两套 tests、task 配置的哈希，以及模型、agent、rollout 数等运行参数。评测期间不改动 `original/` 或 `final/`。
2. **生成两组解。** 原始组使用原任务；转换后组临时使用 final instruction 与原任务的其他 solver 可见输入。两组均由 Harbor 的同一 `mini-swe-agent` 配置运行。保存每次 trajectory、patch、token、耗时及终止状态。solver 不得接触 Gold、转换证据、verifier 答案或另一组轨迹。
3. **对每个 patch 交叉复判。** 从相同干净 base repo 分别应用同一 patch，再运行原始和 functional 两套 verifier。按各任务的测试脚本、配置及原始 P2P 依赖准备测试；每次用独立容器/工作区，保存退出码、结构化结果和完整日志。Harbor rollout 自带的首次 verdict 可以留存，主分析统一采用这一步的复判结果。
4. **审查判定变化。** 对两组中所有“旧 FAIL / 新 PASS”和“旧 PASS / 新 FAIL”保留 patch 与日志，按 Problem Statement 和可观察行为核查。只有确认满足规范的“旧 FAIL / 新 PASS”才计为被新 verifier 挽救的正确解。
5. **汇总报告。** 输出每任务及总体的生成、复判和审查结果，并明确缺失样本与环境故障。

复判遇到 patch 无法应用、超时、容器故障或 verifier 未启动，应记录为独立状态，不能当作语义 FAIL。按预先固定的次数重试基础设施故障，保留每次日志；不得因 verdict 不合预期而替换 patch 或重跑 solver。

## 5. 统计口径

每组每任务的计划 rollout 数为 `n`，运行前固定。报告原始计数、分母和比率：

| 指标 | 口径 |
|---|---|
| 生成成功率 | 有候选 patch 的 rollout / 计划 rollout |
| 双复判覆盖率 | 两套 verifier 均有有效 verdict 的 patch / 计划 rollout |
| 四格通过率 | 两种 instruction × 两套 verifier，各格 PASS / 该格有效 verdict 数 |
| 配对判定矩阵 | 对每组同一 patch 统计：双 PASS、旧 FAIL/新 PASS、旧 PASS/新 FAIL、双 FAIL；分母仅含双有效 verdict |
| 确认挽救数 | “旧 FAIL/新 PASS”中经独立语义审查确认满足 Problem Statement 的 patch 数；同时报告全部候选数 |
| 拒绝正确解数 | “旧 PASS/新 FAIL”中经审查确认满足 Problem Statement、因而被新 verifier 错误拒绝的数 |
| Solver 成本 | 两组的 token、耗时、无 patch 和其他失败类型 |

Instruction 效应分别在固定原始 verifier、固定 functional verifier 下比较两组通过率；verifier 效应在各组内部由同一 patch 的配对矩阵计算。汇总同时给出逐任务结果、任务等权平均及总计数，避免某些任务的 rollout 数主导结论。若报告区间估计，以任务为重抽样单位给出 95% 区间；样本量与缺失情况必须一并呈现，不对未审查的判定变化作正确性推断。

## 6. 输出与冻结规则

所有本轮结果写入 `check/stage3/<experiment_id>/`，实验完成后另在 `docs/stage3/` 写本轮方法与结果说明；不写回 Stage 2 的 final task：

```text
check/stage3/<experiment_id>/
├── manifest.json                  # 冻结清单、attempt、哈希和统一运行配置
├── instances/<instance_id>/
│   ├── original_instruction/      # 各 rollout 的 trajectory、patch、元数据
│   ├── converted_instruction/
│   ├── regrade/                    # 每个 patch 的两套 verifier 结果与日志
│   └── analysis.json              # 四格统计、配对矩阵、语义审查结论
├── aggregate.json
└── report.md
```

发现系统性 verifier 缺陷时，在本轮报告中标记受影响任务与证据，暂时不回到stage2。