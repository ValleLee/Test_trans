# SWE-bench Pro 功能测试转换方案：待讨论

> 日期：2026-09-28  
> 目的：整理当前关于 SWE-bench Pro、DeepSWE/Harbor、R/I 去除和功能性 verifier 转换的疑问，形成可评审的实验方案。

## 1. 我们真正要解决的问题

当前项目最初被表述为“把 SWE-bench Pro 的 F2P 测试转换成更功能性的测试，并解除测试与具体实现的绑定”。
上一步实验把任务改造成 DeepSWE 的任务形式
但在想是否应该保持 SWE-bench Pro 任务语义和求解流程，只替换或扩展 verifier，使它在不依赖 `requirements` 和 `interface` 的情况下仍能检查目标行为。

因此需要先确定主问题是哪一个：

1. **测试转换问题**：给定同一个 SWE-bench Pro 任务，研究从原始测试到功能性测试的转换是否提高了测试对实现方式的包容性。
2. **任务提示消融问题**：研究去掉 `requirements` 和 `interface` 后，模型能否仅凭 `problem_statement` 完成任务。
3. **端到端数据格式问题**：把任务改写成 DeepSWE 风格，使其可以在另一套任务/agent 流程中运行。


## 2. 目前的核心疑惑

### 2.1 SWE-bench Pro 和 DeepSWE 是否已经统一了任务形式

2026-09-22 发布的 SWE-bench Pro V2 使用 Harbor task format。Harbor 更像任务运行、容器环境和评测编排的外壳；`LockedMiniSwe`、`LockedCodex`、`LockedClaudeCode` 等是让 agent 进入仓库、读代码和修改代码的 scaffold/driver。三者需要分开：

| 层次 | 作用 | 是否应作为本项目的研究变量 |
|---|---|---|
| Harbor task/package | 镜像、仓库、运行脚本、verifier、结果解析和任务元数据 | 尽量固定 |
| Agent scaffold | 模型如何进入 repo、执行命令和提交修改 | 尽量固定 |
| Problem/verifier 内容 | 提示包含什么、测试检查什么行为 | 本项目的主要变量 |

所以可以说 SWE-bench Pro 和 DeepSWE 在运行外壳上趋于兼容，但不能据此说二者在任务语义、instruction 写法和测试目标上已经统一。
DeepSWE 的抽象 instruction 形式可以参考其功能测试类别，但不应自动成为 SWE-bench Pro 转换后的内容标准。

### 2.2 最终 instruction 应该是 SWE-bench Pro 风格还是 DeepSWE 风格

当前有两种相互混淆的选择：

- 保留 SWE-bench Pro 的 `problem_statement`，只移除 `requirements`/`interface`，并替换 verifier；
- 把内容重写成更抽象、更像 DeepSWE 的 solver-facing instruction。

如果研究问题是“功能性 verifier 是否能摆脱 R/I 与 gold patch 的绑定”，第一种更干净。这样只改变被研究的因素，最终仍能解释为 SWE-bench Pro 任务上的 verifier 转换结果。第二种会同时改变提示的措辞、信息量和任务表达，容易把“提示重写带来的影响”误认为“verifier 改进”。

建议：以原始 SWE-bench Pro V2 Harbor task 为 canonical source；保留原始 `problem_statement` 作为主提示；把 DeepSWE 风格作为可选的 presentation/runtime variant，而不是默认语义。

### 2.3 去掉 R/I 后，是否还算同一个任务

不算完全相同的 prompt 条件。原始 SWE-bench Pro 的 `requirements` 和 `interface` 是数据集作者为配合 verifier/gold patch 提供的附加约束；去掉它们会形成一个新的 prompt ablation。即使仓库、base commit 和 problem statement 相同，也需要在报告中明确标记为不同条件。

因此应避免把“无 R/I + 新 verifier”的结果直接称作只由 verifier 转换造成的提升。

### 2.4 原始 problem statement 是否已经绑定具体实现

总体上，problem statement 通常描述 PR 目标和可观察行为，但不能假设它永远完全实现无关。不同任务中可能出现文件名、符号名、公共 API、序列化格式或可定位的实现线索。`requirements` 和 `interface` 更经常包含精确函数名、路径、参数、类名和测试相关约束。

所以应区分：

- **行为约束**：输入、输出、错误、状态变化、兼容性和用户可观察结果；
- **实现线索**：具体文件、函数、类、内部数据结构或测试 fixture；
- **接口契约**：必须保留的公开 API、签名、导入路径和兼容格式。

转换目标不是机械删除所有具体名词，而是保留必要的公开契约，删除只为复现 gold patch 或原测试写法服务的内部实现提示。

## 3. 当前两条样例暴露出的具体问题

### 3.1 navidrome

原始问题涉及 Last.fm、ListenBrainz 和 Spotify 客户端封装，要求降低底层 HTTP 客户端的暴露程度，同时保持高层行为。原始 `test.patch` 包含较丰富的运行时行为检查：请求构造、解析、错误处理，以及部分 agent/router 场景；但 F2P selector 是 suite-level 的 `TestLastFM`、`TestListenBrainz`、`TestSpotify`，P2P 为空。

当前转换后的 verifier 主要检查包构建和外部编译探针，例如外部代码不能使用 `NewClient` 或 `Client`。这能验证 API 可见性和外部兼容边界，但没有逐一重放原始 F2P 中的运行时行为，也没有覆盖 agent/router 回归。

这里要区分两个来源：

1. 原始 F2P 选择器没有把每个行为测试逐条暴露出来，这是源数据测试选择粒度造成的证据限制；
2. 转换 verifier 又主动把重点收窄到可见性和编译边界，因此运行时覆盖进一步减少。

不能把第 2 点全部解释为“原来的 F2P 本来就没有覆盖”。如果最终只保留 API 边界测试，需要在报告中标成转换范围或 `spec_gap`，并说明高层行为没有被当前 verifier 重新确认。

### 3.2 qutebrowser

原始问题是把 `hide_qt_warning` 和相关测试从 `log.py` 移到 `qtlog.py`，保持行为不变。原始 F2P 覆盖四种 warning 过滤情形：显式 logger、精确匹配、前缀匹配和带空白的匹配。

当前功能性 verifier 通过公共 `hide_qt_warning` 和标准 logging handler 检查可观察的过滤行为，避免依赖私有过滤器类和 pytest 的内部捕获机制。这是较好的功能解耦方向。

但它没有直接验证退出 context manager 后 warning 是否恢复，也没有验证默认 logger=`qt` 路径。如果这些行为没有 F2P seed 支持，就不应从 problem statement 猜测为强制新增测试；应记录为 `spec_gap` 或 supplemental coverage。

## 4. “只保留 problem statement”与当前 instruction 的内容差异

当前最终 instruction 通常比原始 problem statement 多出以下内容：

1. 对任务范围的重新解释，例如明确哪些 API、边界或内部结构属于 scope；
2. 对测试/验证方式的暗示，例如说明外部编译探针、公共 API 或“两个边界都要独立移除”；
3. 对非目标行为的排除，例如声明 private helper、内部结构不在范围内；
4. 从 `requirements`/`interface` 提炼出的精确符号、路径和签名；
5. 为 DeepSWE/新 runner 添加的执行或提交说明。

这些内容会让任务更容易执行，但也可能泄露 verifier 的检查形状，导致模型针对测试而不是理解行为进行实现。需要把“必要的行为/公开契约”与“测试实现提示”分开记录。

## 5. 建议的统一实验设计

为了量化并分离变量，建议至少做 2×2，而不是只比较三种条件：

| 条件 | Prompt | Verifier | 作用 |
|---|---|---|---|
| A | 完整 `problem_statement + requirements + interface` | 原始 verifier | SWE-bench Pro 基线 |
| B | 仅 `problem_statement` | 原始 verifier | 测量去 R/I 的提示消融 |
| C | 仅 `problem_statement` | 新功能性 verifier | 目标条件：无 R/I 下的功能测试 |
| D | 完整 R/I | 新功能性 verifier | 单独测量 verifier 转换效果 |

用户当前提出的三种条件（A、B、C）可以先跑，但缺少 D，无法判断 A 到 C 的变化究竟来自去掉 R/I，还是来自新 verifier。D 是解释因果效果所需的最小补充。

所有条件应固定：

- base commit、仓库快照、容器镜像和依赖；
- Harbor task wrapper、run script、结果解析和超时策略；
- agent scaffold、模型、随机种子、预算、重试和网络权限；
- patch 提交协议和初始工作区。

只切换 prompt 字段和 verifier 版本。若采用 DeepSWE 风格重写 instruction，应单独增加一个“提示重写”实验，不能和主结果混在一起。

## 6. 新 verifier 的证据边界

新 verifier 应按以下优先级构建：

1. 原始 F2P 测试中可观察且与实现无关的行为；
2. problem statement 中明确要求的行为；
3. `requirements`/`interface` 中明确的公开接口契约；
4. 只有在有 seed、官方文档或仓库既有测试证据时，才增加补充行为。

没有证据支持的新增行为不能仅凭“看起来合理”写进强制 verifier。应使用 `spec_gap`、supplemental 或 coverage note 标记。否则新 verifier 可能从“验证功能”变成“重新设计规格”。

同时，功能性测试不等于只测黑盒高层流程。公开 API 的导入路径、签名、错误类型、日志、序列化和兼容性也可以是功能契约；关键是测试不应要求某个私有类、文件布局或 gold patch 的具体结构。

## 7. 需要向 Mentor 确认的决策

1. 项目主论文/报告的研究问题是否明确限定为“verifier 转换”，而不是“DeepSWE 任务重写”？
2. 是否把原始 SWE-bench Pro V2 Harbor task 作为唯一 canonical source？
3. 主实验是否采用 2×2（完整/无 R/I × 原 verifier/新 verifier），并把三条件结果作为简化报告？
4. `requirements` 和 `interface` 在转换中是：
   - 完全从 agent prompt 删除；
   - 保留为内部转换证据但不下发给模型；
   - 还是仅删除实现绑定部分、保留公开接口契约？
5. 对 problem statement 中出现的具体符号、文件路径和 API，应采用什么判定标准来区分“必要公开契约”和“实现泄露”？
6. 新 verifier 是否允许补充原 F2P 未直接选中的测试？如果允许，什么证据等级足以升级为强制测试？
7. suite-level F2P、空 P2P、多服务仓库和 synthetic harness 的覆盖不足，报告中是否统一使用 `spec_gap`/`infrastructure` 等状态？
8. 评测时是否固定同一 agent scaffold？如果需要比较 LockedMiniSwe、LockedCodex 等，应作为单独的 agent 变量，而不是混入 verifier 结果。
9. 最终数据是否同时发布：原始 Harbor task、无 R/I 变体、新 verifier 变体及其 coverage/evidence manifest？

## 8. 当前建议的工作定义

在 Mentor 确认前，可以暂时采用以下定义：

> 从 SWE-bench Pro V2 的 Harbor task 出发，保持仓库、环境、agent scaffold 和任务运行协议不变；把 `requirements`/`interface` 视为可控的 prompt 消融变量；基于 F2P、problem statement 和公开契约证据重建功能性 verifier；用 2×2 实验分别量化去 R/I 和 verifier 转换的影响。DeepSWE 只提供功能测试设计和运行兼容方面的参考，不作为最终任务语义模板。

这个定义可以让“测试是否更功能化”“是否摆脱 R/I 绑定”“是否提高无 R/I 通过率”三个问题分别得到可解释的答案。
