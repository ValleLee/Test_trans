# 2026-10-09 挂起任务的框架问题归纳与本轮修复

日期：2026-10-09
范围：Stage 1 选定的 100 条任务；依据 `python_parked_for_framework_review_20261008.txt`、`python_parked_after_external_review_20261008.txt` 和外审发现记录。

更新时间：2026-10-09（记录到第七轮恢复批次启动）  
文档用途：解释 **转换框架本身** 在 Stage 2 中造成的误报、漏检、错误归因和无效修订；同时明确哪些仍是单条任务的转换错误，不能被泛化成全局规则。

## 先看结论

这轮暴露的不是一个单点 bug，而是转换链路中六个控制面没有完全闭环：

1. **规范来源没有闭环。** Converter 可以读取 P、R、I、F2P、P2P、Gold 和 Repo，但最终断言只能由 P 或既有公开契约授权。早期流程主要依赖 self-review 的文字声明，没有强制逐字证明，因此出现了把 Requirements、Gold 新符号、私有 helper 或执行器调用方式误当成规范的情况。
2. **历史 F2P 没有从源案例闭环到实际断言。** trace 有一行、suite 名称存在或 self-review 写“已覆盖”，都不能证明原测试的每个子案例、分支、集合成员和后置条件已经落到可运行 assertion。Flipt、Vuls、Teleport、Tutanota 等实例重复暴露了这一点。
3. **断言语义容易比 P 更强或更弱。** 精确警告总数、完整集合等值、固定错误文案、只判断 falsy、只判断错误词消失，都会让符合 P 的替代实现被拒绝，或让不符合 P 的实现通过。Base/Gold 通过本身不能发现这种过严/过松。
4. **selector、行为角色和测试源身份曾被不同解析器解释。** `file | suite | case`、`::`、`test/` 与 `tests/` 前缀、顶层 JSON 数组、尾部空格和父 suite/子 test 的身份在不同门禁中不一致，造成误报、无效回修或错误的 P2P/F2P 归类。
5. **回放失败与产品失败没有严格分开。** setup hook 在叶子测试前失败、runner 不可执行、旧 F2P patch 阻断 Base 编译、QA 环境损坏等情况，曾被当成 verifier 行为失败，浪费修订轮次并污染语义候选。
6. **批次状态不是可靠的实验状态机。** 旧队列会继续调度已挂起或已合格 ID，SIGINT 不能停止线程池中的已提交任务，首轮 agent 没有总时限，status 为空时又无法判断 worker 是否启动。这样会把调度问题误记成转换结果问题。

因此，本轮的处理原则是：**先修确定性的框架闭环，再重跑任务；不靠任务名、仓库符号、字段名或某个错误文案增加特例；历史失败记录不追溯改判。** 一个候选只有在框架门禁、Base/Gold 回放、QA、P2P 原序保留、P-only instruction 和框架外独立审计全部通过后，才进入合格名单。

## 转换链路中问题出现在哪里

| 时间/环节 | 应该回答的问题 | 暴露的框架问题 | 典型证据 | 正确处理 |
|---|---|---|---|---|
| Stage 2 输入冻结 | 哪些材料是规范，哪些只是 construction evidence？ | P-only 边界靠模型自述，Requirements/Interface/Gold 可能泄漏到最终 instruction 或断言 | Ansible `_build_doc`、Teleport `SQLServerPinger`、Navidrome 配置入口、最终 instruction 泄漏 | 冻结 P-only source；每条断言提供逐字 P/addendum 引文或既有公开契约；引文做确定性存在检查，再做语义判断 |
| F2P inventory/accounting | 原历史测试的每个可观察行为是否列全？ | suite/bootstrap 被当成一个 case；多分支、多项集合、空值后置条件和失败恢复被漏掉；row 状态静默继承给子义务 | Flipt、Vuls、Teleport `CacheSuite`/`TestInitCACert`、OpenLibrary `pagenum` | 逐文件、逐 suite、逐 case、逐参数化行建立 inventory；每个产品义务显式填写 `base_behavior_status`；selector→source→runner→assertion 四段可追溯 |
| 断言生成 | 新测试是否只检查 P 要求的行为？ | 精确固定无依据的数量、闭集、字段、文案、调用顺序；`undefined`/`null`/`false` 被混为一类；只检查错误消失而不检查正确错误类别 | Ansible warning 总数、archive 全量集合、ProtonMail falsy、Navidrome 历史枚举值 | 逐断言检查 P 授权；对错误、无值、恢复和副作用写正向语义；用满足 P 的替代实现和破坏 P 的反事实分别验证 |
| selector/role contract | 配置中的测试身份是否真的存在，且角色唯一？ | 层级 selector、路径前缀、顶层 JSON array、尾部空格和父/子 test 身份在 parser 间不一致；同一 selector 同时进入 delta 和 regression | NodeBB `file | suite | case`、OpenLibrary 顶层数组、NodeBB 尾空格、Teleport selector 重叠 | 统一规范化与解析；仍保留原始 P2P 字符串和顺序；缺失源文件继续拒绝，只给候选路径提示；重叠角色直接报错 |
| Base/Gold/hard replay | 失败来自产品、测试还是环境？ | setup hook 无叶子结果、runner 权限、旧 patch 阻断 Base、QA 基础设施失败被混入语义失败 | NodeBB setup failure、Teleport `run_script.sh`、Navidrome 旧 F2P patch、QA replay failure | 回放报告区分 `setup_failure_before_leaf_tests`、`no_leaf_test_results_reported`、`replay_infrastructure_failure`；环境失败不调用 Judge、不消耗语义候选、不触发无意义 repair |
| 批次调度与恢复 | 队列、暂停、重试和合格名单是否形成可复现状态机？ | stale ID snapshot、SIGINT 不停新任务、无首轮 timeout、空 status、宽口径合格名单 | 旧 9-worker 批次、暂停后仍派发 queued worker、`append_newly_qualified.py` | 暂停先阻止新任务，再中断进程组并落 manifest；队列始终按 `selected − all certified qualified` 重建；worker 状态写明；旧 attempt 只保留证据，不回填通过 |

## 框架问题与任务问题的边界

### 可以统一修复的框架问题

- 同一种来源真实性问题在多个仓库出现，例如把 Gold-only 方法/类型或 Requirements 中的接口说成 P 要求。
- 同一种证据闭环问题重复出现，例如历史 F2P 有 accounting 行但没有对应 emitted assertion。
- 同一种解析、序列化或状态机问题跨语言复现，例如 selector 解析、JSON 输出形状、尾空格、暂停信号和队列快照。
- 同一种失败归因错误反复消耗修订，例如 setup/权限/环境失败被误当作产品行为失败。

### 必须留在任务级审计的问题

- 某个错误类别是否必须出现、某个返回字段是否属于公开结果、某种恢复行为是否由 P 要求，必须逐条查看 P、原 F2P 和实际断言。
- 某个仓库的 helper、字段、MIME 类型、构造函数、SQL 类型、警告文案或测试路径不能直接写成全局黑名单或白名单。
- 若 P 描述了内部状态，却没有规定公平的公共触发操作，应记录 `access-contract gap/HOLD`；不能为了制造 Base/Gold 差异而下沉到私有入口，也不能把 Gold 中存在的 API 自动升级为 solver contract。
- 具体 fixture 相同、具体路径写错、具体 CVE/枚举成员漏测，首先是转换产物问题；只有同一检查机制在不同任务上重复失效，才上升为框架修复。

## 带时间的修复时间线

| 时间 | 事件 | 框架层结论 |
|---|---|---|
| 2026-10-08 | 外审开始集中报告“框架已接受、独立审计不接受”的包，并按实现绑定、F2P 覆盖、P2P 排除和 instruction 泄漏归类 | 仅有 prompt 提醒不足，需要确定性来源、角色和产物门禁 |
| 2026-10-09 第一轮 | 发现 NodeBB `file | suite | case` 被 `::` 解析器误判为缺失 | selector 解析必须按语法分段并兼容仓库/容器路径；修复后仅消除 artifact 误报，不能替 NodeBB 通过语义审计 |
| 2026-10-09 第二轮 | 引入 `problem_statement_quotes`，并要求引文必须出现在冻结 P 或批准 addendum 中 | “模型说 P 要求”不再等于来源证据；字符串存在检查与语义蕴含判断分开 |
| 2026-10-09 复跑期间 | semantic Judge 精简输入遗漏 `base_behavior_status` 与 `evidence` | 证据序列化必须保留 schema 的语义字段；不能因裁剪丢字段而触发伪缺陷 |
| 2026-10-09 第三轮 | OpenLibrary 顶层 JSON array 被行为角色审计当作缺失；Navidrome 暴露多类 binding 缺陷 | parser 兼容性统一修复；私有入口/构造方式仍用反事实审查，不加仓库特例 |
| 2026-10-09 第四轮 | 批次 SIGINT 后仍继续派发任务，暂停不是真暂停 | 编排器必须有信号、进程组、queued/running 状态和 manifest 的完整暂停协议 |
| 2026-10-09 第五轮 | selector 缺失反馈、显式布尔与缺值、深层字段逐项映射被补强 | 错误反馈可以更具体，但不能用“相近路径”替代真实 selector 或放宽断言 |
| 2026-10-09 第六轮 | NodeBB setup hook 失败被误认为产品 FAIL；合格名单脚本使用过期/宽口径来源 | 回放必须报告叶子测试是否真正运行；qualified 名单必须由 selected-100、独立审计和 final package 共同约束 |
| 2026-10-09 00:38:14 UTC | 新队列启动，10/10 worker 进入 `agent_running` | 旧 batch 关闭、日志保留；恢复队列按选集减去已合格名单重建 |
| 2026-10-09 第七轮 / 01:44:06 UTC | NodeBB P2P 尾空格造成稳定性门禁误报，批次安全暂停并按 selector 规范化恢复 | 比较双方使用同一规范化规则，但原始 P2P 文本和顺序不改 |

## 当前验收口径

对后续每个新 attempt，必须同时满足：

1. `final/instruction.md` 与冻结 P-only source（及明确批准的 addendum）一致，不含 Requirements/New Interfaces。
2. 原始 P2P selector 原文、原序、零排除；P2P 非空时才暂存原始测试 patch。
3. 每个历史 F2P case/子 case 都能沿 `source → obligation → emitted selector → executable assertion` 回放；混合 Base/F2P 的每个义务都有显式 `base_behavior_status`。
4. 每个断言有 P/addendum 逐字引文或既有公开契约，并通过反事实检查；不接受只凭 trace、自检或 Gold 符号存在的证明。
5. Base/Gold 硬回放真正运行叶子测试并形成预期区分；setup、权限和环境失败不能被记作产品语义结果。
6. Positive/Negative QA、framework package、固定独立审计全部通过后，才更新合格名单；任何历史 FAIL、`needs_review`、`interrupted` 或 `rejected_*` 都不自动转为合格。

后文的“第一轮”至“第七轮”保留每次发现的证据、代码修复、测试数量和批次状态；它们是本节总览的可追溯明细，不是新的验收标准。


## 阶段状态

复盘开始时，选集内有 31 条已转换且通过独立审计，69 条尚未合格，两个挂起名单去重后有 23 条。根据用户新设的“挂起达到 5 条先暂停复盘”门槛，已停止原 9-worker 批次和 1-worker 重试批次，保留 batch、attempt、revision、agent 与 pipeline 日志。停止时正在运行的部分 attempt 可能只有中间产物；它们仍属于未合格候选，后续按统一框架重新排队。已审计合格的 31 条不重跑。

## 从挂起记录归并的通用问题

| 类别 | 跨任务证据 | 框架缺口与当前状态 |
|---|---|---|
| 规范授权与实现绑定 | Ansible `_build_doc` / `run_command`、qutebrowser 私有 helper、Navidrome options、OpenLibrary 字段、Teleport/Vuls 新符号 | 共享规则已要求以 P 或既有公开契约授权每条断言、检查 P-conforming 替代实现；Gold/Base 来源扫描也已补充 Go receiver method 和新类型。残余风险是模型自检声明与可执行断言不一致；继续核对真实断言，不增加仓库/符号特例。 |
| 历史 F2P 到实际断言的闭环 | Flipt、Vuls、Teleport 多例漏掉成功分支/子案例；trace/accounting 完整但最终测试缺行为 | converter 与 semantic prompt 已要求枚举 suite 子案例，并逐项核对 selector→source→runner→assertion。artifact gate 可验证映射和 source，但语义仍需复核实际 assertion。重试时不能把 trace 行数当作覆盖证明。 |
| 诊断语义过宽/过窄 | Ansible 告警总次数被固定；另有错误测试接受任意非空异常，或只检查错误词串消失 | 本轮已补共享 converter、focused converter、semantic Judge 和 negative generator：按事件验证所需诊断，不设无依据总数上限；对 P 指定的错误类别拒绝无关但非空错误，同时允许合理改写/本地化；失败输入还要有正确的公开拒绝、无值或恢复后置条件。 |
| P2P / F2P 角色和 selector 映射 | OpenLibrary 混合 Base 行为角色、Go 子测试映射问题；旧审计中曾出现 P2P 排除 | prompt/schema 已要求原始 P2P 原序保留、Base regression 与 delta 分开、每条行为显式给 Base 状态；artifact/final audit 已加强 selector 角色和 instruction 检查。历史包不追溯改判，新 attempt 全量验证。 |
| 回放基础设施与产品失败归因 | qutebrowser pytest INTERNALERROR、NodeBB selector 在镜像缺失、Teleport runner 权限、无 P2P 时旧 F2P patch 阻断 Base | 已有独立 infra failure 分类/重试、run_script 权限门禁、P2P 非空才暂存旧 patch、timeout 与 selector contract 修复。NodeBB 缺失原 selector 仍需保留为环境/映像证据；不能通过删改 P2P 解决。 |
| 规范材料与最终包一致 | 最终 instruction 泄漏 Requirements/Interface；self-review 规范来源自相矛盾/标记被追加内容覆盖 | final instruction 已改为从冻结 P-only source 构造并逐字审计；self-review 末尾标记也有 contract。新的 attempt 仍须检查自检正文与测试代码一致。 |
| 规范行为没有公共触发面 | Teleport 预计算状态要求没有 P 规定的公共激活操作，容易被误标 Base 已满足或下沉内部入口 | prompt 已要求区分不可观察/无触发面与可测试行为；无公平公开区分路径时应记录 access-contract gap/HOLD，而不是造接口。此类候选只有在公共行为和 Base/Gold 差异都可证时才重跑通过。 |
| 批次队列陈旧 | 已合格项曾出现在长生命周期 batch 的初始 ID 快照；挂起名单更新后，运行中的调度器仍可能继续调度旧 ID | 本轮发现 10 个活跃任务中有 3 个已列入挂起名单，且批次启动后名单变更不会自动改变已加载的 ID 列表。已停掉旧批次；恢复时从 `selected_100.txt - qualified IDs` 重新生成去重队列，由 runner 的 accepted-final 检查做第二重跳过。 |

## 本轮修改

- 更新 `prompts/converter.md`、`prompts/converter_focused.md`、`prompts/judges/semantic.md` 与 `prompts/qa/negative_generator.md`，把诊断的语义边界写成统一的正反例规则。
- 不修改 `prompts/independent_audit_standard_cn.md` 的判定门槛；现有 v1 标准已覆盖 P-only、P2P、F2P、公共可观察边界和反事实要求。本轮让转换器与框架内语义门禁更一致地执行既定标准。
- 已暂停的两批不会自动恢复；框架修复完成后，基于选集和当前合格名单重建唯一未合格队列，10 路重新启动，其中包含挂起任务。每个 framework-complete 产物仍需按固定独立审计标准外审，PASS 才进入新增合格名单。

## 后续复核

1. 检查 prompt 更新的差异与语义一致性。
2. 对框架测试运行必要验证；保留当前 31 条已合格任务。
3. 生成新队列前重新核对 selected、qualified、parked、active 四组 ID；已合格 ID 不进入新队列。
4. 恢复 10-worker 转换；每个 framework-complete 产物独立审计。达到新的 5 条挂起时再次暂停并复盘。

## 2026-10-09 复跑中新发现的通用校验器缺陷

首批 10 条复跑中，NodeBB revision 7–9 连续被 `artifact_contract` 报为 emitted test 不存在。复核发现历史 selector 使用 `file.js | suite title case title`；校验器只按 `::` 拆分，把文件路径和层级标题当成一个字符串，因此真实存在的 `tests/test/f2p_sorted_topics.js` 被误判缺失。这个错误令同一 selector 连续触发多个无效回修。

已修复 `src/swepro_trans/validation/revision.py::_selector_is_emitted`：识别多个 ` | ` 分段，要求源文件存在，并以大小写/标点归一后的有序标题词逐段核对层级 suite/case 名；同时兼容仓库 `test/...` 前缀、转换包 `tests/...` 根路径和容器 `/tests/...` 绝对路径。原有 `::` 检查不变。`tests/test_revision_selector_contract.py` 新增层级标题、缺失标题和路径前缀用例。针对性回归为 **4 passed**；真实 NodeBB 与两条 Element revision selector 均识别为 emitted，修复后 NodeBB `revision_contract` 为 **PASS**。

NodeBB 随后进入语义审查，发现排序测试的创建顺序与回复顺序一致，按 TID/创建顺序的错误实现也能通过；再后续发现同一 selector 被错误同时归到 functional delta 和 Base regression，hard replay 还发现 Base/Gold 回放没有达到预期。它们是实际转换缺陷，当前继续修订，不能计入合格。通用解析器修复消除了错误 artifact gate，但还不能把 NodeBB 计为合格。首批其他任务的 pipeline 进程已在旧代码加载后启动；它们结束后需用新校验器复核涉及 ` | ` selector 的 revision，不能让旧误判继续驱动转换。

## 2026-10-09 第二轮：挂起问题分类与可执行修复

### 通用框架问题（值得统一修）

1. **规范依据只有自由文本，没有来源真实性校验。** 多个挂起/外审实例出现 trace 或 self-review 声称 P 规定了某个方法、字段、格式或精确行为，但 P 实际没有该文本。Prompt 已多次要求精确引用，问题不是缺少提醒，而是流程只相信模型自己对引文的描述。
2. **F2P 覆盖证明过度依赖模型叙述。** Trace 行、suite 名或 self-review 说“已检查”不证明实际源 case 的每个产品结果都落到可运行断言上。Flipt、Vuls、Teleport 和 Tutanota 的重复遗漏说明这属于跨语言的证据闭环问题；它不能靠增加某个仓库/测试名称的特例解决。现有 case-by-case prompt、selector→source→runner→assertion 检查继续保留；semantic gate 仍需检查源测试实际断言与映射的对应关系。
3. **selector 语法与仓库路径存在框架通用兼容缺口。** `file | suite | case` 层级标题以及 `test/`、`tests/`、容器 `/tests/` 前缀曾被错误判成缺失测试。已在上一轮修复 parser 并添加跨语言路径/标题测试。
4. **明确的规范、角色、执行器问题已有确定性门禁，复跑时继续使用。** final instruction 对 P-only 的逐字校验、原始 P2P selector 原序保留及零排除、Base/Gold role replay、runner 可执行位及硬 selector replay 已纳入现行检查。它们不需要按具体任务加规则。

### 应留在任务级审计、不能泛化成统一断言

- 对某个错误类别到底是否应触发某条警告、某个结果是否应包含特定记录、某种错误恢复是否被 P 要求，必须逐项看 P、原 F2P 行为和具体断言；不能把单一任务例子硬编码进全局语义规则。
- 某仓库的私有 helper、某个 Gold-only 符号、字段名、MIME 类型、警告次数等，不写成跨任务特例。通用规则只要求每个断言有 P 授权、从公开产品边界观察，并通过满足 P 的替代实现反事实。
- 没有公共触发面或访问契约不足的候选标为 HOLD/access-contract gap，不用无限回修造出接口。

### 本轮可执行修复：逐字规范引文门禁

- 在每个 `p_supported_behavior` / `base_regression_behavior` trace 行新增必填 `problem_statement_quotes: string[]`，保存逐字复制的 P 或当前批准 addendum 连续片段；现有 `problem_statement_support` 继续写解释，不再充当引文。
- 在 `artifact_contract` 加入确定性检查：每条引文必须出现在本 attempt 的 `source/problem_statement.md` 或当前 addendum 中；仅归一化空白，不忽略词语或标点。缺引文、错引或从 Requirements/Interface/Gold 借来的文本会在 Docker replay 前拒绝。
- semantic Judge 收到 quote 后，另行判断引文是否真正蕴含其关联行为；“原文存在”不等于“语义支持”。这保留语义判断，不把 P 的含义降格为字符串匹配。
- 同步 converter、focused converter、semantic Judge 和 deterministic fallback 所需字段。新增测试覆盖有效 P 引文、空白换行、错引、addendum 引文和非规范分类。
- 完整单元测试：**161 passed**；本轮引文/selector针对性回归：**9 passed**；`git diff --check` 通过。

### 运行记录

旧 cohort 使用新门禁前的代码启动，已向该 cohort 的 pipeline/agent 发出 SIGINT 并确认退出；attempt/revision 与日志保留。首批 10 条随后以新框架、10 workers 重新启动。完成状态需查看新的 batch 目录；任何被框架接受的包仍须按固定独立审计标准外审，不能只凭 framework accepted 进入新增合格名单。


批次可观测性也有一个通用小修：`run_stage2_batch.py` 现在会把 worker 标为 `preparing`、`agent_running` 或 `pipeline_running`，并在批次清单中写 `running` 状态；旧版在完成前留下空 status，容易让人误以为worker没有启动。当前运行批次已手动补齐初始状态。

## 2026-10-09 复跑期间修复：semantic Judge证据裁剪遗漏字段

首批复跑中，Navidrome、OpenLibrary等trace的每条 `obligation_accounting` 实际已有 `base_behavior_status`，但 semantic Judge 在 `semantic.py` 构造精简输入时仅保留 id/obligation/scope/disposition/emitted_tests/rationale，遗漏了 `base_behavior_status` 和 `evidence`。Judge因此报告“状态缺失”，触发了本可避免的回修。这是跨任务的证据序列化缺陷，不是任务问题。

已抽取 `_compact_semantic_f2p_rows`，让Judge输入保留完整必需字段及 obligation 自己的 `base_behavior_status`；新增单测直接验证裁剪后值相等。`tests/test_semantic_evidence.py` 与引文/selector针对测试 **30 passed**；完整单测 **162 passed**，`git diff --check` 通过。新启动的 semantic 子进程已加载修复；旧revision仍保留日志和结果，后续按新证据复审。


## 2026-10-09 第三轮：5 条挂起后的复盘与暂停

### 本轮问题归类

| 证据 | 是否通用 | 结论 |
|---|---|---|
| OpenLibrary 回放结果是标准 JSON 顶层数组，行为角色审计只接受 `{"tests": [...]}`，因此把 Base/Gold selectors 全部判成 MISSING | 是，跨语言 parser 输出 schema 兼容缺口 | 已修复 `validation/behavior_roles.py`：保留 JSON 对象/数组形状，统一提取数组记录或对象中的 `tests`；新增顶层数组回归测试，`tests/test_behavior_roles.py` 为 **11 passed**。
| Element 776 的 verified/unverified 输入 fixtures 实际相同、多个历史可观察行为未落到断言，以及内部 Modal/CSS/精确文案/调用顺序绑定 | 混合 | “逐条历史断言→产品行为→P/Base依据→实际断言”是通用审查要求，prompt 已覆盖；本条的具体 fixture 和 UI 输出缺陷属于任务转换错误，不增加 Element 专属规则。按语义反馈重转。
| Vuls 的单条历史 case 有多项 CVE，转换测试未验证全部项 | 风险模式可复用，但具体缺失是任务级 | suite/case inventory 与 assertion mapping 已存在；本轮复跑应逐个核对集合中的每项断言，不增加 CVE 特例。
| Navidrome 的构造函数依赖初始化方式、Ansible/qutebrowser 的私有入口和 Element 的内部 UI 观察 | 共同风险：P 未授权的构造/内部入口被测试固定 | counterfactual/private-entrypoint 规则已经通用覆盖；后续审计要核对可执行断言与引用的 P 原文是否真支持该构造/观察边界。不要把仓库符号加入全局特例。
| Element 494 selector 路径与实际 source 文件不一致 | 需区分 | 只有路径解析规则跨语言都不识别时才修 parser；若 trace selector 本身指向不存在文件，应作为转换产物映射错误由 converter 修复。不能通过全目录扫描弱化 selector 对应关系。

### 批次状态

本轮达到 5 条新挂起后，已停止主批次与 4 个 slotfill worker。所有 attempt/revision/log 保留；未完成项不视为通过。新队列仍从 Stage 1 selected-100 减去已独立审计 PASS 的 31 条生成，重新包含挂起项；runner 在启动时再次跳过已接受且 P2P 原序保留的包。

### 已完成修复与重跑

- 修复行为角色审计无法读取 top-level JSON array 的确定性缺陷；针对性测试 **11 passed**，完整测试在本轮所有改动后为 **166 passed**。
- Navidrome 独立审计发现的“测试通过多个 null 依赖构造路由”此前没有触发静态绑定复核。新增跨语言 advisory 信号 `multiple_null_constructor_dependencies`，并让 focused counterfactual 必须比较有效初始化下保持同一 P 行为的实现与真正破坏公开行为的实现；不要求测试一定拒绝所有 null setup，由 Judge 按 P 和公开契约判断。
- 其余挂起表现出的私有绑定、历史断言覆盖遗漏与错误 fixture 均已有通用 prompt/semantic gate 约束，但实际产物仍失败；不添加任务名、符号或特定测试路径规则。重跑时以这些任务的具体反例检查规则是否生效，并记录新的重复型缺口。
- 本轮暂停批次关闭后，将从 `stage2_remaining_selected100_after_framework_review_20261009.txt` 重建当前唯一未合格队列，10 路重新转换；已独立审计 PASS 的 31 条不重跑。


最终重跑于 2026-10-09 启动：批次 `stage2_remaining_selected100_after_framework_review_20261009_20261008T201806Z`，配置 10 workers、最多 8 次修复、agent timeout 3600 秒；启动时 10/10 个 worker 均已进入 converter。

### 运行中补充的通用修复：同 revision 收集独立 binding 缺陷

Navidrome attempt_005 的 rev_001 同时包含“扩展集/响应格式超出 P”与“多个 nil 依赖固定构造方式”两类缺陷。旧流程在主 semantic Judge FAIL 时跳过 focused counterfactual，只把第一类反馈给 converter；修好后才会有机会看到第二类，造成顺序回修。

现改为：只要主审查返回确定的 PASS 或 FAIL，且不是 Judge transport failure，就运行 focused counterfactual 并合并全部发现；deterministic-only 模式仍跳过。pipeline 每个 revision 通过独立 Python 子进程启动 semantic gate，因此当前运行中的后续 revision 会加载此修复，无需中断现有 attempt。针对性测试 **74 passed**，完整测试 **166 passed**。


## 2026-10-09 第四轮：暂停流程缺陷与继续复跑

### 挂起项的通用性归类

对本轮 5 条挂起任务及既有外审记录复核后，框架层面的共性集中在四处：

1. **规范来源和断言授权没有确定性闭环。** 模型曾把 Requirements、Gold 或仓库实现误说成 P 的要求。现有逐字引文门禁负责验证来源真实性，semantic Judge 再判断语义蕴含；不能只凭 self-review 声明。
2. **历史 F2P 的覆盖容易停留在 trace 层。** suite/case 名称和 accounting 行不证明测试实际断言覆盖了原行为的每个结果或子案例。复跑规则要求逐条核对原测试 source、行为义务和 emitted assertion；多项集合/多分支遗漏仍按实际断言审查，不加 Vuls、Flipt 等任务特例。
3. **验证器输入格式差异造成误报。** `file | suite | case` selector 和顶层 JSON 数组此前都触发过跨任务解析缺口；对应 selector parser、行为角色 parser 与回归测试已经修复。
4. **实现绑定审查需要正反事实而非符号黑名单。** 私有 helper、未初始化依赖构造、内部 UI/CSS/调用顺序等风险统一按“P 是否授权观察边界、满足 P 的替代实现能否通过”处理；不能把某个仓库方法、字段或错误文案硬编码为规则。

Element 的真实 fixture 缺陷、Vuls 多 CVE 子项遗漏、Ansible 的具体调用绑定仍是任务级转换缺陷；若同一证据闭环在多任务继续失效，再修通用检查，不新增仓库特例。

### 本轮新发现并修复：批次暂停不是可用的暂停

实际停止 10-worker 批次时，后台 `SIGINT` 被忽略；即使调度器收到信号，线程池中的已提交工作仍会继续派发，正在运行的转换进程也没有统一登记/中断路径。于是旧任务可被错误记为 `needs_review`，排队任务仍可能开始。这是实验编排层的通用缺陷，不是某条测试转换问题。

已修复 `scripts/run_stage2_batch.py`：捕获 `SIGINT`/`SIGTERM`，停止新任务启动，向登记的 converter/pipeline 进程组发送中断，等待活跃 worker 收尾，将未启动项记为 `cancelled`、运行中项记为 `interrupted`，并把 batch manifest 更新为 `paused`。新增信号路径与 queued-worker 回归测试。针对性测试 **6 passed**；全套测试 **168 passed**；`git diff --check` 通过。

### 暂停批次记录与恢复边界

批次 `stage2_remaining_selected100_after_framework_review_20261009_20261008T201806Z` 已停止；manifest 已记为 `paused`。19 个运行/排队条目标记为 `interrupted` 并保留所有 attempt、revision、pipeline/agent 日志；Flipt `instance_flipt-io__flipt-d966559200183b713cdf3ea5007a7e0ba86a5afb` 的 `attempt_005/rev_003` 已完成且独立审计 PASS，仍计入新增合格名单，不重做。

恢复队列从 `task_list/selected_100.txt` 减去旧、新两份独立审计合格名单后重算；当前共 **68 条未合格候选**，其中包括此前挂起和刚中断的任务。新的 runner 启动仍会二次检查 certified final，避免重做已通过项。并发上限维持 10。

## 2026-10-09 第五轮：5 条挂起后的通用修复与恢复

### 本轮挂起证据与分类

- **Ansible**：测试 patch 了仓库内部 reader，并用按调用位置排列的固定返回值。这个测试会把内部读取次数/顺序误当成行为契约。通用转换与语义审查规则现要求优先控制文件等外部边界；除非有公开注入契约，不固定内部 helper 调用次数或位置，并用不同读取/批处理实现做反事实检查。
- **Element 494、Element 776**：两条产物的 trace selector 与包内测试源映射不完整。框架必须继续拒绝 selector 指向的源文件不存在的产物；本轮只改进错误反馈，提示实际 bundle 中相近的测试源路径，帮助修正目录/文件映射。候选路径只是提示，不能使缺失 selector 自动通过。
- **ProtonMail**：负向断言只检查 falsy，缺少方法返回的 `undefined` 也会通过。通用规则现要求区分明确的 `false` 与缺失、`undefined`、`null`；精确断言仍须受历史可观察行为及 P/既有公开契约支持。
- **Vuls**：历史测试比较多个字段，转换后的断言漏掉了其中一部分。通用规则现要求从原 assertion 逐字段/集合成员核对实际新断言；同时继续允许规范未封闭的额外字段。

这些规则不会把上述任务名、仓库符号或字段写成特例；是否符合仍由实际历史断言、P 和转换测试逐条决定。

### 实施与验证

- 更新 converter、focused converter 和 semantic Judge 的跨语言规则，覆盖内部 fixture seam、显式布尔值与缺值的区别、深层对象断言的逐字段映射。
- `artifact_contract` 对缺失 emitted selector 仍返回失败，并附带最多 6 个 bundle 内测试源候选路径；新增 selector feedback 回归测试。
- 针对 selector、语义证据、行为角色的测试：**38 passed**；完整项目测试：**169 passed**；`git diff --check` 通过。
- 旧暂停批次保持 `paused`，其 attempt/revision/log 未删除。恢复队列由 `selected_100.txt` 减去两个合格名单生成：selected=100，原合格=20，新增合格=14，无交集，当前未合格=66。队列包含挂起和被中断候选；runner 仍会再次检查正式审计、独立审计和原始 P2P 前缀，只跳过已审计合格任务。

恢复批次：`stage2_remaining_selected100_after_parked_framework_repair_20261009_20261008T225515Z`。配置 10 workers；启动检查显示 10/10 worker 已进入 converter，66 条都处于待处理/运行集合。当前尚无本批次最终合格结果；转换包完成后仍须逐条走固定独立审计。
\n\n## 2026-10-09 第六轮：复核 5 条挂起并修复回放归因

### 本轮挂起项与通用性判断

本轮批次在达到 5 条挂起后暂停。对照 attempt 的最终记录，5 条是：

| 任务 | 框架最终发现 | 归类 |
|---|---|---|
| Element 776 | F2P trace 仍有未填写的脚手架字段 | 产物未完成；artifact gate 已正确拒绝 |
| Element 494 | 多项历史 F2P 行为仍对应 `expect(true)` 或空基线，没有可执行行为断言 | 转换覆盖不足；semantic gate 已正确拒绝 |
| NodeBB 0f788b | Base/Gold 回放在叶子测试执行前因 suite setup hook 失败；结果为 0 个测试 | 通用的回放失败归因缺口，见下方修复 |
| ProtonMail | 三条 F2P accounting 仍无 emitted selector，测试保留占位断言 | 转换覆盖不足；semantic gate 已正确拒绝。不能仅凭这一条增加 addendum 专属规则 |
| Navidrome | self-review 留有未完成脚手架且没有最终 PASS 标记 | 产物未完成；artifact gate 已正确拒绝 |

其中 Element、ProtonMail 和 Navidrome 的失败机制不同，现有门禁已识别实际缺陷；证据不足以归纳为新的共同语义规则。它们多次修订仍未解决，反映 converter 没有落实反馈，不应靠放宽门禁或写任务特例解决。NodeBB 则暴露了一个独立、可跨仓库复用的问题：硬回放只报告 FAIL，却没有指出初始化钩子失败导致叶子测试根本没有运行，修复者容易把它误当成产品行为失败。

### 通用框架修复

- `prepare_swebench_pro_v2.py` 从结构化 runner 输出中区分 `setup_failure_before_leaf_tests`、`leaf_test_results_reported`、`no_leaf_test_results_reported` 与 `unavailable`，并把诊断附在 Base/Gold 每侧的回放结果上。
- hard-replay 修复反馈若检测到初始化钩子在叶子测试前失败，会明确说明这不是产品行为证据，要求只排查候选测试自身的初始化问题；原始 P2P 保持不动，且仍必须满足叶子测试运行、Base FAIL / Gold PASS 才能通过。
- 该诊断只改善失败归因和修复反馈，不改变验收标准，也不会把 setup failure 当作转换成功。
- 定向测试：**12 passed**；完整测试：**172 passed**；`git diff --check` 通过。NodeBB 原始回放记录确认两侧 `stats.tests = 0`、`tests = []`，支持上述归因。

### 暂停与恢复队列

- 批次 `stage2_remaining_selected100_after_parked_framework_repair_20261009_20261008T225515Z` 已暂停，无活跃 Stage 2 converter/pipeline worker；manifest 为 `paused`。该批次含 66 条：5 条终止挂起、10 条运行中断、51 条尚未启动即取消，所有日志和 attempt 产物保留。
- 从名单逐行核对：Stage 1 selected=100；原合格 20 条、新增合格 14 条，去重且均属于 selected-100；待处理集合=66 条。现有队列文件与 `selected_100 - qualified_20 - qualified_14` 完全一致，5 条挂起都重新纳入，合格 34 条不会重跑。
- 修复 `scripts/append_newly_qualified.py`：原脚本仍写入宽口径名单、依赖过期的 `external_audit_20261008.json`，且使用与 selected-100 名单不一致的计数标题；现改为校验 Stage 1 selected-100、当前独立审计标准的 P-only/P2P 结果和 final package，然后追加到并列的新名单。针对性测试 **2 passed**，修改后全套测试 **174 passed**。
- 已用 runner `--plan` 验证队列为 66 条、workers=10。新批次 `stage2_remaining_selected100_after_parked_framework_repair_20261009_20261009T003814Z` 已于 2026-10-09 00:38:14 UTC 启动；启动核对时 10/10 个 status 都是 `agent_running`。新 attempt 继承保留历史记录，不把旧的框架失败包计作合格。后续仍按固定独立审计标准判定，P2P 必须原序保留且零排除。


## 2026-10-09 第七轮：稳定性门禁 P2P selector 尾空格误报

### 问题归类

当前批次在运行约一小时后，本轮首个 NodeBB attempt 被标成 `needs_review`。检查 Base/Gold 的结构化回放发现，两条原始 P2P selector（`Topic's .fork should update the user's bookmark `、`Topic's teasers should return empty array `）都实际报告 `PASSED`；但配置 selector 保留尾空格，稳定性门禁读取 runner 输出时对测试名调用 `.strip()`，却用未规范化的配置文本查找，因而两侧都误报 `missing_selectors`。这是跨任务通用的 selector 比较不一致，不是 NodeBB 转换缺陷。

### 框架修复与验证

- `validation/stability.py` 在比较阶段对配置 selector 和结构化输出名称使用相同的去首尾空白规范；错误报告仍保留配置中的原始 selector，方便定位。原始 P2P 配置及其序列没有改动，硬回放通过条件没有放宽。
- `tests/test_stability.py` 增加“配置 selector 带尾空格、runner 输出省略尾空格”的 Base/Gold 回归用例。定向测试 **3 passed**；全套测试 **175 passed**；`git diff --check` 通过。
- 之前的挂起记录还反复暴露了 selector 层级语法、结构化输出 JSON 形状及测试启动失败归因问题；相应 parser / 诊断修复已分别记在第三轮、第五轮和第六轮。任务自身的占位断言、历史行为漏测、私有入口绑定仍由语义门禁拒绝，不通过改宽全局标准处理。

### 批次暂停、名单核对与恢复

- 为防止同一稳定性误报让更多任务无效回修，批次 `stage2_remaining_selected100_after_parked_framework_repair_20261009_20261009T003814Z` 提前安全暂停。停止时 1 条为受误报影响的 `needs_review`、10 条运行中被中断、55 条尚未启动；共 66 个候选均保留在后续队列。NodeBB attempt 会随其他未合格任务重新转换/验证，不把旧 `needs_review` 当成真实任务失败。
- 重建队列逐项核对 `selected_100.txt`=100、原合格名单中的选集任务=20、新合格名单中的选集任务=14、两名单无交集，未合格候选=66；新队列与选集减去 34 条合格任务完全一致。
- 恢复批次 `stage2_remaining_selected100_after_stability_selector_fix_20261009_20261009T014406Z` 使用新队列 `task_list/stage2_remaining_selected100_after_stability_selector_fix_20261009.txt`，worker 上限 10、最多 8 次修订、converter 超时 3600 秒。启动核验时 10 个 worker 均已进入 converter，另 56 条排队；已独立审计合格的 34 条不重跑。


## 当前恢复批次：第 1 条挂起

`instance_NodeBB__NodeBB-05f2236193f407cf8e2072757fbd6bb170bc13f0-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e` 的 `attempt_010/rev_002` 已通过 semantic、hard replay、Base/Gold F2P、原始 P2P 和 stability。Positive QA 的原始候选测试通过，但功能回放因 NodeBB Redis 运行时生成未跟踪 `appendonly.aof`，被通用工作树洁净检查以返回码 92 拒绝；没有语义 verdict。暂记为 recovery batch hold #1，不计入合格名单。该现象提示 QA harness 需要识别并清理测试运行时生成物，不能把它当作 verifier 修改仓库。达到 5 条挂起后统一修复与重跑。
