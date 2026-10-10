# Stage 3 新增合格数据与原 20 条合并统计

日期：2026-10-10  
实验：`deepseek_miniswe_20_20261008` + `deepseek_miniswe_new22_20261010`

## 样本范围

- 原 Stage 3 队列：20 条。
- 新增合格队列：22 条，与原队列无重合；其中 8 条不在 Stage 1 的 selected-100 名单中。
- 两批共 42 条进入 Stage 3。新队列清单为 `task_list/stage3_new_qualified_cohort_20261010.txt`。

## 执行与回放覆盖

| 指标 | 原 20 条 | 新增 22 条 | 合计 |
|---|---:|---:|---:|
| 计划 solver rollout（两种 instruction） | 40 | 44 | 84 |
| Harbor rollout 完成 | 40 | 43 | 83 |
| 生成非空 patch | 40 | 42 | 82 |
| patch 的原始与 functional verifier 均有有效结果 | 40 | 40 | 80 |
| 两种 instruction 都有完整有效结果的任务 | 20 | 19 | 39 |

新增 22 条都启动了两种 instruction 的 rollout。未形成完整配对的情况有三类：Vuls 原始 instruction rollout 没有 patch；Teleport 转换 instruction rollout 未完成且没有 patch；一个 OpenLibrary 任务的两份 patch 都因 `auth.yaml` 已存在而无法应用。该 patch 冲突不是 verifier 的语义 FAIL，未计入有效判定。

## Verifier 通过数

以下分母只包含对应 instruction 组中双 verifier 均有效的 patch。

| 解生成时使用的 instruction | 原 verifier PASS | Functional verifier PASS |
|---|---:|---:|
| 原始 instruction | 39 / 40（97.5%） | 37 / 40（92.5%） |
| 转换后 instruction | 15 / 40（37.5%） | 30 / 40（75.0%） |

分批数据：

| 批次 | 原始 instruction：原 / functional PASS | 转换后 instruction：原 / functional PASS |
|---|---:|---:|
| 原 Stage 3 20 条 | 19/20；17/20 | 3/20；13/20 |
| 新增 22 条（各组有效结果 20 条） | 20/20；20/20 | 12/20；17/20 |

## 配对 verifier 判定矩阵

每个 patch 同时运行两套 verifier。以下为原 verifier / functional verifier 的 PASS/FAIL 配对数。

| 解生成 instruction | 两者 PASS | 原 FAIL、functional PASS | 原 PASS、functional FAIL | 两者 FAIL |
|---|---:|---:|---:|---:|
| 原始 instruction | 36 | 1 | 3 | 0 |
| 转换后 instruction | 15 | 15 | 0 | 10 |
| 合计 | 51 | 16 | 3 | 10 |

## 分歧语义复核

| 指标 | 原 20 条 | 新增 22 条 | 合计 |
|---|---:|---:|---:|
| verifier 分歧候选 | 14 | 5 | 19 |
| 已复核 | 14 | 5 | 19 |
| 确认为 functional verifier 挽救的正确解 | 10 | 5 | 15 |
| 确认为 functional verifier 误拒的正确解 | 1 | 0 | 1 |
| patch 本身不正确 | 3 | 0 | 3 |
| 不确定或未复核 | 0 | 0 | 0 |

新增 5 个分歧都经 task Description/Expected Behavior 与两套 replay 证据核对，判为符合任务行为目标。原 verifier 报告的失败是历史 selector 缺失；这些失败本身不证明 patch 违反目标行为。复核记录在 `check/stage3/deepseek_miniswe_new22_20261010/semantic_reviews.json`。

## 解释限制

- 通过率是每个 patch 一次 rollout 的结果；不能解释为每项任务的稳定成功率。
- 新队列 22 条中只有 19 条可以在两种 instruction 条件之间完整配对比较；另外两种单边结果和一个 patch 应用冲突保留为缺失/错误状态。
- `report.md` 和 `aggregate.json` 分别保留各批原始结果；本文件只做合并计数，不改写 Stage 2 任务或 verifier。
