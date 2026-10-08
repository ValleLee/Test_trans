# 当前测试功能性转换框架（自动补充规范版）

更新时间：2026-09-30（UTC）

## 1. 目标

把 SWE-Bench Pro v2 的 historical F2P 测试转换成面向产品功能的 Harbor verifier：

- 保留每一条 historical F2P 背后的行为意图；
- 通过公开 API、CLI、服务、文件输入输出、可观察状态或错误语义验证行为；
- 不把 Gold 实现、私有 helper、内部字段、mock 调用形状变成解题要求；
- 当 P 没有明确写出重要功能时，自动补充行为级 instruction，再继续转换；
- 只有确认某条测试纯粹检查实现细节时，才允许 drop；
- 每条 F2P 都必须在账本中得到 `rewrite`、`merge`、`drop` 或已解决的 `specification_gap` 结论。

这里的 P 是最终给解题 agent 看到的 Problem Statement 加上自动生成并审计过的行为补充。补充只能描述功能行为，不能规定类名、方法名、模块路径、签名或 Gold 的实现方式。

## 2. 输入和输出

### 2.1 输入

原始任务保持不变，位于：

```text
tasks/<instance_id>/
└── original/                 # Harbor 原任务，只读
    ├── instruction.md
    ├── task.toml
    ├── tests/                # historical F2P/P2P
    ├── solution/             # Gold 和运行环境证据
    └── environment/
```

阶段一确认过的证据位于：

```text
runs/<instance_id>/source/
└── problem_statement.md      # 基础 P
    requirements.md           # construction evidence
    interface.md              # construction evidence
    dataset_row.json
    instruction_policy.json
```

Requirements、Interface、历史测试和 Gold 用于恢复行为意图，不会直接成为最终 instruction。

### 2.2 输出

每次转换隔离在一个 attempt：

```text
runs/<instance_id>/attempts/attempt_NNN/
├── intermediate/
│   ├── converter/revisions/rev_NNN/  # agent revision
│   ├── specification_addendum.md     # 自动生成的功能补充（如有）
│   ├── validation/                   # 结构、语义、重放、QA 结果
│   ├── qa/                           # 正负 QA
│   └── control/                      # 状态和事件
├── review/                           # 人可读报告、F2P 映射、指标
└── final/                             # 只有全部门槛通过才生成
```

旧 attempt 只作审计证据，不能自动冒充当前 final。

## 3. F2P 逐条转换决策

Converter 对每条 canonical F2P 生成一行 accounting。至少包含行为意图、功能表面、P 支持情况、Base/Gold 证据、决定和理由。

### 3.1 `rewrite`

一条 F2P 改写为一个或多个公开行为测试。测试不应直接调用仅由 Gold 引入的 helper；应通过用户可见输入和输出验证等价功能。

### 3.2 `merge`

多个 F2P 共享一个公开功能场景时合并测试，但每条原始 selector 仍要在账本中明确映射到该测试。

### 3.3 `specification_gap`

当行为属于产品功能、可被观察，但基础 P 没有清楚描述时使用。Converter 必须给出：

- 缺少的行为语义；
- 为什么它是产品功能而非实现细节；
- 行为级补充文本；
- 计划使用的公开观测面。

Controller 随后会：

1. 生成 `intermediate/specification_addendum.md`；
2. 把补充作为下一轮 mini-swe Converter 的有效任务上下文；
3. 重新生成 revision；
4. 将补充并入最终 `final/instruction.md`（仅在全部验证通过后）。

因此 gap 是自动修复信号，不是要求用户手动改源文件的终点。

### 3.4 `drop`

只有以下情形可 drop：

- 私有字段、内部缓存、内部容器；
- mock 调用次数或精确调用形状；
- fixture/测试 plumbing；
- Gold 专用文件、helper 或内部 bookkeeping；
- 没有独立产品行为的实现路径。

Drop 必须同时填写 `drop_justification` 和 `drop_evidence`，说明为什么删除不会丢失用户可观察功能。不能因为“找不到同名 API”“测试用了新 class”“测试调用了 constructor”就 drop。

## 4. 自动流程

```text
准备 Stage 1 Harbor 任务和 source P
              │
              ▼
mini-swe Converter（Docker）
  读取 P + construction evidence + taxonomy
  对每条 F2P 做行为分类和公开表面重写
              │
              ▼
Artifact Contract
  schema / selector accounting / drop evidence
              │
       ┌──────┴────────┐
       │               │
   有 gap            无 gap
       │               │
生成 behavior addendum  Semantic Judge
并自动申请新 revision       │
       │               ▼
       └──────► Semantic Judge
                    │
                    ▼
          Deterministic Hard Validator
          Base/Gold F2P + retained P2P
                    │
                    ▼
              Stability replay
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
      Positive QA          Negative QA
  不同实现仍应通过       违反单一功能应失败
          └─────────┬─────────┘
                    ▼
                Acceptance
                    │
                    ▼
              Package final Harbor
```

所有自动 repair 都有最大 revision 次数。达到上限仍有 gap、未解释 drop 或 verifier 缺陷时，状态为失败并保留完整证据，不能降低门槛制造成功。

## 5. 质量门槛

### 5.1 Artifact

- 每条 canonical F2P 恰好一行；
- `rewrite`/`merge` 有 emitted tests；
- `drop` 有 justification 和 evidence；
- 不允许未知决定、重复 selector 或漏记 selector；
- P2P selector 原样保留。

### 5.2 语义

Semantic Judge 检查：

- 是否保留历史行为意图；
- 是否错误继承 Gold-only 或私有实现；
- 是否存在 under-conversion；
- drop 是否确实是实现细节；
- 新增 addendum 是否只描述行为而没有隐含 API。

### 5.3 执行

- Base + functional verifier：原始 Base 应保持失败语义；
- Gold + functional verifier：Gold 应通过；
- retained P2P：继续通过；
- 稳定性：重复执行结果一致；
- Positive QA：结构不同但满足功能的实现通过；
- Negative QA：违反目标功能的实现被拒绝。

## 6. 路径和运行契约

所有 controller、Converter、Judge、QA、validator 通过 `TaskPaths` 解析路径。Docker 内使用 `/app` 或 `/testbed`，宿主机路径不会写入 verifier。每个组件读取统一的 revision artifact 和状态文件，不自行猜测相对路径。

模型只写 `/solution`；原任务、Base 仓库和 Gold 不可改写。最终任务只复制原 `task.toml`、环境、solution 和生成的 `tests/`，instruction 由基础 P 与审计过的 addendum 组成。

## 7. 本轮两条任务的预期处理

- qutebrowser 的字体解析、空项处理、顺序和序列化属于可观察功能；应补充行为级描述并通过配置行为或其他公开边界验证，不应因为历史测试调用 `FontFamilies` 就整体 drop。
- OpenLibrary 的作者名组合和 alternate-name 输出属于公开作者数据行为；应从 MARC 输入经过公开读取流程验证，不应直接依赖 `name_from_list` helper。

两条任务都必须重新生成 revision，并通过完整的 semantic、hard replay、stability、positive/negative QA 后才能出现 `final/`。

## 8. 记录和审计

每次 gap enrichment、repair、judge、replay 和 package 都写入：

- `intermediate/control/events.jsonl`；
- `intermediate/validation/stage2_pipeline.json`；
- `review/conversion_report.md`；
- `review/f2p_mapping.csv`；
- `review/metrics.json`。

这使得“某条 F2P 被改写、合并、补充还是删除”都能追溯到原 selector 和证据。

## 9. 2026-09-30 本轮落地结果与规则修正

qutebrowser 的单条任务在 `attempt_010` 完成了完整自动流程。最终包位于：

```text
runs/<instance_id>/attempts/attempt_010/final/
```

本次通过的门槛为：

- Semantic Judge：`PASS`；
- Docker hard replay：Base functional verifier 失败、Gold functional verifier 通过；保留的 P2P 回归通过；
- Stability replay：F2P 和 P2P 重放均通过；
- Positive QA：不同于 Gold 的实现通过；
- Negative QA：破坏一个已转换行为的近似实现被拒绝；
- Acceptance 和 Package：`accepted` / `packaged`。

本次暴露并修正了一个通用问题：原 acceptance 读取的是 attempt 级初始化账本，而不是被选 revision 的 `conversion_trace.json`，并且错误地要求 F2P selector 数量不变。现在 acceptance 使用选中 revision 的逐条映射作为权威记录：允许多条 historical F2P 合并到一个功能测试，但每条原始 F2P 必须有 `rewrite`、`merge` 或有充分证据的 `drop` 映射；`emitted_tests`、行为意图和证据仍必须完整。接受后同时同步 attempt 级索引和 stage2 审计报告，避免人审文件显示过期失败状态。

因此，“每条 F2P 都转换”指每条都有可追溯的行为映射，不要求机械地保留相同数量的测试函数。只有确认是 Gold/历史测试的纯实现细节时才允许 drop；若是产品功能但 P 缺少行为描述，则先写入行为级 addendum，再重新转换和验证。

## 10. OpenLibrary 完成记录与 QA 恢复规则

OpenLibrary 的单条任务已在最新的 `attempt_006/final` 完成。`attempt_005` 保留了中间恢复过程和候选证据。六条 F2P 全部保留行为映射：两条 alternate-script fixture 合并为公开作者数据测试，四条历史 `name_from_list` 测试改写为 `read_edition(MarcBinary) -> authors` 的姓名规范化测试，没有 drop。

本次还验证了一个恢复场景：Positive QA agent 在写出 `candidate.patch` 和 `candidate_metadata.json` 后达到步数上限，未发送最终哨兵。QA runner 现在以两个完整工件作为交接事实，记录 `resumed_artifacts` 并继续 Docker replay 和 Judge；不会因为缺少最后一条哨兵消息而丢弃候选。QA runner 也会在重新启动时优先复用完整候选，避免重复调用模型。

因此自动流程的可恢复条件是：

1. Converter revision 必须包含完整 revision artifact 和逐条 F2P trace；
2. Positive/Negative candidate 必须同时有 patch 和 metadata；
3. 所有候选仍必须经过 Docker replay 与 Judge，工件存在本身不等于通过；
4. acceptance 会从各门槛的权威 JSON 重建 stage2 审计报告，保证恢复运行后审计文件不缺 QA 结果。

两条已完成任务的最终状态均为 `state.status=accepted`、`stage2_pipeline.status=complete`，且都包含 final、review 和完整 intermediate evidence。OpenLibrary 的 attempt_006 是经过修复后从 pipeline 入口自动跑到底的最终尝试。
