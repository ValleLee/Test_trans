# Harbor-to-Harbor 转换框架优化方案

- 生成时间：2026-09-29 03:09:19 UTC
- 适用范围：SWE-bench Pro V2 Harbor 任务的 Stage 2 转换
- 状态：当前框架优化的执行基线

## 1. 目标

输入和输出都保持 Harbor 任务格式。转换器只做两件事：

1. 以原始 Harbor `instruction.md` 为基准，只删除 `## Requirements` 和
   `## New Interfaces` 两个 construction-only 章节；其余前言、PR 包装和
   Constraints 完整保留；
2. 将 historical verifier tests 转成检查 public / observable behavior 的
   functional verifier。

原始 Harbor 任务保持只读。镜像、原生测试入口、网络策略和语言工具链全部由
原任务提供，框架不实现 Go、Python、Node 等语言的替代 runner。

## 2. 宿主机目录契约

```text
tasks/<instance_id>/original/       # Stage 1 READY 的不可变 Harbor 输入
data/stage1/<instance_id>/         # 尚未进入 Stage 2 的 Stage 1 证据
runs/<instance_id>/                 # 只有实际进入 Stage 2 的任务
├── source/                         # 被选中任务接管的固定输入证据
├── intermediate/                   # revision、validator、QA、控制状态
├── review/                         # 人审报告和指标
└── final/                          # 全部 gate 通过后才创建的 Harbor 任务
```

`init` 必须显式指定一个 `instance_id`，不会为所有准备好的任务创建 run。
Stage 1 失败的任务只留在 `tasks` 和 `data/stage1`，不进入 `runs`。Stage 2 init 将选中任务的 `data/stage1/<id>/source` 移入 `runs/<id>/source`，避免保留重复副本。

## 3. Converter 容器边界

mini-swe-agent 使用一个临时 sandbox。容器只需要下面的逻辑路径：

```text
/app 或 /testbed       # 镜像内的原始仓库
/evidence              # 只读 construction evidence
/reference             # 只读 taxonomy 等可选设计参考
/solution              # 唯一可写的 revision 输出
/scratch               # 临时探索，永不提交
```

`/workspace` 仅是 mini-swe-agent 的临时工作目录，不是任务格式、持久化数据目录
或第二份仓库。`restricted`、`sealed`、`public` 和旧 compatibility alias 不再
承担数据语义。

## 4. 最小流水线

```text
Stage 1 READY Harbor task
        │
        ▼
mini-swe-agent Converter
  P = runs/<id>/source/problem_statement.md
  R/I/F2P/P2P/Gold = construction evidence
  output = Harbor tests + conversion_trace + self_review
        │
        ▼
Deterministic artifact validator
  schema / required tests / F2P accounting / P2P accounting
        │
        ▼
Fresh semantic Judge
  P support / public observability / implementation coupling / harness coupling
        │
        ▼
Harbor-native Base/Gold replay
  Base + Functional → FAIL
  Gold + Functional → PASS
  retained P2P → PASS
        │
        ├── Positive QA: different valid implementation → Functional PASS
        └── Negative QA: one targeted semantic mutation → Functional FAIL
        │
        ▼
Acceptance → runs/<id>/final/
```

任意 gate 失败都会将反馈交给下一次 Converter revision。只有 acceptance 通过
后才创建 `final/`。

## 5. Revision 最小产物

Converter revision 只提交：

```text
revision/
├── tests/                  # Harbor verifier contract
├── conversion_trace.json   # 每个 historical F2P 的 disposition
├── self_review.md
└── manifest.json           # 文件和覆盖范围清单
```

`instruction_scope`、跨格式 materialization、旧版 P-only task 和多套 evidence
副本不再是转换必需品。人审映射和 QA 指标由宿主机 `runs/<id>/review/` 统一生成。

## 6. 运行时与语言兼容性

Stage 1 preflight 必须使用任务自己的 `tests/test.sh`、`run_script.sh`、
`parser.py`、`config.json` 和镜像，遵循 `task.toml` 的 network policy。

- 镜像缺少 Go 等运行时：记录为 Stage 1 environment failure，不创建 Stage 2
  run，不生成 final；
- 镜像可运行：Stage 2 继续使用同一镜像和原生测试入口；
- framework 不根据语言选择自定义执行器；
- `/app` 与 `/testbed` 由任务镜像实际布局决定，代码不得依赖某个仓库路径。

## 7. 本次落地顺序

1. 将 Converter evidence mount 从旧分类目录收敛到 `evidence/reference`；
2. 更新 Converter / QA prompt 的路径和输出契约；
3. 保持 Harbor preflight、network policy、Base/Gold replay 和语言工具链；
4. 清空 qutebrowser 的旧 Stage 2 run，创建干净 `rev_001`；
5. 运行 Converter、artifact validator、semantic Judge 和 Harbor replay；
6. 根据实际失败继续修订框架和 prompt；
7. 在 positive/negative QA 可执行后才接受并 package final。

## 8. 验证记录

本文件对应的执行结果写入：

```text
runs/<instance_id>/intermediate/
runs/<instance_id>/review/
```

成功任务的唯一发布位置为：

```text
runs/<instance_id>/final/
```

## 9. 详细 Gate 语义（与 plan1 第四节对齐）

### 9.1 Functional Converter / Revision Loop

Converter 使用 mini-swe-agent 读取全部 construction evidence，但只把
`problem_statement` 当作 normative specification：

```text
分析 historical F2P
    ↓
理解原测试 behavioral intent
    ↓
识别 implementation binding
    ↓
找到 public / observable behavior
    ↓
编写 functional verifier
    ↓
semantic self-review
    - 是否由 P 支持
    - 是否错误继承 R/I/Gold 约束
    - 是否仍绑定特定实现
    ↓
submit revision
```

每个 F2P 必须在 `conversion_trace.json` 中有且只有一条 disposition。可用
`keep`、`rewrite`、`merge`、`drop`；`drop` 必须说明 P 不支持或无法形成稳定
observable contract 的原因。P2P 记录为 retained regression，不能混入 functional
F2P coverage。

### 9.2 Hard Validator

Hard Validator 是脚本控制的确定性 gate，按以下顺序工作：

```text
artifact/schema/accounting
    ↓
verifier runnable
    ↓
Base + Functional → FAIL
Gold + Functional → PASS
retained regression / P2P → PASS
```

失败时保存 revision-relative 的错误和运行日志，作为下一轮 Converter 的反馈；
它不能自动发明新的测试语义。

### 9.3 Verifier QA

#### Positive QA

mini-swe-agent 可以参考 Gold 构造一个实现策略、控制流或文件组织明显不同的正确
实现。Fresh Judge 确认它满足 P 且确实存在 structural difference。随后执行 paired
replay：

```text
Original verifier   → PASS/FAIL（比较证据）
Functional verifier → 必须 PASS
```

Original verifier 的结果用于审计，不作为 functional candidate 语义正确性的唯一
判据。

#### Negative QA

从 Gold 或已确认正确的 positive candidate 构造 near-correct 实现，只违反一个
F2P 支持的 P semantic。Fresh Judge 确认目标缺陷确实存在，然后执行：

```text
Functional verifier → 必须 FAIL
```

语法、依赖、编译或无关环境失败不能作为合格 negative mutant。

### 9.4 Acceptance / Repair

```text
positive + negative QA 都通过
    ↓
verifier OK → acceptance → package final

任一 QA 发现 verifier defect
    ↓
Converter REPAIR
    ↓
新的 revision → Validator
    ↓
Replay 已有 QA，避免修复破坏已有结论
```

`final/` 只由 acceptance 后的 package 脚本创建。所有 gate 和 QA 结果必须带
revision-relative 路径，防止旧 revision 的结果污染新 revision。
