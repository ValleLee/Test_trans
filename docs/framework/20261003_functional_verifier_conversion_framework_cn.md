# SWE-Bench Pro v2 测试功能性转换框架（2026-10-03）

## 1. 目标

框架以 Harbor 任务为输入和输出。原始 Problem Statement（P）是求解者规范；Requirements、New Interfaces、historical F2P、Gold patch 和仓库代码只作为构造证据。

转换目标是保留 historical F2P 的产品行为意图，并通过 Base 中已有的公开接口、CLI、服务接口、文件输入输出或其他可观测结果验证。最终测试不得要求 Gold 才新增的 helper、私有状态、精确调用形状或内部容器表示。

## 2. 一条 historical F2P 的四种分类

| 分类 | 判定 | 转换动作 | 最终 Harbor 角色 |
|---|---|---|---|
| `p_supported_behavior` | P 已表达，Base 缺失或错误 | 用公开边界改写 | `fail_to_pass` |
| `base_regression_behavior` | P 未新增该要求，但 Base 已有公开产品行为 | 用 Base/Gold 公共边界改写 | `pass_to_pass` |
| `missing_product_behavior` | 重要产品行为不在 P，且 Base 缺失或错误 | 提出最小行为描述，下一 revision 再转换 | 暂不发布 |
| `implementation_detail` | 去掉 helper/表示后没有独立产品行为 | 提供证据后排除 | 不进入测试 |

historical F2P 始终是完整的转换账本，但不是最终 `fail_to_pass` 清单。`base_behavior_status=changed_or_missing` 的 selector 进入 `fail_to_pass`；`already_satisfies` 的 selector 与保留的原始 P2P 一起进入 `pass_to_pass`。

## 3. Pipeline

```text
Stage 1 READY Harbor task
        │
        ▼
Converter（mini-swe-agent）
- 逐条分析 historical F2P
- 拆分 product_behavior / implementation_detail obligation
- 选择 Base/Gold 共同公开边界
- 写静态可审阅 verifier、trace、自审
        │
        ▼
Artifact / schema gate
- 完整 F2P 记账
- selector 角色派生
- instruction provenance
        │
        ▼
Semantic Judge（外部 LLM）
- 检查 P 支持、公开边界、欠转换、隐藏契约
- semantic 阶段位于 hard replay 前，不要求已有 replay
        │
        ▼
Docker hard replay
- Base：功能增量失败；回归通过
- Gold：所有转换测试通过
- 原始 P2P：通过
        │
        ▼
Behavior-role audit
- 对每个 selector 读取结构化 Base/Gold 结果
- 证明 functional delta 与 converted regression 未混淆
        │
        ▼
Stability replay（两轮）
        │
        ▼
Positive QA（mini-swe + fresh Judge + paired replay）
Negative QA（mini-swe + fresh Judge + hard replay）
        │
        ▼
Acceptance → Package → Final audit
```

门禁失败时，只有 verifier 或语义缺陷进入 Converter repair。Judge 传输/JSON 协议失败应重试 Judge，不应创建语义 revision。

## 4. 运行和路径契约

每个运行实例位于：

```text
runs/<instance_id>/
├── source/                         # 本次运行冻结的输入证据
├── attempts/attempt_NNN/
│   ├── intermediate/
│   │   ├── converter/revisions/
│   │   ├── validation/
│   │   ├── qa/
│   │   └── control/
│   ├── final/                      # 仅 accepted convertible 任务存在
│   └── review/
└── latest_attempt.json
```

Docker 内固定使用 `/app` 或 `/testbed` 作为仓库，`/tests` 为只读 verifier，`/logs/verifier` 为结果目录。角色审计按结果 JSON 的 `tests[{name,status}]` schema 读取，兼容 `output.json` 与 `parsed_results.json`。

## 5. Instruction 策略

1. 保留原 Harbor instruction 的包装、PR description 标签和 Constraints。
2. 只删除 PR description 内的 Requirements 与 New Interfaces 区块。
3. Base 已有回归不得扩写 P。
4. 只有 `missing_product_behavior` 经过明确审计后，才在 PR description 内加入最小行为描述。
5. 补充文字不得包含测试路径、helper 名、类/方法签名、Gold 结构或实现方案。

## 6. 两条实验任务的结论

### qutebrowser

11 条 historical F2P 中，10 条可转换为 Base 已有 `QtFont` 产品行为回归；1 条为空输入 helper 特性，公开产品入口在 Base/Gold 都拒绝该输入。没有可证明的 Base FAIL / Gold PASS 功能增量，因此最终状态为 `non_discriminative_task`，不发布 final。

### OpenLibrary

6 条 historical F2P 被证明为：

- 2 条 alternate-script author name 功能增量：Base FAIL、Gold PASS；
- 4 条名称规范化既有回归：Base PASS、Gold PASS；
- 0 条 drop，0 条 specification gap，0 条 instruction addendum。

最终 rev_007 通过 Semantic Judge、Hard Replay、角色审计、两轮稳定性、Positive QA、Negative QA 和 final audit，并发布到 `attempt_008/final`。
