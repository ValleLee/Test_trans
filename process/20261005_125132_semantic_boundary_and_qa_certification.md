# 异常处理层级绑定与 QA 认证门槛修复

时间：2026-10-05 12:51:32 UTC

## 现象与关键证据

五条 accepted 任务的独立审查发现，Tutanota `attempt_001/final/tests/functional_test.ts` 要求 `DeviceEncryptionFacadeImpl.decrypt` 必须把底层异常转换为指定 `DomainCryptoError`，并要求凭据层抛出指定 `KeyPermanentlyInvalidatedError`。P 描述凭据解密失败的识别与恢复，不指定在哪一层完成转换。两个异常类虽在 Base 中已存在，Base facade `decrypt` 接口没有声明精确异常类型。正向 QA 候选主要改变 try/catch 写法，仍采用 Gold 的两层异常传播设计，因此不能证明 verifier 接受不同架构的正确解。

新建 `attempt_002`，用框架 `seed_revision` 从旧 accepted revision 复制产物到独立 `rev_001`，未改写任务测试。收紧语义 Judge 后的真实 DeepSeek 审查对该 revision 返回 `FAIL`，明确列出两个精确异常类型和 facade 层级的隐藏契约；这与独立审查一致。

另发现通用 QA runner 的确定性 fallback 曾允许仅凭“候选 patch 与 Gold 字节不同、原/新 verifier 都通过、metadata 有解释”就把 Positive 判为 `VALID`。这些事实不能证明实现结构实质不同或满足 P，也不能替代 fresh Solution Judge。Negative 仅凭被 verifier 拒绝和候选自述亦不能证明只违反一个 P 行为。

## Failure classification

- Tutanota 当前 verifier：实例级语义缺陷，需由 Converter REPAIR 改写；不可通过修改 Docker/runner 放宽。
- 审查准则与 fallback：跨任务的框架级缺陷。任何异常处理或 UI 菜单任务都可能有等价的不同处理层级／控件结构；任何 QA 任务都可能遇到 Judge 协议或传输故障。

## 通用修复

- Converter 与主／compact 语义 Judge：要求区分公共错误契约与 Base 中恰好存在的类型；检查“换一层完成同样外部效果”的反事实解；没有 P 或 Base 公共契约依据时拒绝精确层级约束。UI 全局按钮数量断言也需同等审查。
- Positive 生成器与 Judge：优先改变 verifier 最可能绑定的设计轴，并验证不是仅改变代码写法；保留 P 明定公共契约的例外。
- QA runner：确定性 fallback 只记录诊断，不再认证 Positive/Negative；两个配置均显式关闭自动 QA fallback。Judge 不可用时按未认证失败处理，由既有重试/repair 流程处理。

## 验证与剩余工作

`PYTHONPATH=src .venv/bin/pytest -q tests`：32/32 通过，新增两条测试确认回放成功也不能替代正／负语义 Judge。Tutanota 旧 verifier 的新语义审查返回 `FAIL`，说明新准则已在真实任务上发现已知问题。

Tutanota `attempt_002` 的完整自动修复、Base/Gold 重放、正负 QA 与最终独立审计正在进行。修复尚未完成前，`attempt_001/final` 仍是旧 accepted 产物，但不能凭其历史 PASS 宣称已经实现无关。没有启动五条之外的数据转换。

## 13:09 UTC 追加：主 Judge 不一致与专项门槛

同一 `attempt_002/rev_001` 在独立调用中被主语义 Judge 判为 `FAIL`，但正式 pipeline 的另一轮主审查判为 `PASS`；后者把 Base 中存在的异常类误作指定 facade 的公共错误契约。该 PASS 已走到下游门槛，发现矛盾后立即中止，未打包或发布新 final。这是模型审查波动的直接证据，仅优化主提示词不足以可靠阻止该类错误。

通用框架新增 `exact_exception_type` 语法信号：当可执行测试包含 `instanceof ...Error`、`pytest.raises(...Error)` 等精确类型断言时，主审查即使 PASS，也必须经过独立的错误契约反事实审查。专项审查要求指出 P 或**同一 Base 公共边界**的精确类型依据，并尝试构造在其他层处理同一 P 故障的合理解；仅“类在 Base 存在”不构成依据。失败结果覆盖主 PASS，并把专项反例与原因送进结构化 REPAIR 反馈。该规则不含 instance ID、repo 名、具体异常类或文件路径特判。

真实 Tutanota rev_001 再审：主 Judge 又给出 `PASS`，专项 Judge 给出 `FAIL`，反例是用另一种应用错误在 facade／凭据层间传递并实现同样恢复。最终合并 verdict 为 `FAIL`。使用框架 `next_revision`、`seed_revision`、`write_feedback` 生成 rev_002，mini-swe/DeepSeek 正按该反馈修复。完整框架测试 34/34 通过，其中新增精确异常语法触发与回放不可代替 QA 认证测试。

## 13:34 UTC 追加：反复出现的提交时 schema 失败

mini-swe 对 rev_002 生成了面向行为的异常测试草稿，但提交时 `_normalize_revision_outputs` 报错：第二条 F2P 有 2 个 `behavioral_obligations`，只有 1 个 `obligation_accounting`。随后独立 `validate` 也只报这一条。该任务先前的首次转换曾在 109 次模型调用后遇到同类错误，因此不是偶然拼写问题；根因是早期 checkpoint 只检查文件存在、F2P 行数和 placeholder，不检查义务账本 cardinality，最终 sentinel 无本地 schema 阻断。

通用修复：`_converter_finalization_issues` 在模型会话内检查每条 F2P 的义务数与账本数；执行提交 sentinel 时重新读取正式产物，若文件缺失或仍有 finalization 问题，则把具体错误作为工具反馈返回给同一 mini-swe 会话，避免先结束再报错。没有按 instance、repo、测试名或 artifact 特例分支。新增测试模拟有 2 项义务、1 项账本的提交，确认 sentinel 返回可修复反馈；`tests/test_converter_checkpoint.py` 7/7 通过。

使用标准 `next_revision`、`seed_revision`、`write_feedback` 生成 rev_003，正在让 mini-swe 修复这条确定性错误。rev_002 没有进入正式语义与 QA 门槛，也未打包。

## 13:41 UTC 追加：rev_003 专项审查发现隐性层级绑定

rev_003 已由 mini-swe 提交并通过义务账本结构检查。它删去了对 Gold 应用异常类的精确断言，改为拒绝原始库异常外泄；但新增 `thrown === capturedFacadeError` 判断，等于要求凭据层必须创建一个与 facade 错误对象不同的新异常。此要求仍不由 P 推出：凭据层也可以识别故障、处理无效凭据、再将同一个应用错误交给调用者。

完整 pipeline 的主／专项语义审查最终 `FAIL`，专项 Judge 给出上述反事实解，并建议检验下游恢复效果。控制器自动生成 rev_004 和结构化 `repair_feedback.json`，mini-swe 正继续修复。没有用硬规则直接禁止错误对象比较；拒绝依据是该比较在本任务中替代了 P 要求的产品结果。

## 14:12 UTC 追加：运行路径与异常语义的两侧边界

rev_004 去掉应用异常精确类型和错误对象同一性要求，主／专项语义审查均 `PASS`。但 Docker 硬回放中 Base 与 Gold 都因从 `/tmp/harbor-verifier.*/verifier.mjs` 解析不到仓库包 `@tutao/tutanota-crypto` 而失败。这是测试入口所在目录与 Node 包解析规则之间的运行路径问题，不是任务实现结果。自动 REPAIR 进入 rev_005，要求先修复可运行性并保留已接受的行为映射。

rev_005 修正包路径后，主语义 Judge 指出另一侧缺陷：凭据层只拒绝原始库异常、接受任意普通 `Error`，无法证明“识别失效凭据并允许恢复”；相同层次的普通错误也可能让调用方继续把凭据当成有效。rev_006 为保留此行为，重新要求 Base 中已有的 `KeyPermanentlyInvalidatedError`。专项精确异常审查又给出反例：其他应用错误加状态码或标志也可触发清理与重新认证，而 P 未指定这个精确类型，所以判 `FAIL`。控制器现自动进入 rev_007，目标是找到真正可观察的恢复效果。

两次拒绝针对不同方向：任意错误属于功能覆盖不足，精确异常类属于实现绑定。不能把其中一个判定简单地当作另一个的修复；下一版必须同时满足行为覆盖和替代实现兼容。尚未将 attempt_002 打包为 final。`PYTHONPATH=src .venv/bin/python -m pytest -q tests` 本地回归 35/35 通过；真实任务的语义、硬回放及 QA 仍在进行。

## 14:35 UTC 追加：rev_007 语义失败与 rev_008 续修

rev_007 通过真实 `LoginViewModel.deleteCredentials` 和内存凭据存储尝试验证清理与重新登录，避免把 `KeyPermanentlyInvalidatedError` 当成 P 指定的唯一信号。正式语义审查仍判 `FAIL`：这版未直接覆盖 `NativeCredentialsEncryption.decrypt` 不外泄原始库异常的义务，账本却仍声称保留了精确异常断言，测试与账本不一致。因达到本轮自动修订预算，pipeline 以 `rejected_semantic` 结束，没有打包。

另用提交版 verifier 做只读 Docker 预检，Base 的 facade 断言按预期失败，Gold 的 facade 断言通过；两边的凭据恢复测试都因导入登录模块时 `ReferenceError: window is not defined` 失败。该运行错误与语义失败相互独立；仅修复其中之一不能接受产物。

使用框架 `next_revision`、`seed_revision`、`write_feedback` 创建 rev_008，把正式语义反馈和上述 Base/Gold 运行诊断传给 mini-swe/DeepSeek。没有手工改写测试，也没有启动五条之外的数据。rev_008 仍在转换中。

## 14:50 UTC 追加：rev_008 运行预检

mini-swe/DeepSeek 在 rev_008 同时增加了凭据解密入口的非原始库异常断言与登录恢复的可观察检查；runner 保留动态导入的独立 bundle chunk，使浏览器全局对象先于登录模块求值。对当前修订执行只读 Docker 预检：Base 的两个 converted selector 均失败，分别因原始库异常从 facade 与凭据解密入口外泄；Gold 两个 selector 均通过。此前 Base/Gold 都因 `window is not defined` 失败的运行问题已消失。该预检仅证明当前测试可运行并区分 Base/Gold，语义 Judge、正式硬回放、稳定性与正负 QA 尚未完成，rev_008 mini-swe 会话仍在运行。

## 15:04 UTC 追加：rev_008 专项语义反例

rev_008 的只读 Docker 预检是 Base 两项失败、Gold 两项通过，但正式专项语义 Judge 判 `FAIL` 并触发自动 rev_009：另一个满足用户恢复结果的实现可以在凭据层捕获库异常、清理失效凭据并回到登录流程，而不要求 `DeviceEncryptionFacadeImpl.decrypt` 本身改变异常类型。rev_008 对两个中间入口都要求 `Error` 且不是库 `CryptoError`，可能强制了异常转换所在层。Gold 回放成功不能反驳这个替代实现反例。

这里也出现了审查边界需要继续调查的现象：前一轮主 Judge 曾要求直接覆盖凭据解密入口不外泄原始库异常，而此轮专项 Judge 认为把该断言固定在中间入口会绑定实现。不能通过简单放宽所有检查或简单固定原始断言解决；应以每条 F2P 的行为意图、P 的用户可观察结果和有据可查的 Base 公共契约决定映射。当前先由 mini-swe rev_009 改写实例级 verifier；是否需要通用 Judge 规则修改，待比较后续审查与正向替代解 QA 证据再定。

## 15:22 UTC 追加：主审查与专项审查规则冲突的通用修正

rev_009 把两个历史异常断言映射到相同的登录恢复场景，Gold 的只读 Docker 预检通过，但正式主语义 Judge 判 `FAIL`：它要求直接保留 facade 与凭据层的历史异常类／边界，并指出两条 selector 实际执行同一个函数。这与 rev_008 专项 Judge 的反事实相冲突：一个正确解可以在不同层识别库异常，满足 P 的恢复结果，却被精确中间层断言拒绝。后者的反例是真实的设计自由度；前者对重复 selector 的批评也成立。

根因不是这条数据的路径或 Docker 环境，而是共享语义指令内部有互相拉扯的绝对规则：主 Judge 提示写“exception behavior is not an empty product result”，精简重试提示也写“an exception is not an empty product result”；converter 与专项错误审查则要求 P 未固定类型和层级时检验下游结果。该冲突可影响任何“历史测试断言内部异常、P 要求用户可观察恢复”的任务，因此属于跨任务的审查编排缺陷。不能把单纯吞错当成恢复，也不能把旧异常类本身升格为 P 契约。

通用修复：主 Judge 和精简重试提示现在区分无关的空结果／吞错与“触发同一失败后、证明 P 要求的可观察恢复”；明确只有 P 或同一 Base 公开边界文档固定类型和层级时才要求精确异常。两条历史 F2P 剥离机制后若只剩同一产品行为，应通过 `merge` 指向一个有意义的测试，不能复制相同测试体凑两个 selector；独立边界条件仍须单独断言。converter 提示同步这一合并规则。没有加入 instance ID、repo、具体异常类或路径特判。

验证：`PYTHONPATH=src .venv/bin/python -m pytest -q tests` 为 35/35 通过。真实任务的后续语义审查和替代实现 QA 才能验证这项提示修正的行为效果；在这些结果出来前不宣称框架稳定或第五条完成。

## 15:26 UTC 追加：rev_010 错误方向与 REPAIR 反馈优先级

rev_010 是控制器依据 rev_009 主 Judge 反馈自动启动的 REPAIR。暂存 verifier 再次直接要求 facade 抛应用 `CryptoError`、凭据解密抛 `KeyPermanentlyInvalidatedError`，与 R 和 Gold 一致，却没有证明 P 或 `NativeCredentialsEncryption.decrypt` 的 Base 公开契约固定这些精确类型。这个结果说明即使初始 Converter 提示强调 P 优先，结构化 Judge 反馈中出现具体历史异常名时，REPAIR agent 仍可能把反馈误当新增规范。尚未据此认定 rev_010 可接受。

补充通用 Converter 提示：REPAIR 模式下 Judge 反馈是待验证的缺陷假设，不是 solver specification；若它要求 P 和同一 Base 公开边界没有规定的精确异常类、传播层、构造器、模块或 Gold 机制，agent 应保留 P 支持的行为并在自审中给出反事实理由。修订不包含任务 ID、仓库、具体错误类或路径特判。下一轮语义审查继续验证提示规则是否真正生效。

## 15:35 UTC 追加：提交前 schema 检查补全

rev_010 的 mini-swe 会话提交了缺少 `preservation_evidence` 的两条 F2P 行；正式 artifact contract 因必填字段缺失拒绝，控制器又消耗一轮自动 REPAIR 进入 rev_011。此前同一提交路径已因义务账本 cardinality 漏检浪费修订，本次说明通用提交前检查与正式 schema 没有共享同一组字段规则。这不是 Tutanota 特性：任何转换任务都可能在长 agent 会话尾部漏填必填证据字段。

通用修复：mini-swe 提交 sentinel 的 `_converter_finalization_issues` 复用 `conversion_schema.REQUIRED_F2P_FIELDS`、`classification_errors`、`trace_disposition_errors`，先返回每条 F2P 的义务数量和缺失字段，再返回其他 schema 错误。错误作为同一 agent 会话的工具反馈，避免把可当场修复的格式问题推迟到下一 revision。新增缺失 `preservation_evidence` 回归测试；`PYTHONPATH=src .venv/bin/python -m pytest -q tests` 为 36/36 通过。正在运行的 rev_011 agent 已在代码修改前加载旧模块，本轮提交不以新 checkpoint 生效为前提；后续新会话会使用新规则。

## 15:41 UTC 追加：断言助手绕过专项错误审查

rev_011 的 artifact、主语义、Base/Gold、行为角色与稳定性门槛均已通过，正向 QA 正在运行。但独立读取可执行测试发现，两个 selector 通过 `expectRejects(ErrorType, …)` 调用，把 Gold 的应用 `CryptoError` 和 `KeyPermanentlyInvalidatedError` 作为必需精确异常类。主 Judge 把 R/Gold 中的类型误认作 P 支持；此前新增的专项审查没有运行，因为 `exact_exception_type` 静态信号只匹配直接 `instanceof ConcreteError`、`pytest.raises(ConcreteError)` 等写法，而测试通过“错误类参数 + 断言助手内部 `instanceof ErrorType`”间接表达同一约束。

这是跨任务的信号漏检：任何语言或任务都可以把精确错误断言包装进辅助函数。通用检测器增加“把 `*Error` 类作为函数第一个参数传入”的保守触发规则；它只启动专项 Judge，不直接判失败。新增回归测试覆盖 `expectRejects(KeyPermanentlyInvalidatedError, …)`；完整本地框架测试 37/37 通过。用 rev_011 的真实 `functional_test.ts` 只读调用检测器，已产生 `exact_exception_type` 信号。当前运行中的 rev_011 语义进程在修改前已结束；其 PASS 不能证明专项规则通过。保留正在运行的正向 QA 证据，之后需用新检测器重新审查该 revision，不能直接据旧 PASS 发布。

## 15:49 UTC 追加：正向 QA 重试反馈链

rev_011 的 Positive QA 第一个候选通过了原始和功能 verifier，但 fresh Judge 判 `INVALID`：它只把 Gold 的 `instanceof/ofClass` 换成按错误名称识别，两个中间层仍分别抛完全相同的异常类，不能检验 verifier 对不同异常处理架构的包容性。此判定正确，说明单纯配对回放不能认证“实质不同”的正确解。

阅读通用 QA runner 发现，候选循环虽允许多次尝试，`run_candidate_agent` 每次创建新会话时只读取相同 P、Gold 和 verifier，没有把上一候选的 Judge 理由或回放结果传入下一会话。因此重复浅层策略的风险适用于所有任务，不是 Tutanota 特例。通用修复：后续候选会话在只读 `reference/previous_attempt_feedback.json` 中获得此前设计轴、简短说明、Judge verdict/reasons 及原始/功能回放通过状态；任务提示要求先阅读反馈并改变被拒绝的设计轴。反馈不含候选完整补丁，不升格为 solver 规范。新增单测验证此数据契约，完整本地测试 38/38 通过。当前运行中的 QA runner 已在代码修改前加载旧函数，第二候选不会自动收到新反馈；下一次启动的 QA 会话才会使用此修复。

## 16:02 UTC 追加：Positive Judge 的虚假 VALID 与独立复审受阻

rev_011 的 Positive QA 第二候选被 Judge 判 `INVALID`：它仅扩大异常捕获范围，仍在相同两个中间层映射为同样的 Gold 异常类型。第三候选的 metadata 明确写着“两个传播层级和精确异常类保持不变”，变化只是通过 `objToError` 重建应用错误、以及把 `ofClass` 换成整个方法的 try/catch。其配对重放通过，Positive Judge 却给 `VALID`，称两种错误重建／控制流写法是实质不同。这是共享 QA 判定缺陷的真实反例：当前提示虽要求在被测行为路径上判断设计差异，Judge 仍把语法和错误构造差异当成能揭露 verifier 过绑定的替代实现；又把 verifier 自身要求的精确异常类误称为 P 的公共拒绝契约。P 原文只描述库异常未被应用识别、存储凭据仍被认为有效、用户无法再次认证，并没有指定这两个异常类。第三候选的 VALID 不构成独立性认证。正向 QA 进程及随后门槛仍在运行，不能依据旧语义 PASS 或这一 QA verdict 发布 rev_011。

本地静态检测已验证当前通用 `_binding_signals` 能在 rev_011 的 `functional_test.ts` 中识别 `expectRejects(KeyPermanentlyInvalidatedError, …)`，触发 `exact_exception_type` 信号。尝试将新增专项语义复审写入独立 `/tmp` 文件时，自动审批拒绝该额外 endpoint 调用，理由是虽有此前的真实转换及 endpoint 授权，但未证明此具体任务 payload 到具体目标地址的授权范围；已停止该新调用，没有通过其他命令绕过。只读检查确认任务来自 `ScaleAI/SWE-bench_Pro` test 数据集和官方镜像，配置模型为 `deepseek-v4-pro-Code-PT-SWE-Pro-o-66`、内部 endpoint 为 `10.101.56.66`；没有读取或输出 API 密钥。已向用户提出明确授权问题。其间继续本地审计，并只观察已启动的进程；未把受阻的额外复审伪称完成。

## 16:08 UTC 追加：自动完成与独立审计结论分歧

Tutanota `attempt_002` 随后完成负向 QA、acceptance 和 packaging，控制器曾记录 `status=complete`、正向候选 3 `VALID`、负向候选 1 `RELEVANT_NON_EQUIVALENT`。但这并未解决上文的精确异常层级绑定：正向候选 3 的 metadata 自认保留 Gold 两个异常类和传播层级，Judge 把 `objToError` 与 catch 范围差异误作能检验该绑定轴的替代设计；rev_011 的语义结果又是在新静态信号规则生效前产生，没有专项错误契约审查。Base/Gold 和负向回放通过也不能证明能接受不同正确实现。

因此在 `attempt_002/review/independent_audit.json` 写入独立 `FAIL` 和具体证据，并把该 attempt 的索引状态从自动 `accepted` 标为 `audit_rejected`、清空可用 `final_task`。保留自动 gate 报告与已打包目录作为历史证据，不把该 final 作为认证完成的转换。第五条仍需新的 mini-swe 修订、语义复审和真正改变设计轴的正向 QA；额外 endpoint 复审仍待自动审批所要求的具体授权。该处置属于实例级结果修复，通用问题是静态信号漏检和 Positive Judge 误认证，不能靠降低验收条件解决。

## 16:15 UTC 追加：Positive Judge 缺少 Gold 对比证据的通用修复

**现象**：同一个第三正向候选在 metadata 中明说两个精确异常类和传播层级都与 Gold 一样，只有 `objToError` 与 catch 范围不同；Positive Judge 却给 `VALID`。这不是 Tutanota 特殊路径或 Docker 问题。

**根因与范围**：正向 mini-swe 生成会话挂载了真实 `reference/gold.patch`，但 `qa.runner._evaluate_candidate` 发给独立 Judge 的证据只有 P、候选补丁、生成者自己的 metadata、重放与转换账本，没有 Gold 补丁。Judge 被要求比较 Gold/候选，却只能信候选的自述，且容易把 verifier 自身对精确异常类的要求误当成 P 的规范。所有任务的 Positive QA 都有同样证据缺口。

**通用修复**：`src/swepro_trans/qa/runner.py` 现在把原始 Harbor `solution/gold_patch.diff` 和当前 verifier 的通用静态绑定信号一同送到 Positive/Negative Judge；没有任务 ID、repo 或异常名特判。`prompts/judges/positive.md` 明确要求用真实 Gold diff 比较同一被测行为路径，区分语法变化与设计轴变化，并要求精确异常类／传播层级的规范主张引用 P 原文或同一 Base 公共边界文档，不能从 R/I/Gold/verifier 循环推断。一个 P 正确但被当前 verifier 拒绝的替代实现应成为假阴性反馈，而非被逼回 Gold 设计。

**验证与残余风险**：新增 `tests/test_qa_judge_evidence.py`，证实 Judge 证据包含真实 Gold 补丁以及辅助函数封装的精确异常绑定信号；相关测试 6/6，通过全套本地测试 39/39。由于额外 endpoint 调用被自动审批拒绝，新提示的真实 LLM 效果尚未在新一轮 QA 中验证；不能据本地单测宣称第五条已完成或框架稳定。

## 16:30 UTC 追加：前四条独立复核发现两种新的 verifier 语义缺陷

**qutebrowser `attempt_020`：实例级 verifier 假阳性。** P 标题要求 `FontFamilies` 类型和一致的字体解析，但最终 `test.sh` 中的 `_parse_font_families(text, expected)` 对每条输入遍历所有公开方法，先按该用例的 `expected` 过滤输出，再选择一个方法作为“解析入口”。这会让不同的不完整方法分别通过不同测试，却没有一个稳定、对用户可用的解析接口。本地从最终脚本直接抽取实际函数执行反例：`parse_first` 只正确处理 `foo, bar`、`parse_second` 只正确处理 `foo,   spaces `；两个测试都通过，而没有一个解析器同时处理二者。必须由一个先选定的公开入口接受整组输入，或经真实产品配置路径验证；不得用预期答案反向选 API。已将自动 `accepted` 的 `attempt_020` 记入 `review/independent_audit.json` 并标为 `audit_rejected`，保留原 final 作历史证据。

**Element `attempt_006`：实例级 verifier 假阴性。** 两份最终 JS 测试都通过 `screen.getAllByRole('button')` 在整个渲染页面搜集 `aria-haspopup` 按钮，然后断言 `toHaveLength(1)`。P 只要求当前会话区域提供可操作菜单及两项会话操作；它没有禁止页面其他位置存在第二个菜单。若正确实现同时显示一个无关菜单，当前 helper 在业务断言前即失败。应寻找属于当前会话的可观察操作，而非要求全页面菜单数唯一。已写入 `review/independent_audit.json` 并将该版本标为 `audit_rejected`，保留自动 gate 报告。

**OpenLibrary 两条的只读补充证据**：作者别名测试使用的 `alternate_names` 是 Base 作者实体已有字段，`openlibrary/plugins/openlibrary/types/author.type`、作者搜索、模板和入库代码均使用它；查询测试观察的 `workQuery` 是 Base `WorkSearchScheme.q_to_solr_params` 已生成的参数。两条均通过记录的 F2P 账本、Base/Gold、P2P、正负 QA 和最终审计，暂未发现同类隐藏新接口。该检查只覆盖已读测试和公开边界，不把自动 PASS 夸大为所有可能实现的形式化证明。

**框架范围及修复**：两个缺陷反映了跨任务可复现的审查漏检：用 expected 选择测试入口、全局 UI 数量误充目标控件行为。通用 `_binding_signals` 增加 `oracle_guided_selection` 与 `global_ui_cardinality` 风险信号，供主语义 Judge 和 Positive Judge 看见；主语义提示及精简协议重试提示要求一个稳定入口贯穿用例、区分目标菜单与全局菜单数。没有加入 instance ID、仓库或具体组件特判。新增两项回归测试，完整本地框架测试 41/41 通过。真实 mini-swe 修订与 endpoint 语义 Judge 尚未重跑，受自动审批阻断的附加模型调用仍待明确授权；不能视上述两条为完成转换。

## 16:35 UTC 追加：审阅状态与独立审计一致性

独立审计把 qutebrowser、Element、Tutanota 的最新 attempt 标为 `audit_rejected` 后，发现 `final_audit.audit_task` 仍只读取历史 acceptance/gate 文件和 final 存在性，会返回 `PASS`；`reporting.human_review` 也会在 `summary.json` 继续显示 `complete`。这是共享报告编排缺陷：任何后续独立审计驳回都可能被旧自动 PASS 掩盖，适用于所有任务。

通用修复：最终审计现在要求最新 attempt 的状态仍为 `accepted`，并检查 `review/independent_audit.json` 不为 `FAIL`；人类审阅摘要优先呈现 `audit_rejected`、单列独立审计状态及 `certified_final`，同时保留 `final_packaged` 表示历史物理产物。新增回归测试验证“存在最终目录也不能覆盖独立审计驳回”。重建了上述三条审阅摘要，均为 `audit_rejected / independent FAIL / certified_final false`；只读汇总审计对这三条返回 FAIL，对两条 OpenLibrary 返回 PASS。完整框架测试 42/42 通过。旧自动 gate 文件与 final 未删除，供追溯与后续 mini-swe REPAIR 使用。

## 16:40 UTC 追加：语义结果与候选证据指纹绑定

Tutanota rev_011 的自动验收发生在语义 Judge 结束后、但通用静态信号检测器已经修复之后。旧 Judge 报告没有识别辅助函数传入的精确异常类，新检测器在同一 verifier 上会触发专项审查；旧 PASS 被原 acceptance 直接复用，造成“运行中的语义规则已变、验收仍沿用旧结论”的跨任务时序漏洞。

通用修复：将绑定信号逻辑独立为 `validation/binding_signals.py`，供语义审查和 QA Judge 共用；语义报告现在记录基于完整 `tests/` 文件哈希与当前绑定信号的 `verifier_evidence_fingerprint`。`validation/acceptance.py` 验收时重新计算并拒绝缺失或不匹配的指纹；`validation/final_audit.py` 对新报告复核指纹，对老报告仅标记 `legacy_unversioned` 警告。这样既能拒绝运行过程中更改 verifier 或风险检测规则后的陈旧 PASS，又不伪造老任务已经通过新规则。新增回归测试：变动测试源码后原语义审查指纹失效；完整本地测试 43/43 通过。

用户现已明确授权 Tutanota 的公开任务材料发送到 `.env` 配置的内部 DeepSeek endpoint 做独立复审；正在只写 `/tmp` 的 rev_011 语义扫描，不覆盖历史门槛记录。此授权目前明确指向 Tutanota 的独立复审，不据此假定其他任务的新 endpoint 调用已获同等具体许可。

## 16:45 UTC 追加：经授权的 Tutanota 独立语义复审

用户明确授权将该公开任务材料（不含密钥）发送到 `.env` 配置的内部 endpoint 复审。独立 DeepSeek Judge 对 attempt_002 rev_011 返回 `FAIL`：两条 F2P 均要求 P 未规定的精确异常类与传播层级。结果保存于 `attempts/attempt_002/review/independent_semantic_rescan_rev011.json`，原流水线的历史门槛记录不覆盖。此次结果证实独立审计驳回有模型复审证据，旧 final 仍不可作为合格产物。下一步通过新的 mini-swe attempt 修订并重跑全部门槛。

## 17:15 UTC 追加：Tutanota REPAIR 无测试产物与通用会话控制修复

attempt_003 rev_001 使用 mini-swe/DeepSeek 进行了 180 次模型调用，轨迹显示已发现登录恢复链路，但到步数上限时 `tests/` 与旧 rev_011 字节相同。agent 只追加自审说明并修改账本，原 checkpoint 因“任何形式产物变化”被解除；CLI 误记 `submitted_artifacts_after_limit`。该现象与任务 ID 无关：所有有完整种子文件的语义修复都可能靠改说明解除探索限制。

通用修复：当结构化 semantic feedback 有 `binding_risks`/`hidden_contracts`/`under_conversion`，额外记录 verifier 测试目录指纹；写入检查要求测试目录变化，不能由自审文字解除；若会话仍未改变测试则标记 `repair_no_verifier_change` 并使 agent 命令失败。单测验证自审修改仍被拦住、测试改写后可继续。旧 rev_001 状态记为 `converter_no_progress`，保留完整轨迹；新 rev_002 从原 verifier 独立复制并接收该反馈。

## 17:48 UTC 追加：Judge 输出预算优先级

Tutanota attempt_003 rev_002 的语义 Judge 首次请求连续给分析文本却未给闭合 JSON，控制器正确归类为 `judge_transport` 而非语义 FAIL，并对同一 revision 重试。调查 `_client`：共享 `.env` 加载器总是写入 `max_tokens=6144`；Judge 取值顺序先用该通用值，导致 YAML 的 `judge_max_tokens=16384` 永远不生效。修复为优先读取角色专属 `judge_max_tokens`，其次 YAML Judge 预算，再退回通用预算。通用单测验证 16384 生效且角色覆盖仍可用。该缺陷适用于所有 Judge 角色，不是 Tutanota 特判。当前已启动的旧进程仍运行旧代码；待其结束用新进程复审。

## 17:55 UTC 追加：Tutanota rev_002 语义复审

修复 Judge 输出预算后，rev_002 独立语义 Judge 返回合规 JSON `FAIL`，输出 token 9896（旧 6144 预算无法容纳）。结论：测试虽然删除精确异常类型断言并检查 `LoginViewModel` 恢复状态，夹具仍直接 `new NativeCredentialsEncryption`、`new DeviceEncryptionFacadeImpl` 并调用内部 decrypt；一个在其他层实现相同恢复的正确解可能无法运行此夹具。这是 verifier setup 的隐性实现绑定。控制器自动生成 rev_003 并将结构化失败原因交给 mini-swe；尚未进入 Base/Gold 回放。

## 18:02 UTC 追加：Tutanota rev_003 预回放诊断

rev_003 删除了内部加密 helper 构造，但改为在 `ICredentialsProvider` 假对象直接抛出 `KeyPermanentlyInvalidatedError`。agent 自己将任务标成 `non_discriminative`；控制器按此先跑 Base/Gold。两边均 `ReferenceError: window is not defined`，属于网页模块在 Node 中加载的夹具错误，尚不能支持功能结论。控制器自动反馈并启动 rev_004。后续需检查修复夹具后 Base 是否也通过：若是，说明预注入下游错误绕过了原 F2P 的解密失败识别，不应发布 final。

## 18:17 UTC 追加：Tutanota rev_004 环境回放

rev_004 为 Node 回放补浏览器全局并以轻量 stub 代替 `mithril/stream`，但 Base 与 Gold 都报 `TypeError: Cannot read properties of undefined (reading getRandomValues)`，尚未测到产品行为。控制器自动反馈并启动 rev_005。更深的设计风险仍在：将 `KeyPermanentlyInvalidatedError` 直接从假 provider 注入，会绕过 Base 实际未能把原始解密失败翻译成失效凭据的路径；即使环境修通，若 Base 同样通过，此测试只能是旧回归，不能发布为新的 F2P 增量。

## 18:27 UTC 追加：失败触发因果保真规则

现象：Tutanota attempt_003 rev_003–rev_005 把原始 PR 中“密钥链材料不匹配导致原始解密失败，应用未识别并留下失效凭据”的路径，替换成 fake `ICredentialsProvider.getCredentialsByUserId` 直接抛出已分类的 `KeyPermanentlyInvalidatedError`。这样一来，无论测试最后观察到什么登录状态，夹具已经完成了待实现的错误识别；即使 Base 通过，也不能据此认定原始 F2P 没有产品差异。rev_003/rev_004 的 Docker Base/Gold 尚因浏览器全局环境错误而双双失败；rev_005 正在修复运行环境，功能判定仍待回放。

分类：这是 converter 和 semantic Judge 共用的跨任务语义风险，不是 Tutanota 名称或路径特性。任何“原始触发 → 应用识别/翻译 → 可观察恢复”的任务，都可能在模拟边界预先注入已翻译结果而绕过待测环节。通用规则已补入 `prompts/converter_focused.md` 与 `prompts/judges/semantic.md`：保留 P 描述的上游输入或失败事件，允许 mock 无关基础设施，但不得由 mock 代做被测识别/决策；Judge 要核对触发到公开结果的可执行因果路径，并允许正确实现在不同层完成识别。此改动仅收紧语义审查，不增加特定异常类、层级或实现路径要求；新修订仍需经 Base/Gold 回放与正负 QA 证明。当前运行中的 agent 可能已加载旧 converter 提示，不能把 rev_005 当作该新规则的验证结果。

## 18:41 UTC 追加：非区分性任务门槛顺序与独立复审

attempt_003 最终于 rev_006 结束，Base/Gold 都在网页模块加载时因 `KeyManager` 读取未定义的 `addEventListener` 失败；流水线退出 `rejected_hard`，没有 final。rev_003–rev_006 都自报 `non_discriminative`，旧控制器为这种自报状态先运行 Docker，故四轮都只修夹具环境，语义 Judge 一次也未运行。对 rev_006 单独调用已获授权的 DeepSeek 语义审查，返回 `FAIL`：fake provider 直接抛 `KeyPermanentlyInvalidatedError`，绕过 P 中的原始解密失败识别；不能将两条历史 F2P 合并标为 Base 已满足的 P2P。结果另存于 `attempt_003/review/independent_semantic_rev006.json`，旧 attempt 仍按真实流水线状态保留 `rejected_hard`。

根因是共享控制器以未经审查的 `task_disposition` 改变门槛顺序，和 `docs/optimize_rule.md` 所规定“Semantic Judge → Hard Validator → 回放”的顺序不符。所有任务都能自报 non_discriminative，所以这是跨任务编排错误。已移除预先 Docker 的特殊分支，让所有 revision 在 artifact 检查后先做语义审查，再做 Docker 回放和行为角色核对；同步调整 Judge 提示，要求先审源码与仓库证据、再由后续回放证实 Base/Gold 共同边界。新增回归测试模拟非区分性 revision 的语义 FAIL，断言控制器未启动 `--execute`；完整框架测试 46/46 通过。潜在限制是语义 Judge 在回放前只能据代码判断共用边界，因此后续 Docker 和角色审计仍为必经门槛，不能用语义 PASS 代替。

已新建 Tutanota attempt_004，rev_001 从上一版候选复制；将独立语义 FAIL 的结构化发现写入 `repair_feedback.json`，准备由 mini-swe 依据新规则重写真实失败触发路径。尚无新的合格 final。

## 19:06 UTC 追加：Tutanota attempt_004 首轮语义门槛

mini-swe rev_001 把两条历史 F2P 合并到真实不可解密 token → 生产凭据加密链路 → 登录恢复状态的测试，账本重新标为 `convertible` / `changed_or_missing`。但独立语义 Judge 返回 `FAIL`：测试将 mithril stream 属性 `viewModel.displayMode` 直接与字符串比较，未调用 stream，首个断言就会失败，实际没有触发待测解密路径。Judge 还指出精确 `credentials` / `form` 内部状态名可能形成不必要的实现绑定；应优先验证公开可观察的认证恢复结果。新框架先语义后 Docker，故此缺陷在运行容器前被识别，控制器已将结构化反馈交给 rev_002 mini-swe 修复。该属性访问属于当前测试的实例级缺陷，不据此修改共享框架。

## 19:14 UTC 追加：Tutanota rev_002 功能回放里程碑

rev_002 根据首版 Judge 反馈修复 mithril stream 读取，改为以既有登录控制行为取得期望模式，仍保留真实不可解密 token 作为触发。独立语义 Judge 返回 `PASS`，理由是两条历史 F2P 的产品义务均由同一个原始解密失败 → 凭据清除 / 登录恢复测试覆盖，精确中间异常类型仅作实现细节排除。Docker 硬回放：Base 退出 1，具体断言为“预期失效凭据被清除，实际仍有 1 条”；Gold 退出 0，必需 selector 全部通过。行为角色审计 `PASS`，重复稳定性回放 `pass`。这些证据说明当前候选已具备真实 Base/Gold 功能区分，但还不能发布：正向 QA 已启动，负向 QA、最终验收与独立审计尚待完成。

## 19:31 UTC 追加：Tutanota 正向 QA 假阳性与生产边界

**现象**：attempt_004 rev_002 的转换测试满足语义审查、Base FAIL、Gold PASS，自动正向 QA 候选也得到“原测试 FAIL／功能 verifier PASS”，流水线因此自动 accepted。但独立审计发现该候选只在同进程夹具里成立：它在主线程 `LoginViewModel` 捕获加密库原始 `CryptoError`，而正式应用在 worker 中运行 `DeviceEncryptionFacadeImpl`，错误经 `MessageDispatcher` 序列化后在主线程按 `name` 重建。原始库错误的 `name` 实测为 `Error`，跨桥后变成普通 `Error`，主线程的 `instanceof` 无法命中。因此这个正向候选不能证明 verifier 接受真实可用的不同实现。

**根因与通用性**：独立 Judge 原来接受“候选补丁与 Gold 不同＋隔离 verifier 通过”作为主要证据，却没有强制追踪产品调用链上的 worker／RPC／进程／序列化边界。任何跨边界传递的异常、对象身份或状态都可能出现相同假阳性，不能按当前任务名特判。

**修改与复核**：`prompts/judges/positive.md` 要求核查正式产品拓扑及对象/异常跨边界保真；`prompts/qa/positive_generator.md` 要求在 metadata 中列出生产路径证据。对同一个候选、同一份证据使用更新后的 Judge prompt 独立复审，结果从 `VALID` 改为 `INVALID`，理由明确指出 worker 桥。结果保存于 `attempt_004/review/independent_positive_rejudge_001.json`；`independent_audit.json` 标记 FAIL，控制状态改为 `audit_rejected`。原 final 保留作历史产物，不计入完成数。后续须生成真正可在生产拓扑中工作的不同解并重新经过正负 QA、回放和最终审计。

## 19:55 UTC 追加：Tutanota attempt_005 合格与耗时分析

以 `attempt_004` rev_002 的相同 verifier 为起点建立新 attempt，使用修订后的正向 QA 提示完整重跑。语义 Judge `PASS`；Docker Base `FAIL`、Gold `PASS`，稳定性与角色审计通过。正向 mini-swe 用 47 次模型交互生成生产拓扑可行的不同解：在 worker 中将原始加密库 `CryptoError` 直接转换为 `KeyPermanentlyInvalidatedError`，并在 `Utils.ErrorNameToType` 登记该类、设置可序列化的 `name`。原 historical verifier `FAIL`（要求中间应用 `CryptoError`），功能 verifier `PASS`；新 Positive Judge `VALID`。独立审阅又查 Base 的 `MessageDispatcher.errorToObj` / `Utils.objToError` 和 `LoginViewModel` 捕获路径，确认这次跨 worker 类型映射设计成立。负向 mini-swe 生成“清除凭据但不恢复登录表单”的错误解，Judge `RELEVANT_NON_EQUIVALENT`，功能 verifier `FAIL`。完整流水线自动 `accepted`、final-audit `PASS`，独立审计 `PASS` 记录于 `attempt_005/review/independent_audit.json`；该条可计入完成数。

**实际慢点**：新 attempt 几乎没有改 verifier，但独立语义模型审查仍用了数分钟；正向 QA 是多步 mini-swe 源码探索与构造（47 次模型交互）＋原/新 verifier 容器回放＋独立 Judge，之后还有负向 QA。文件格式转换和打包本身不是瓶颈。当前未观察到 endpoint 报错；耗时来自长模型会话与串行质量门槛。`request_timeout_seconds=600` 是单请求上限，不能当作每次实际耗时。后续可评估按输入/提示指纹复用完全相同的审查结果，但必须保留每次 QA 的独立候选与回放，避免性能优化绕过质量门槛。

**界限**：功能 verifier 在 Node 夹具中直接组装真实产品类，没有启动完整 worker/UI。候选的 worker 可行性由生产源码审查支持，不宣称形式化覆盖所有实现。这是对上一次同进程 QA 假阳性的明确约束。
