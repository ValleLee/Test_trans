# Stage 2 框架外复审记录：已完成包的语义问题

日期：2026-10-08（本地时间）  
用途：记录转换框架报告完成、但框架外独立复审不接受的实例，供判断是否需要调整通用流程。本文只记录证据和候选改进方向，不代表已经修改框架。

## 处理约定

- 框架报告 `complete/accepted` 不等于最终可用；仍需通过框架外复审。
- 框架外复审发现实质问题后，先把该实例挂起，不继续对它反复转换；继续处理其他候选。
- 框架内部拒绝后可以依据反馈做有限修复；但如果语义门禁再次拒绝同一类“未由 P 支持的实现/接口绑定”，或达到本轮 `max_revisions=8` 仍未通过，就停止该实例并挂起，记录拒绝类别和 revision。不要为了把单个实例磨到通过而无限消耗修订轮次。
- 对“规范到实现/表示绑定”采用更紧的上限：首次内部拒绝后只允许一次针对该反馈的定向修订；如果同一任务再次出现同类绑定拒绝，立即挂起，不等通用的 8 次修订上限。若框架已接受的包经独立复审确认绑定 P 未规定的接口或表示，直接挂起，不再逐任务重转。
- 对接口绑定问题，至少记录：测试绑定了什么调用边界/符号、P 是否逐字规定该接口、该接口是否仅在 Gold 出现、是否存在满足 P 的替代实现。相同模式跨任务重复出现时，先合并为框架级类别统一复盘；不在各任务上分别追加特例规则。
- 挂起实例保留当前包、审计结果和失败原因，等框架调整决定后再决定是否重跑。
- 只有 P2P 原样保留且排除数为 0、历史 F2P 已按原意转换为功能行为、独立复审通过、最终 instruction 符合要求的实例才进入新增合格名单。

## 已确认的框架外复审失败

### 1. Ansible `709484969c8a`

- Attempt：`attempt_002`，revision：`rev_005`。
- 转换器状态：`complete` / `accepted`；内部语义审查、确定性绑定检查、Base/Gold 回放、正负 QA 均通过。
- 框架外复审：FAIL。原 P2P 5 条全部原样保留；instruction 只保留 Problem Statement；4 条历史 F2P 均有映射。
- 实际问题：转换测试把 `module.warn` 调用总数固定为 3、2、1。P 要求每条格式错误输入产生警告，并要求命令错误产生警告，但没有禁止额外的有用汇总警告。符合 P 的实现只要多发一条汇总警告也会被拒绝。测试还断言 `module.run_command.called`，即使公开返回值和警告已经足以判定行为。
- 转换器自检中的不一致：自检称只要求“每个错误至少一个非空警告”，并称没有断言精确警告文案；但没有发现测试正文仍把警告总数精确固定。也就是说，自检说明与实际 verifier 没有逐项核对。
- 挂起决定：保留当前包，不纳入合格名单，暂不重转。该任务已从本轮待启动补跑队列移除，以便继续其他候选。
- 证据：`runs/instance_ansible__ansible-709484969c8a4ffd74b839a673431a8c5caa6457-vba6da65a0f3baefda7a058ebbd0a8dcafb8512f5/attempts/attempt_002/review/external_audit_20261008.json`；同目录 `intermediate/converter/revisions/rev_005/self_review.md`。

### 4. qutebrowser `77c355799570`

- Attempt：已接受包 `attempt_007`（其后有一次外审失败）；当时原始 P2P selector 完整保留，instruction 合规，两条 F2P 均有映射。
- 框架外复审：FAIL。repr 测试会拒绝 `values=[ScopedValue(...)]` 这种可能准确表达 value/scope 配对的形式，但 P 没有禁止这种表示，只要求 scoped organization 表示可信。
- 后续处理：`attempt_008` 已在该外审之后启动；依据挂起约定，于 2026-10-08 03:17 UTC 停止当前 pipeline，保留 attempt 产物，不纳入合格名单、不再重跑。
- 证据：`runs/instance_qutebrowser__qutebrowser-77c3557995704a683cdb67e2a3055f7547fa22c3-v363c8a7e5ccdf6968fc7ab84a2053ac78036691d/attempts/attempt_007/review/external_audit_20261008.json`；`attempt_008/intermediate/control/state.json`。

### 3. OpenLibrary `c12943be1db8`

- Attempt：`attempt_002`，revision：`rev_001`。
- 转换器状态：`complete` / `accepted`；17 条历史 F2P 均映射，P2P 原 selector 保留，外层 instruction 也符合要求。
- 框架外复审：FAIL。3 条无效 LCCN 输入的测试只检查原始错误字符串未出现在保存列表中，没有检查公开结果确实表示“无 LCCN/无有效值”；实现若静默写入一个无关的伪造 LCCN 仍会通过。
- 后续处理：该实例的 `attempt_003` 已在对 `attempt_002` 的外审失败后启动。按“先挂起失败任务”的约定，已于 2026-10-08 03:12 UTC 终止该 attempt 的 pipeline；其状态记为 `needs_review`，保留中间产物，不纳入合格名单，也不再重试。
- 证据：`runs/instance_internetarchive__openlibrary-c12943be1db80cf1114bc267ddf4f9933aca9b28-v2c55207218fb8a0138425cbf7d9675272e240b90/attempts/attempt_002/review/external_audit_20261008.json`；`attempt_003/intermediate/control/state.json`。

### 2. Ansible `be2c376ab87e`

- Attempt：`attempt_004`，revision：`rev_005`。
- 转换器状态：已生成并接受包；P2P 14 条精确保留、排除数为 0；instruction 移除了 Requirements/New Interfaces。
- 框架外复审：FAIL。两条历史 F2P 被映射，但测试直接调用 `RoleMixin._build_doc` 并依赖固定位置参数签名。P 没有命名 `_build_doc`，也没有指定这个签名；该方法带前导下划线，是私有入口。符合 P、使用不同公开方法名或签名的实现也会被拒绝。
- 更关键的漏检证据：转换器自检声称“P 明确要求 `RoleMixin._build_doc`”，并据此把私有入口当成规范接口。内部语义审查重复接受这个说法。其所谓支持证据引用的是 P 对 entry-point filter 的描述，并未实际包含 `_build_doc` 这个名称。确定性 binding gate 和 Base repository probe 都返回 PASS / `gold_only_symbols: []`，没有识别 Gold 新增的私有方法。
- 挂起决定：不纳入合格名单，暂不重转；等待判断是否调整框架的 P 引文核验和 Gold/Base 差异检查。
- 证据：`runs/instance_ansible__ansible-be2c376ab87e3e872ca21697508f12c6909cf85a-vba6da65a0f3baefda7a058ebbd0a8dcafb8512f5/attempts/attempt_004/review/external_audit_20261008.json`；同目录 `intermediate/converter/revisions/rev_005/self_review.md`、`intermediate/validation/semantic/review.json`。


### 6. Ansible `379058e10f3d`

- Attempt：`attempt_004`，revision：`rev_009`；框架状态 `complete/accepted`，内部 semantic、Base/Gold、positive/negative QA 与 package 均通过。
- 框架外复审：FAIL。原始 P2P 66 条按原顺序全部保留、排除数 0；4 条 F2P 全部映射；最终 instruction 与冻结的 `source/problem_statement.md` 字节一致。
- 问题：functional verifier 对公开依赖扫描器生成的 archive 做 `names == REQUIRED_ARCHIVE_MEMBERS` 精确全量集合比较，沿用了历史测试的 30 个文件清单。P 只要求目标 shim 在未显式导入时不进入 minimal-module archive，并没有禁止其他有用依赖或规定全部 30 个成员。满足 P、但归档中包含额外依赖的实现也会被拒绝。
- 处理：保留 attempt 和 audit 证据，挂起、不计入新增合格名单、不立即重转。候选框架类别：历史精确集合断言是否应在转换时收窄为 P 支持的可观察条件；检查语义门禁是否能发现完整输出集合的过度约束。
- 证据：`runs/instance_ansible__ansible-379058e10f3dbc0fdcaf80394bd09b18927e7d33-v1055803c3a812189a1133297f7f5468579283f86/attempts/attempt_004/review/independent_audit.json`、`review/final_audit.json`、`final/tests/functional/test_recursive_finder_verifier.py`。

## 与上述两项不同的终态

以下任务没有框架报告可接受的最终包，因此不是“框架接受后被框架外复审打回”的实例；它们也暂不重跑，避免把两种失败来源混在一起：

- Ansible `942424e10b20`：attempt 进入 `non_discriminative_task` 终态，Base 上转换后的历史 F2P 已通过、Gold 上也通过，没有形成 Base FAIL / Gold PASS 的功能区分。已从本轮补跑队列移除，并由 `34db57a47f87` 替代；替代任务仍按正常流程处理。
- qutebrowser `44e64199ed38`：attempt 进入 `non_discriminative_task` 终态，当前没有合格最终包。该实例先挂起，不在原任务上继续耗费转换轮次。
- OpenLibrary `308a35d69994`：`attempt_007/rev_008` 进入 `non_discriminative_task`。判定说明指出，历史差异只是模块路径和类身份变化；Base 已存在相同的公开可观察行为，因此转换后的 verifier 在 Base 与 Gold 上都通过。不能把 Gold 的路径/类名差异制造成产品契约。先挂起，不重试。
- qutebrowser `ed19d7f58b26`：`attempt_007/rev_009` 被框架语义审查拒绝。转换漏掉两条历史断言中的全局隐藏设置（无 URL pattern），且隐藏选项只核对名称和 pattern，没有核对渲染值；同时把 P 未规定的 `--include-hidden` 拼写固定进测试。属于框架审查已捕获的语义/接口绑定问题，不是框架接受后外审拒绝；先挂起，不重试。
- qutebrowser `ff1c025ad321`：`attempt_010/rev_009` 被 artifact contract 拒绝。trace 将大量历史 F2P 行映射到最终并未生成的测试，错误集中在 `tests/unit/config/test_configfiles.py` 下的 selector。属于框架的产物映射门禁拒绝，先挂起，不重试。

- OpenLibrary `09865f5fb549`：`attempt_006/rev_009` 已于 2026-10-08 03:23 UTC 以 `rejected_semantic` 终止（8 次修订）。框架指出 `test_from_markdown_metadata_column` 漏掉两个历史 F2P 情形的空/无值 `pagenum` 后置条件；`_assert_fields` 在 `None` 时跳过该断言。此项由框架语义门禁拒绝，不是框架外复审失败；保留产物，暂不重跑。证据：`runs/instance_internetarchive__openlibrary-09865f5fb549694d969f0a8e49b9d204ef1853ca-ve8c8d62a2b60610a3c4631f5f23ed866bada9818/attempts/attempt_006/intermediate/validation/stage2_pipeline.json`。

## 可能需要评估的通用框架问题

这些是从上述证据归纳出的候选方向，不是针对警告、Ansible 或某个具体方法名增加特例规则：

1. **自检声明与测试实现逐项对账。** 自检中“至少一个”“允许额外输出”“不依赖某接口”等声明，应能对应到最终测试断言；若测试有更强约束，应要求指出 P 中的直接依据。
2. **P 支持应核对原文。** 对公开方法名、签名、字段等精确接口声称得到 P 支持时，应要求给出 P 原文片段，并检查片段是否真的包含该标识符或约束；主题相近的描述不能代替直接依据。
3. **检查 Gold 相对 Base 新增的调用边界。** 运行时可用性和 Base/Gold 区分不足以证明接口由 P 授权。对 verifier 调用的仓库方法，应识别它是否仅在 Gold 新增，以及名称/签名是否由 P 指定或属于允许使用的原仓库公开实现。
4. **负向反事实应覆盖“符合 P 的替代实现”。** 不只检查违反 P 的实现能否被拒绝，也检查改变未规定的调用次数、额外有用输出、公开方法命名/签名后，仍符合 P 的替代实现是否能通过。

可以先讨论是否把这些变成通用检查或 QA 门槛，再决定改哪些文件；本记录本身没有修改转换 prompt、语义审查器或验证逻辑。

## 后续记录

后续每当框架报告一个包完成、而框架外复审判定不合格时，在本文追加：instance、attempt/revision、框架状态、复审依据、挂起状态，以及该问题更像任务数据问题还是通用框架缺口。合格实例仍进入独立于原名单的新增名单。


## 框架内部反复修订后挂起，待统一复盘

这组与上面的“框架已接受、框架外复审拒绝”不同：前序 attempt 已被框架自己的门禁拒绝；随后启动的重试尚未完成，本轮按“同类问题不要无限修复，先汇总框架缺口”的约定主动停止。因此它们不是转换成功包，也不是本轮独立审计失败；目前均无最终 revision、无 accepted 包，不计入合格数据。

### 处理约定

- 内部门禁的反馈仍可用于有限次修复；如果重复修订继续出现同一类语义、接口绑定、产物映射或回放问题，则停止该任务并加入框架复盘队列。
- 挂起时保留所有 revision、门禁报告和当前 attempt；不把“用户策略下主动停止”伪装成框架自然终态，也不继续开启新 attempt，直到这些问题完成分类并决定统一修补方案。
- 当前四个重试已于 2026-10-08 03:55 UTC 停止。批次 JSON 记录 `needs_review`、`exit_code: -15`、`final_revision: null`；本地进程检查未发现这四个实例仍在运行。其他仍在跑的任务不受影响。

### 挂起实例

1. **OpenLibrary `09865f5fb549`** — `attempt_006/rev_009` 曾在 8 次修订后被语义门禁拒绝：Markdown 元数据测试没有覆盖历史 F2P 对空/无值 `pagenum` 的后置条件。重试 `attempt_007` 又在语义审查发现历史 F2P selector 的角色归类问题：一个 Base 已通过的 selector 被归入 F2P，而不是按 P2P 后缀归类；还涉及 Markdown 规范化行为的证据/覆盖。重试在 `rev_003` 生成后停止。**候选框架类别：历史测试清单与转换映射的语义对账、P2P/F2P 分类约束、规范化行为的证据跟踪。** 证据：`attempt_006/intermediate/validation/stage2_pipeline.json`、`attempt_007/intermediate/validation/semantic/review.json`、`attempt_007/intermediate/control/state.json`。

2. **qutebrowser `ed19d7f58b26`** — `attempt_007/rev_009` 曾被语义门禁拒绝：遗漏全局隐藏设置和渲染值检查，并将 P 未规定的 `--include-hidden` 拼写固定进测试。重试 `attempt_008` 的语义审查通过，但 hard replay 遇到 pytest `INTERNALERROR`，导致本轮无法可靠判断转换测试；修复过程中已生成 `rev_003`，之后按复盘策略停止。**候选框架类别：语义修复完成后回放错误的分类/归因，及大规模 selector 下测试收集与 replay harness 的稳定性。** 证据：`attempt_007/intermediate/validation/stage2_pipeline.json`、`attempt_008/intermediate/validation/semantic/review.json`、`attempt_008/intermediate/validation/stage2_pipeline.json`、`attempt_008/intermediate/control/state.json`。

3. **qutebrowser `ff1c025ad321`** — `attempt_010/rev_009` 曾被 artifact contract 拒绝：trace 中多条历史 F2P selector 映射到了最终没有生成的测试。重试 `attempt_011` 的语义门禁又发现测试依赖 Gold 中存在、P 未指定的 `configtypes.Font.set_defaults`，因此错误地绑定 Gold 实现。重试在 `rev_004` 生成后停止。**候选框架类别：历史 F2P 到最终测试的双向完整性校验、Gold 相对 Base 的新增符号/调用边界审查，以及 P 原文引用验证。** 证据：`attempt_010/intermediate/validation/stage2_pipeline.json`、`attempt_011/intermediate/validation/semantic/review.json`、`attempt_011/intermediate/control/state.json`。

4. **Ansible 替代实例 `34db57a47f87`** — 前一 `attempt_001/rev_009` 因功能测试绑定 `module.run_command`/mock 调用边界、拒绝符合 P 的 subprocess `nproc` 调用而被语义门禁拒绝；在 8 次修订后仍未解决。重试 `attempt_002` 尚处于语义审查阶段时停止，没有形成新结论。**候选框架类别：用符合 P 的调用路径反事实检查验证测试没有固定实现内部调用边界；对拒绝理由执行 P 原文核对。** 证据：`attempt_001/intermediate/validation/stage2_pipeline.json`、`attempt_002/intermediate/control/state.json`。

上述实例的完整名称和复盘标签列于 `task_list/python_parked_for_framework_review_20261008.txt`。上述类别是待验证的框架假设，不是已确认的根因；后续应并列检查 converter prompt、自检/语义审查 prompt、artifact contract、replay harness 和 retry controller，找出哪些关口应前移或加强，再一次性修补通用机制。

### 实现/接口绑定：合并复盘类别

以下实例体现同一类风险：转换测试把规范要求绑定到特定仓库调用边界、私有接口或 Gold 中新增的符号。框架内部拒绝并不表示应该无限迭代；按上述有限修复规则，重复触发同类拒绝或用满 8 次修订后即挂起。

- **Ansible `be2c376ab87e`**：框架报告接受，但框架外复审发现测试固定调用 P 未命名的私有 `RoleMixin._build_doc` 及其参数签名。说明现有语义审查/绑定检查也可能漏放此类错误。
- **qutebrowser `ff1c025ad321`**：重试的语义门禁发现测试依赖 Gold 才有、P 未指定的 `configtypes.Font.set_defaults`；同一任务前序 attempt 还存在 F2P 映射缺失。说明需同时核对 Gold/Base 新增符号和历史测试映射完整性。
- **Ansible `34db57a47f87`**：8 次修订后仍围绕 `module.run_command` 的调用边界失败；符合 P 的 subprocess `nproc` 调用被错误排除。说明当前反馈/修复循环可能持续围绕实现路径，而未稳定转向可观察行为。
- **OpenLibrary `1351c59fd436`**：多次 attempt 后仍要求扩展作者记录必须使用 `db_name`，但 P 只要求得到统一作者 identifier，并未规定字段名。说明 converter/semantic QA 可能把历史 F2P 或 Gold 的数据表示误当成规范接口；该任务已挂起，不继续做逐任务补丁。

这四例先作为一个“规范到实现接口的授权与替代实现检查”类别归档，而不是三个任务特例。后续框架复盘应检查：converter 是否从 P 的真实措辞推导验收接口，semantic gate 是否核实引文和断言，确定性 gate 是否能发现 Gold-only 符号，以及反事实 QA 是否验证满足 P 的其他实现也能通过。


5. **qutebrowser `99029144b510`** — `attempt_003/rev_005` 曾获接受且旧的独立审计记录为 PASS，但其 `final_audit.json` 明确记载原始 P2P 58 条、保留 45 条、排除 14 条，不符合当前“原始 P2P 全部保留、排除数为 0”的验收条件，因此不能计入合格名单。随后 `attempt_005/rev_009` 在 8 次修订后被语义门禁拒绝：ForceDarkMode 缺失时没有保留历史要求的 Qt 6.6 fallback 行为，且没有独立验证 copy 操作不改变原定义。**候选框架类别：旧版独立审计/最终审计对 P2P 排除策略不一致；历史 F2P 行为逐项对账和负向副作用回归不足。** 当前没有可按新标准接受的包；先挂起，不再继续重试。证据：`runs/instance_qutebrowser__qutebrowser-99029144b5109bb1b2a53964a7c129e009980cd9-va0fd88aac89cde702ec1ba84877234da33adce8a/attempts/attempt_003/review/independent_audit.json`、`attempt_003/review/final_audit.json`、`attempt_005/intermediate/validation/semantic/review.json`、`attempt_005/intermediate/validation/stage2_pipeline.json`。

6. **qutebrowser `ebfe9b7aa0c4`** — `attempt_005/rev_009` 在 8 次修订后被内部 semantic gate 以 `rejected_semantic` 终止，没有最终包。报告发现 `test_category_logger_name[custom]` 将历史 F2P 的 `category='network'` / `qt-network` 错写为 `js` / `qt-js`，且多个 category/stack-trace 转换新增了历史断言和 P 均未要求的精确 message 文本。**候选框架类别：历史 F2P 的输入与断言逐项对账、无依据的精确输出约束，以及 8 次修订后自动挂起。** 当前 attempt 已终止，保留产物，不继续重转。证据：`runs/instance_qutebrowser__qutebrowser-ebfe9b7aa0c4ba9d451f993e08955004aaec4345-v059c6fdc75567943479b23ebca7c07b5e9a7f34c/attempts/attempt_005/intermediate/validation/semantic/review.json`、`intermediate/validation/stage2_pipeline.json`。


#### 后续任务的挂起规则

实现/接口绑定问题已经跨 Ansible 与 qutebrowser 重复出现，说明不能只依赖逐任务修复。它应作为一个待统一复盘的框架控制类别处理：

- 对同一任务的实现/接口/表示绑定拒绝，首次反馈后最多做一次定向修复；若再次收到同类拒绝，立即保留当前 revision、报告和状态并挂起，不等到 8 次通用修订上限，也不再开启新 attempt。
- 若框架已接受的包被框架外审计发现依赖 P 未规定的私有入口、Gold-only 符号或固定内部调用边界，直接挂起该任务，不做逐任务补丁式重转。
- 单个 `info` 级风险提示且后续语义门禁、回放均通过，不单独触发挂起；需有实际拒绝或验证证据，避免把可检查的风险提示误当成失败。
- 挂起清单记录任务、attempt/revision、触发证据和统一复盘类别。只有在 converter 的 P 原文核验、语义门禁、确定性绑定检查和替代实现反事实 QA 完成共同评估后，才批量恢复相应类别。

当前归入该类别的实例为 Ansible `34db57a47f87`（多轮后仍固定调用边界）、Ansible `be2c376ab87e`（外审发现私有 `_build_doc` 与未规定签名）、qutebrowser `ff1c025ad321`（重试绑定 Gold-only `Font.set_defaults`），以及 OpenLibrary `1351c59fd436`（多次尝试仍绑定 P 未规定的 `db_name` 表示字段）。它们已列入 `task_list/python_parked_for_framework_review_20261008.txt`，应作为一组复盘，不逐条继续消耗转换轮次。当前运行任务中尚未发现新的同类拒绝；仅有一条信息级风险提示且语义审查通过，因此暂不据此中断该任务。

### 新增外审失败：最终 instruction 未剥离 Requirements / New Interfaces

- **Ansible `5c225dc0f5bf`**：`attempt_001/rev_002` 被 Stage 2 接受，P2P 7/7 原序保留，历史 F2P 1/1 映射到面向行为的测试，断言通过 `set_state_for_host` 观察后续任务迭代状态。
- **框架外复审：FAIL**。最终 `final/instruction.md` 仍是完整原始 Harbor instruction，包含 `## Requirements` 和 `## New Interfaces`；冻结的 `source/problem_statement.md` 已删除这两节。该结果不符合本轮明确目标，因此不计入新增合格数据，也不做仅针对该任务的包补丁。
- **框架缺口证据**：同一 attempt 的 `review/final_audit.json` 却记录 `instruction_leakage=PASS`。`src/swepro_trans/validation/final_audit.py` 的 `_LEAK_PATTERNS` 没有检查这两个章节，也没有要求最终 instruction 与冻结 P-only source 一致；`layout.initialize_conversion_workspace` 将策略写为 `retained_harbor_instruction`，与 Stage 2 架构文档所述“最终 instruction 去掉 Requirements/New Interfaces”不一致。
- **处理**：保留 attempt 和两份 FAIL 审计，加入 `task_list/python_parked_for_framework_review_20261008.txt`。归类为通用的 instruction materialization / final audit contract 缺口，待统一修补后再决定是否恢复；不影响其他正在运行的任务。

### 新增实现/表示绑定案例：OpenLibrary `1351c59fd436`

- `attempt_008/rev_008` 被框架接受；正式 final audit 为 PASS，历史 F2P 1/1、原始 P2P 16/16 且排除数 0，最终 instruction 与 P-only source 一致。
- 框架外复审：FAIL。`source/problem_statement.md` 只要求从作者姓名得到统一 identifier，并未规定扩展后必须使用字典键 `db_name`。`tests/verifier_merge_marc.py` 的两个 expansion 测试都直接读取 `authors[0]['db_name']`，因此符合 P、但使用其他 identifier 字段并由匹配器消费的实现会被拒绝。历史 F2P 和 Gold 中的 `db_name` 是构造证据，不等于 P 对该字段名的授权。
- 该任务早先 attempt 也曾因 identifier 类型/表示绑定、未证明作者身份影响匹配等问题被外审打回；当前 attempt 虽补上身份差异比较，却仍固定未被 P 命名的字段，说明逐任务修复循环未稳定消除表示绑定。
- 处理：保留 `review/independent_audit.json` 与 `review/external_audit_20261008.json`，挂起、不计入新增合格名单；归入“规范到实现接口/表示授权与替代实现检查”，不再单独重转。

### 新增外审失败：警告总调用次数被精确固定

- **Ansible `709484969c8a`**：`attempt_002/rev_005` 被框架接受，4/4 F2P 已映射、5/5 原始 P2P 保留，instruction 与 P-only source 一致。
- **框架外复审：FAIL**。`final/tests/test_sysctl_converted.py` 的 `_assert_warnings_nonempty(..., expected_count=N)` 要求警告总调用数严格等于坏行数；命令错误路径也固定为恰好一次。P 要求每条格式错误的行产生警告、解析继续，并要求命令执行错误时给出警告，但没有禁止额外的汇总警告。因此“每条坏行至少得到对应警告”被误写成“总调用数精确等于坏行数”，会拒绝仍满足 P 的实现。
- **框架缺口证据**：测试文件开头声称不固定 warning call count，但 helper 实际按 `expected_count` 比较 `len(module.warn.call_args_list)`；语义/QA 最终接受了这个更强断言。该问题跨任务复现了此前记录的无依据 warning-total 上限风险。
- **处理**：保留独立审计 FAIL，加入 `task_list/python_parked_for_framework_review_20261008.txt`；待统一检查 converter、自检和 semantic/反事实 QA 对“至少一次/每个对象一次”与“总次数不得多于 N”的区分后再恢复。

### 新增外审失败：错误类型检查缺少正向语义约束

- **Ansible `12734fa21c08`**：`attempt_001/rev_003` 被框架接受，原始 P2P 4/4 原序保留，F2P 1/1 转换；最终 instruction 与冻结的 `source/problem_statement.md` 字节一致。
- **框架外复审：FAIL**。新测试调用公共 `yaml.dump(..., Dumper=AnsibleDumper)`，但只断言异常不是 PyYAML `RepresenterError` 且消息非空。因此任意无关的 `ValueError("bad input")` 等错误也会通过，无法证明用户收到的是 undefined-variable error。P 不规定固定异常类或文案，但要求错误体现 undefined-variable condition；开放具体拼写不等于不验证错误语义。
- **框架缺口证据**：converter 的 self-review/semantic QA 把“避免固定异常类和英文文案”放宽成了“接受任意非 RepresenterError”，而负向 QA 没有用一个非空但语义无关的错误作为反事实。Base/Gold 区分通过，因此普通 hard replay 也没有暴露此缺口。
- **处理**：保存两份独立审计 FAIL，加入 `task_list/python_parked_for_framework_review_20261008.txt`；待统一讨论如何检查错误的语义类别，同时允许合理异常类型和本地化文案。不对单个任务做包级补丁。
