# 当前 Harbor-to-Harbor 测试功能性转换框架

- 更新时间：2026-10-01 11:06:47 UTC
- 状态：当前实现与五条任务验证一致
- 规范依据：`docs/optimize_rule.md`
- 适用范围：Stage 1 已通过、输入和输出均为 Harbor 任务的 SWE-Bench Pro v2 实例

## 1. 框架目标

框架只转换任务的 verifier，并在必要时补齐缺失的行为级说明：

1. 保留 original instruction 的仓库说明、`<pr_description>` 包装和通用约束；
2. 去掉 `Requirements` 与 `New Interfaces` 提供的实现约束；
3. 将每条 historical F2P 转为基于公开接口或可观察产品行为的 functional test；
4. 保留 P2P 回归范围；
5. 用语义审计、Base/Gold 重放、稳定性以及正负 QA 证明转换质量；
6. 只有全部门禁在同一 revision 上通过，才生成完整 Harbor `final/`。

转换不是把历史断言换一种语法。它要保留历史测试真正检查的功能语义，同时移除 private helper、Gold 新增内部 API、DOM 结构、内部容器、mock 调用形状等实现绑定。

## 2. 规范与证据的权威顺序

| 材料 | 作用 |
|---|---|
| Problem Statement（P） | 解题者的基础规范性语义 |
| controller 审计生成的 behavior addendum | P 缺少但 historical F2P 明确要求的产品行为补充 |
| historical F2P | 定义本次需要转换的行为范围 |
| Requirements / Interface | construction evidence，不直接进入最终 instruction |
| Base repository | 判断接口是否存在、是否属于稳定产品边界 |
| historical tests / P2P | 理解行为和回归范围 |
| Gold | 已知正确实现与验证证据，不能反向成为唯一规范 |
| verifier taxonomy | 设计参考，不是任务要求 |

“符号存在于 Base”并不自动说明它是公开观测面。UI 行为能从可访问文本、role、控件状态、导航、持久状态或外部服务效果直接观察时，不允许改用内部 modal/router/store/component 调用来代替。外部客户端的公开副作用可以通过 mock/fake 观察，但不能把内部 UI factory 的精确调用形状当成功能结果。

## 3. 代码板块

| 板块 | 主要文件 | 职责 |
|---|---|---|
| CLI | `src/swepro_trans/verifier_conversion.py` | 统一入口：init、agent、pipeline、package、final-audit |
| 路径合同 | `src/swepro_trans/paths.py` | `TaskPaths`、canonical path、attempt/revision 定位 |
| 目录与发布 | `src/swepro_trans/layout.py` | 初始化 run、构造 final、同 revision 安全重打包与归档 |
| Converter agent | `agents/runner.py`、`agents/mini_swe_session.py` | mini-swe BUILD/REPAIR 会话、受限 workspace、产物恢复 |
| Judge | `agents/judge.py`、`model_clients/` | 无工具 LLM Judge、JSON 闭集协议、续答与超时 |
| 编排 | `pipeline/orchestrator.py` | 固定门禁顺序、自动规范补充、接受和发布 |
| Repair | `pipeline/repair.py` | copy-forward 上一 revision、结构化反馈、下一 revision |
| 语义验证 | `validation/semantic.py` | P 支持、F2P 保真、Gold-only/内部绑定、drop 审计 |
| 硬验证 | `validation/revision.py` | artifact/schema、Base/Gold Docker replay、repo clean gate |
| 稳定性 | `validation/stability.py` | F2P/P2P 重复重放；空 P2P 不启动无意义容器 |
| QA | `qa/session.py`、`qa/runner.py`、`qa/replay.py` | mini-swe 正/负候选、fresh Judge、paired replay |
| 接受与终审 | `validation/acceptance.py`、`validation/final_audit.py` | 同 revision 门禁聚合、发布后严格审计 |
| 人审投影 | `reporting/human_review.py` | `review/` 中的报告、指标和 F2P 映射 |
| 策略与参数 | `prompts/`、`configs/experiment.yaml` | 角色 prompt、轮次、超时、重试和 QA 目标 |

Converter、Positive QA、Negative QA 都在 mini-swe-agent 循环中运行。Semantic/Solution/Mutation Judge 在 agent 外部由 controller 调用，Judge 不获得仓库写工具。这样 agent 能根据结构化反馈修复，最终决定仍由独立门禁作出。

## 4. 目录与路径合同

原始任务只有一个权威位置：

```text
tasks/<instance_id>/original/
```

只有实际开始转换的任务才创建 run：

```text
runs/<instance_id>/
├── source/                         # 该 run 使用的 Stage 1 evidence
├── attempts/
│   └── attempt_NNN/
│       ├── intermediate/
│       │   ├── converter/
│       │   │   ├── revisions/rev_NNN/
│       │   │   └── trajectory/
│       │   ├── validation/
│       │   ├── qa/positive/
│       │   ├── qa/negative/
│       │   ├── packaging/
│       │   ├── control/
│       │   └── specification_addendum.md   # 仅在需要时出现
│       ├── review/                 # 人审报告与 final_audit.json
│       ├── final/                  # 全部门禁通过后才生成
│       └── archived/               # 被安全替换的旧 final，仅在需要时出现
├── latest_attempt.json
└── run_manifest.json
```

目录按需创建，不依靠空目录表达状态。`TaskPaths` 是路径的唯一来源；CLI 在边界处把路径 canonicalize，子进程接收绝对路径。模块不得根据当前工作目录、最大编号或字符串拼接猜测任务位置。

### mini-swe workspace

agent 的 workspace 只是一次会话的隔离运行面：

```text
/workspace/
├── app/ 或 testbed/       # Docker 中的仓库
├── evidence/              # P、R/I、historical tests 等只读证据
├── reference/             # taxonomy 等设计参考
├── solution/              # agent 唯一允许提交的 revision/candidate 产物
└── scratch/               # 临时文件
```

它不是第三份任务数据，也不会进入 final。Docker 并不能替代 host 侧路径 schema；host 仍需准确决定挂载哪一个 task、attempt 和 revision。

## 5. Converter 的逐条决策

每条 canonical F2P 必须进入 `conversion_trace.json`，使用以下三分类：

| classification | final decision | 处理 |
|---|---|---|
| `p_supported_behavior` | `rewrite` / `merge` | 在 Base 已有的公开或可观察边界重写 |
| `missing_product_behavior` | `specification_gap` | 先提出纯行为级补充，下一 revision 再 rewrite/merge |
| `implementation_detail` | `drop` | 只有移除实现机制后完全没有独立产品行为时允许 |

`merge` 表示多个 historical F2P 共享一个等价功能测试，不表示丢弃。重复覆盖、已有 P2P、测试名过时都不能单独构成 drop 理由。

每行还要记录行为意图、P 支持、Base 可观察性、绑定风险、发出的测试 selector、证据与理由。schema 会检查遗漏、重复、额外 selector 和 classification/decision 不一致。

## 6. 规范补充与 instruction 生成

当 F2P 确实表达重要产品行为，但基础 P 没写时：

1. Converter 标记 `missing_product_behavior + specification_gap`；
2. controller 只提取行为级 proposal，写入 `intermediate/specification_addendum.md`；
3. 下一 revision 读取 addendum，把对应行改为 `p_supported_behavior + rewrite/merge`；
4. addendum 通过全部门禁后，才插入最终 `<pr_description>` 内。

addendum 不得包含类名、方法名、模块路径、签名、Gold 文件或算法。最终 instruction 保留原 preamble、PR wrapper 和 constraints；`Requirements`、`Interface`、`functional_specification.md` 不进入 final。

## 7. 实际 pipeline

```text
Stage 1 READY Harbor task
        │
        ▼
mini-swe Converter BUILD / REPAIR
  ├─ 逐条 F2P 恢复功能语义
  ├─ 选择 Base public / observable surface
  ├─ 生成 tests + conversion_trace + self_review + manifest
  └─ 先提交完整骨架，再做聚焦改进
        │
        ▼
Artifact / schema / accounting gate
        │
        ├─ specification_gap
        │      └─ controller 生成 behavior addendum
        │          → copy-forward → mini-swe REPAIR
        ▼
Semantic Judge
  ├─ P/addendum 支持
  ├─ historical behavior 保真
  ├─ under-conversion / unjustified drop
  ├─ Gold-only、内部 helper、mock call shape 绑定
  └─ 必须输出 PASS/FAIL；UNCERTAIN 不可通过
        │ FAIL
        └─ structured feedback → copy-forward → REPAIR
        ▼
Hard replay
  ├─ functional expectation：
  │    changed_or_missing → Base FAIL / Gold PASS
  │    already_satisfies → Base PASS / Gold PASS
  ├─ retained P2P → Base PASS / Gold PASS
  ├─ verifier 可运行、selector 可收集
  └─ functional verifier 前后 git status 必须一致
        │
        ▼
Stability：F2P/P2P 各重复 2 次
        │
        ▼
Positive QA（mini-swe + fresh Judge + paired replay）
        │
        ▼
Negative QA（mini-swe + fresh Judge + hard replay）
        │
        ▼
Acceptance → Package final → Human review → Final audit
```

Base 不一定总要失败。如果目标行为在 Base 已经存在，只是 historical verifier 绑定了某种重构实现，则正确 expectation 可以是 Base/Gold 都通过。框架禁止为了制造 Base FAIL 而调用 Gold-only symbol。

## 8. Docker、historical test patch 与副作用

- 使用 Stage 1 记录的官方镜像、repo root 和运行环境，不按语言猜 runner；
- `/tests` 以只读方式挂载，生成测试、parser 输出和缓存写到 `/tmp` 或日志挂载；
- 某些 retained P2P selector 来自 historical `test_patch.patch`，Base 和 Gold solution patch 本身都不包含这些测试。revision 必须把 test patch 作为测试资产打包，在执行前应用，并在 `EXIT` trap 中完整反向恢复；
- functional verifier 运行前后比较 `git status --porcelain --untracked-files=all`，变化即以 infrastructure code 92 拒绝；
- historical/original verifier 允许其原本的测试 scratch 行为，但超时、容器失败、路径错误和 91/92 等 infrastructure failure 不能伪装成 Negative QA 成功。

## 9. Repair 与恢复

失败后不会从空目录重新生成：

1. controller 创建下一 revision；
2. `seed_revision` copy-forward 上一版完整 verifier 与账本，排除 cache；
3. `repair_feedback.json` 写入 semantic、hard replay、stability 或 QA 的结构化证据；
4. mini-swe 只读反馈和相关 Base 文件，做聚焦修复；
5. 从 artifact/semantic 开始重新验证，并重放已有 QA。

如果 agent 达到轮次上限但已写出完整产物，controller 接管这些产物继续门禁；若只缺少 manifest/self-review 等收尾文件，则启动一次有限 artifact-completion 会话。endpoint 失败属于 transport/protocol 问题，不创建伪语义 revision。

## 10. Positive 与 Negative QA

### Positive QA

mini-swe 构造满足 P、但实现结构与 Gold 明显不同的正确解。fresh Solution Judge 判定 `VALID`；original verifier 与 functional verifier 都要完成 paired replay，functional verifier 必须通过。

### Negative QA

mini-swe 从 Gold 或已接受 positive 构造只违反一个明确功能语义的 near-correct mutant。fresh Mutation Judge 必须判定 `RELEVANT_NON_EQUIVALENT`，functional verifier 必须失败。容器、路径、timeout、repo 污染等基础设施失败不能算作成功拒绝。

## 11. 发布与审阅

`final/` 是可直接运行的完整 Harbor task：

```text
final/
├── instruction.md
├── task.toml
├── environment/
├── solution/
└── tests/
```

`review/` 提供：

- `conversion_report.md`
- `f2p_mapping.csv`
- `metrics.json`
- `summary.json`
- `final_audit.json`

同一 accepted revision 因通用打包策略变化需要重建时，旧 final 会先进入 `archived/`，不会被静默覆盖。

## 12. 当前验证基线

截至 2026-10-01 11:06:47 UTC，五条任务全部通过 current schema 严格终审：

| 任务 | attempt / revision | historical F2P | final decision | 结果 |
|---|---|---:|---|---|
| Element Web | attempt_002 / rev_009 | 10 | 5 rewrite + 5 merge | PASS |
| OpenLibrary alternate names | attempt_007 / rev_002 | 6 | 6 rewrite | PASS |
| OpenLibrary work fields | attempt_002 / rev_001 | 1 | 1 rewrite | PASS |
| qutebrowser | attempt_013 / rev_001 | 11 | 11 rewrite | PASS |
| Tuta | attempt_002 / rev_001 | 2 | 2 rewrite | PASS |

合计 30/30 F2P 已记账，25 rewrite、5 merge、0 drop、0 unresolved gap。五条任务的 instruction leakage、semantic、hard replay、stability、positive QA、negative QA、acceptance 与 final artifact 均为 PASS。

## 13. 常用命令

完整 pipeline：

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans.verifier_conversion pipeline \
  --task-root runs/<instance_id>/attempts/<attempt> \
  --revision runs/<instance_id>/attempts/<attempt>/intermediate/converter/revisions/<revision>
```

单条终审：

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans.verifier_conversion final-audit \
  --task-root runs/<instance_id> --write
```

全部当前 run 终审：

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans.verifier_conversion final-audit \
  --all-runs --write
```

终审以 `latest_attempt.json`、`acceptance.json` 和 accepted revision 为准，不根据目录编号猜测结果。
