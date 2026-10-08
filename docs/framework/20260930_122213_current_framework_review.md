
# 当前 Harbor-to-Harbor 功能性转换框架（审计整理版）

更新时间：2026-09-30 12:22 UTC  
状态：框架设计审阅稿；本文更新后暂不重新运行任务。

## 1. 目标与当前判断

目标是保留 historical F2P 的功能行为意图，把绑定 Gold 或历史内部实现的断言，改写为基于 Base 仓库已有公共接口或可观察产品行为的 verifier。

当前框架偏复杂的根因不是 Harbor 任务本身复杂，而是把三件事混在了一起：

1. 从 F2P 恢复真正想验证的行为；
2. 判断哪些接口可以作为观察面；
3. 把缺失功能语义写回最终 Problem Statement。

这三个环节现在必须分开。唯一的数据流如下：

    Stage 1 原始 Harbor 任务
            │
            ▼
    source/：基础 Problem Statement + construction evidence
            │
            ▼
    mini-swe Converter：逐条恢复行为并生成 verifier revision
            │
            ▼
    Controller：结构校验 + 严格接口/表面校验 + Semantic Judge
            │
            ├── specification_gap
            │       └── 生成行为级补充，嵌入 PR description，重新转换
            │
            ▼
    Docker Hard Replay：Base / Gold / P2P
            │
            ▼
    Stability Replay
            │
            ├── Positive QA：不同实现仍通过
            └── Negative QA：违反一个功能行为时失败
            │
            ▼
    Acceptance
            │
            ▼
    Package final Harbor + 刷新 review 审计文件

最终只发布通过全部门槛的 final/。中间 revision、gap、失败候选不能直接成为最终任务。

## 2. 数据和权限边界

原始任务保持在：

    tasks/<instance_id>/original/
    ├── instruction.md
    ├── task.toml
    ├── tests/
    ├── solution/
    └── environment/

该目录只读。

本次运行保持在：

    runs/<instance_id>/
    ├── source/
    └── attempts/
        └── attempt_NNN/
            ├── intermediate/
            │   ├── converter/revisions/rev_NNN/
            │   ├── specification_addendum.md
            │   ├── validation/
            │   ├── qa/
            │   └── control/
            ├── review/
            └── final/

TaskPaths 是所有宿主机路径的唯一来源。组件不能根据当前工作目录猜路径。Docker 内部只使用镜像约定的 /app 或 /testbed。

三类材料的权限如下：

| 材料 | 用途 | 是否直接进入最终 instruction |
|---|---|---|
| Problem Statement | 规范性功能语义 | 是 |
| Requirements / Interface | 恢复行为和候选观察面 | 否 |
| historical F2P / P2P / Gold | 行为证据、回放和 QA | 否 |

## 3. Converter 的职责和 revision

mini-swe Converter 每次只生成一个 revision：

    rev_NNN/
    ├── tests/test.sh
    ├── tests/run_script.sh
    ├── tests/parser.py
    ├── tests/config.json
    ├── conversion_trace.json
    ├── functional_specification.md
    ├── self_review.md
    └── manifest.json

Converter 不修改原任务，不修改 instruction，不把 Requirements 或 Interface 原文复制进最终包。

每条 canonical F2P 在 conversion_trace.json 中保留一行，至少包括：

- behavior_intent：想验证的行为；
- functional_surface：公开接口、CLI、文件、服务、输出或异常；
- problem_statement_support：P 是否已经描述；
- base_repo_observable：Base 是否存在该观察面；
- gold_only_binding：是否只出现在 Gold；
- decision：rewrite、merge、drop 或暂时的 specification_gap；
- emitted_tests：实际生成的测试；
- rationale：转换理由。

多个 F2P 可以合并成一个行为测试，但每个原 selector 必须能追溯到 emitted test。

## 4. F2P 决策规则

### rewrite

保留行为意图，改用公共或可观察表面验证。

### merge

多个历史样例共享一个功能契约时合并，但不能丢掉边界样例。

### specification_gap

行为属于产品功能、可以被观察，但基础 P 没有清楚描述。它是自动补充信号，不是最终结果：

1. Converter 提交行为级提案；
2. Controller 生成补充文本；
3. 补充文本进入下一轮 Converter 的有效 P；
4. 新 revision 重新走所有门槛。

### drop

只有纯实现细节可以 drop，例如：

- 私有字段、内部缓存、内部容器；
- mock 调用次数或精确调用形状；
- Gold 专用 helper、临时文件和 bookkeeping；
- 没有独立产品行为的测试 plumbing。

“用了新 class”“找不到同名 API”“测试调用 constructor”都不是 drop 理由。先恢复功能行为；P 不足时走 specification_gap。

## 5. 观察面授权：当前最重要的规则

必须区分公共契约与 Gold 中看起来像公共的名字。

### 5.1 优先级

1. Base 已存在的公共产品边界：已有读取函数、CLI、HTTP 接口、文件格式、公开返回值或用户可见错误；
2. P 明确写出的完整 qualified contract；
3. Gold-only 符号：只在 Gold、Interface 或历史测试中出现而 Base 不存在，不能自动成为解题要求。

### 5.2 严格授权

P 中只出现一个类型名，不会自动授权该类型的任意方法、构造器或属性。

例如，P 只写“引入 FontFamilies”，但 verifier 直接调用 configutils.FontFamilies.from_str，而 Base 中不存在该类和方法。这仍然是新增实现接口绑定。它必须改写到已有配置行为或其他公共边界；找不到边界时先补充行为语义，再重新设计测试。

Semantic Judge 和 deterministic gate 必须采用同一规则，不能一个放行、另一个拒绝。

## 6. instruction 生成

最终 instruction 由原始 Problem Statement 和自动审核通过的行为级补充组成。

Requirements、New Interfaces、functional proposal 记录和 F2P selector 账本不直接进入最终任务。

补充文本只能说明用户可观察的输入、输出、功能规则和边界；不能包含历史 selector 路径、某条测试要求、Gold helper、实现算法、隐含 API、module path 或 method signature，除非完整契约本身就是 P 明确规定的公共接口。

补充必须插入原 instruction 的 <pr_description> 内部，在 </pr_description> 之前。这样解题 agent 看到的是一份完整 PR，而不是 PR 外部的框架注释。

## 7. Controller 和验证门槛

门槛顺序固定为：

    Artifact Contract
          ↓
    Strict Base/Gold surface check
          ↓
    Semantic Judge
          ↓
    Hard Replay
      ├── Base + functional verifier：应失败
      ├── Gold + functional verifier：应通过
      └── Base/Gold + retained P2P：都应通过
          ↓
    Stability Replay
          ↓
    Positive QA
          ↓
    Negative QA
          ↓
    Acceptance
          ↓
    Package + refresh review

门槛失败时，Controller 写入结构化 feedback，创建下一个 revision，并从该 revision 重新执行后续门槛。达到上限仍失败则自动拒绝。

LLM 的职责：

- Converter agent：生成 verifier 和 F2P 账本；
- Semantic Judge：判断行为保留、实现绑定和 under-conversion；
- Positive/Negative QA agent：生成不同实现和 near-correct mutant；
- QA Judge：判断候选语义；
- Docker 和 deterministic validator：给出执行事实。

LLM 不能覆盖 Docker 失败，Docker 也不能证明没有隐藏接口绑定。

## 8. QA 最小定义

Positive QA 构造和 Gold 实质不同但满足 P 的实现。Functional verifier 必须通过；原始 historical verifier 因实现绑定而失败是允许的。

Negative QA 构造只破坏一个已转换功能的近似实现。Judge 确认它违反 P，Functional verifier 必须失败。

QA agent 即使达到步数上限，只要已经写出 patch 和 metadata，也可以恢复；恢复后仍必须经过 Docker replay 和 Judge。

## 9. Acceptance、打包和审计

Acceptance 的权威输入是同一 revision 的：

    conversion_trace.json
    validation/semantic/review.json
    validation/hard_replay/result.json
    validation/stability/result.json
    qa/positive/summary.json
    qa/negative/summary.json

final/ 只有在该 revision 的所有门槛通过后生成。

Package 完成后必须再次生成：

- review/metrics.json
- review/summary.json
- review/conversion_report.md
- review/f2p_mapping.csv

审计状态必须反映最终是否打包，不能保留打包前的 rejected 状态。

## 10. 当前两条任务的审计结论

### qutebrowser

账本层面：

- 11/11 条 F2P 有映射；
- 10 条 merge、1 条 rewrite；
- 没有 drop；
- Hard replay、stability、QA 均有记录。

目标层面仍有问题：

- 最终测试直接调用 configutils.FontFamilies.from_str 和 FontFamilies(...)；
- Base probe 已记录这两个符号是 Base 不存在的 Gold-only candidates；
- P 只写了 FontFamilies 类型名称，没有明确授权完整 qualified method contract；
- 因此不是完全 implementation-agnostic 的 functional verifier。

结论：不能因为 F2P 全部映射和 replay 通过，就把 qutebrowser 判为目标完成。需要按严格观察面规则重新生成 revision。

### OpenLibrary

- 6/6 条 F2P 都有映射；
- 4 条 helper 测试改到 read_edition(MarcBinary) -> authors；
- alternate-script 测试观察作者数据输出；
- 没有调用 Gold-only name_from_list；
- 主要测试边界符合功能性目标。

仍需修正 instruction 形态：行为补充原来位于 </pr_description> 之后，应该并入 PR 描述内部。MARC 输入规则、作者输出字段和规范化边界属于产品行为，可以保留，但不能写成历史测试来源或实现步骤。

结论：OpenLibrary 的 verifier 设计基本合格；最终 instruction 需要按新的打包规则重新生成。

## 11. 这次整理后要做的事情

1. 重新转换 qutebrowser，禁止直接调用 Base 不存在且 P 未完整授权的新 API；
2. 重新打包 OpenLibrary，把行为补充放入 <pr_description>；
3. 两条任务重新执行 Semantic、Hard Replay、Stability、Positive QA、Negative QA；
4. 确认 Package 后 review 文件自动刷新；
5. 只有满足以上条件的新 attempt 才能作为最终有效结果。

在此之前，旧 attempt 只作审计证据，不作为新的框架基线。


## 12. 2026-10-01 路径与挂载契约修复记录

本次 qutebrowser 单条转换暴露了一个与具体任务无关的路径问题。转换流程同时涉及三种路径空间：

1. 宿主机项目路径，例如 runs/<instance_id>/attempts/<attempt>/...；
2. Converter/QA 容器的逻辑工作区 /workspace；
3. Harbor 镜像内的仓库 /app 或 /testbed。

此前的设计让 mini-swe agent 以为 app/、evidence/、solution/ 都能从 /workspace 的相对路径访问，但 /workspace 实际由镜像提供且属于 root。非 root agent 无法创建 app -> /app 链接，导致同一容器内出现：

- evidence/ 可以访问；
- app/ 不存在；
- 直接进入仓库、运行 Base 探查和生成 verifier 的步骤互相不一致。

同时，多个 Python 模块用不同的 Path(__file__).parents[n] 推断项目根，导致默认 .env 和 configs/experiment.yaml 曾被解析到项目父目录。

当前统一规则：

- src/swepro_trans.paths.PROJECT_ROOT 是唯一宿主项目根；
- CLI、Converter、Semantic、QA、Pipeline、Reporting 和 Runtime 都从该常量解析配置、prompt、参考文档和 subprocess cwd；
- mini-swe sandbox 根作为可写 /workspace 挂载；
- sandbox 预置 app -> /app 和 testbed -> /testbed 链接；
- evidence/、reference/、run/ 使用只读子挂载，scratch/ 和 solution/ 保持角色所需的可写边界；
- 生成的 verifier 在 Harbor 执行时仍以 /app 或 /testbed 为仓库边界，不能把宿主路径写入 artifact；
- controller、validator 和 QA 使用同一个 TaskPaths/attempt 路径解析结果，不能各自猜测目录。

这条规则适用于所有任务，不依赖 instance、repo、commit 或测试名称。任何新角色若需要新增挂载，必须同时更新：

- TaskPaths 的路径属性；
- mini-swe workspace layout；
- Docker mount contract；
- 对应 prompt；
- 至少一次非 root 容器 dry-run 或真实运行验证。

本次 qutebrowser 证据：

- 第一次会话在错误路径契约下反复出现 ls: cannot access app；
- 修正后 rev_001 的 11 条 F2P 均被识别为 missing_product_behavior/specification_gap，没有再被全量错误 drop；
- controller 自动生成行为级 addendum，并在 rev_002 将这些行为重新转换为 11 条 p_supported_behavior/rewrite；
- rev_002 仍需经过 Semantic 的严格 qualified-symbol 检查，不能因为 addendum 或 Gold 中出现类名就自动授权其方法和构造器。


### 12.1 后续统一入口补充（2026-10-01）

复核后又发现 CLI 默认参数仍有少数模块直接使用 `Path(__file__).parents[n]`。这类写法虽然在当前源码层级下通常可用，但一旦通过可编辑安装、模块入口或不同工作目录启动，就会再次产生漂移。现已统一改为从 `swepro_trans.paths.PROJECT_ROOT` 解析 `.env`、实验配置和框架内置 runner。以后新增入口不得自行推断项目根；需要解析路径时必须使用 `PROJECT_ROOT`、`project_file()` 或 `TaskPaths`。

此外，运行环境 bootstrap 中也移除了上一台机器的绝对 Python 路径；现在只按 `SWEPRO_PYTHON`、PATH 中的 `python3.12`、当前解释器顺序选择。这样 Docker、宿主机和 CI 不会因为某个机器目录存在与否而产生不同结果。

## 13. 2026-10-01 三类 F2P 判定的修正规则

Converter 现在先判断 F2P 是否增加了**可观察契约**，再判断它使用的符号是否是新增实现。决策顺序固定为：

| 判定 | 条件 | 处理 |
|---|---|---|
| `p_supported_behavior` | Problem Statement 已描述行为，且可以从 Base 的公共 API、CLI、文件/服务边界、持久化状态或用户输出观察 | `rewrite`/`merge`，测试公共边界 |
| `missing_product_behavior` | 行为属于用户可观察、持久化或产品输出，但 Problem Statement 没写 | `specification_gap`，生成不含 API 名称的行为级补充；下一 revision 再改写成测试 |
| `implementation_detail` | F2P 只检查 Gold 新增类/方法/构造器、私有结构、内部缓存、mock 形状、fixture 或测试 plumbing，且相同行为已由 Base 公共边界或保留的 P2P 覆盖 | `drop`，记录具体证据和不损失产品语义的理由 |

“出现了新类”本身不能触发 drop，也不能自动触发 specification gap。必须先确认该 F2P 是否提出了超出已有公共行为覆盖的新契约。反过来，也不能为了保留每一行而调用旧 helper；如果那只是在复制已经被 P2P 覆盖的行为，应按 implementation detail 处理。

Schema 现在额外约束：`p_supported_behavior` 必须填写 Base 可观察面；`missing_product_behavior` 在补充 P 的 revision 之前不得产生最终测试；`implementation_detail/drop` 不得伪造 functional test。Semantic Judge 使用同一规则审阅，并保持二值 PASS/FAIL。

### 13.1 纯实现细节任务的回放策略

若一条任务的所有 F2P 都被证据支持为 `implementation_detail/drop`，它没有可保留的功能性 F2P；此时不能为了满足“Base 必须失败”而重新引入 Gold-only API。框架现在根据 revision trace 自动选择：

- 保留至少一条 `rewrite/merge`：Base 必须 FAIL、Gold 必须 PASS；
- 全部 `drop`：Base 和 Gold 都必须 PASS，且稳定性只验证保留的 P2P；Positive/Negative QA 标记为 `no_retained_functional_f2p`，不虚构候选实现。

这只适用于完整、有证据的实现细节判定；只要存在一条真实功能行为，就继续使用 Base FAIL/Gold PASS，并要求该行为有公共或可观察测试。
