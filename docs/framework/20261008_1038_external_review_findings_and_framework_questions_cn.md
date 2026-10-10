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
- 处理：attempt_004 的 FAIL 记录保留且不计入合格名单。通用 converter 与 semantic Judge 规则现已明确限制 P 未要求的完整输出集合等值比较；因此按当前共享规则恢复一次有界转换，attempt_005 已启动，结果需重新通过框架门禁和独立审计。
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
- **处理**：保留 attempt 和两份 FAIL 审计，加入 `task_list/python_parked_for_framework_review_20261008.txt`。归类为通用的 instruction materialization / final audit contract 缺口。2026-10-08 修补后，`package_final` 与 final audit 共用 P-only instruction 构造函数，审计会逐字比较 `final/instruction.md` 与 P 加已审 addendum，并检查 Requirements/New Interfaces 标题；Stage 1/Stage 2 的 policy metadata 也已更正。回归测试覆盖该泄漏场景。该历史 attempt 仍保留为 FAIL，不因框架修复自动改判。

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

### 新增外审失败：转换测试仍直接调用私有 ELF parser helper

- **qutebrowser `34a13afd36b5`**：`attempt_001/rev_004` 被 Stage 2 接受，最终审计记录历史 F2P 1/1、原始 P2P 5/5 且排除数 0，最终 instruction 与 P-only source 一致。
- **框架外复审：FAIL**。两个转换测试直接调用 `qutebrowser.misc.elf._parse_from_file(io.BytesIO(...))`。该名称是私有 helper；最终测试没有通过 caller-facing `parse_webenginecore` 或其他公共产品表面观察行为。Converter 在自检中知道入口是私有的，但用“Base 已存在/稳定边界”作为理由；语义门禁与公共/私有接口控制仍接受了该设计。
- **框架缺口证据**：早期 `rev_001`/`rev_002` 曾通过公开 `parse_webenginecore` 入口测试，后续为制造 Base FAIL / Gold PASS 转向私有 helper。这显示当前流程在功能区分压力下可能把“可区分”优先于“公共可观察契约”。P 要求解析错误行为，但没有授权该私有函数名作为验收接口。
- **处理**：保存独立审计 FAIL，加入 `task_list/python_parked_after_external_review_20261008.txt`，不计入新增合格名单，不进行单任务修补。候选统一类别：公开行为与私有实现边界冲突时，如何保留可测的 P 语义、同时不为制造 Base/Gold 差异而下沉至私有 helper。

### 通用控制补充：私有入口的反事实审查

- **发现**：qutebrowser 的外审失败表明，仅在 converter 自检中提醒“使用公共入口”不够。即使私有 helper 存在于 Base，转换器仍可能为制造 Base/Gold 差异而将其当成测试入口。
- **规则调整**：`binding_signals.py` 对可执行测试中的私有成员直接调用生成 `private_entrypoint_call` 信号；focused counterfactual 与 semantic Judge 必须区分仓库 helper 和测试夹具 helper，并检查“移除/改名私有 helper、保持相同公开行为”的合规替代实现。仓库中存在该符号不等于公开契约。若 verifier 因直接调用私有方法而拒绝替代实现，必须改为公共产品路径；若没有公平的公共区分路径，则记录访问契约缺口，不得下沉至私有 helper 制造区分。
- **范围**：仅新增通用审查约束，不修改任何单条任务的转换包，也不自动禁止测试辅助函数。原仓库代码仍可作为理解行为、构造夹具和跟踪调用链的证据；最终验收入口须由 P 或既有公开契约支持。


### 新增框架内 QA 发现：历史枚举值被误当成规范闭集

- **Navidrome `23bebe4e0612`**：首轮 revision `rev_001` 的 hard replay 与 positive QA 通过；negative QA 构造只把 `transcodeOffset` 报告版本从 1 改为 2 的公共 API 实现。Judge 认为其仍可满足 P 的“让客户端查询服务器支持哪些扩展”，因此判该变体有效；verifier 因精确要求三个历史扩展及版本均为 1 而失败，negative QA 正确标出 verifier false positive 并启动修复。
- **框架缺口证据**：converter 与 semantic prompt 已有“无依据的精确集合/值”通用规则，但本次 self-review 仍把历史三项和版本 1 解释为“endpoint 的完整目的”，semantic Judge 也接受该理由。问题在于规则没有要求逐项引用 P 对字面值/闭集的授权，也没有明确区分“报告当前支持内容”与“规范固定内容”。
- **处理**：保留原始 QA 失败与修订反馈；补充 converter、focused converter 和 semantic Judge 的统一规则：历史 fixture、当前 Base/Gold 输出及功能一般目的不能单独授权固定具体枚举/版本；能力发现类行为只有在 P/addendum 明确指定内容时才按闭集断言，否则允许其他真实且符合 P 的报告。此为通用语义审查规则，不对 Navidrome 数据包做手工改写。


### 新增框架内打包失败：报告生成引用未定义变量

- **Navidrome `3bc9e75b2843`**：`attempt_001/rev_004` 的 artifact、semantic、hard replay、behavior-role、stability、positive QA 和 negative QA 均通过，acceptance 状态为 `accepted`；但 pipeline 在 package 阶段返回 `rejected_package`，随后启动 `rev_005`。
- **根因**：`src/swepro_trans/layout.py::package_final` 使用 `paths.specification_addendum_path` 构造最终 instruction，却在生成 `instruction_source`/package report 时引用未定义的 `addendum` 名称。代码在写入 package report 前抛错，导致已通过的任务无法完成打包。
- **通用修复**：先将 addendum path 绑定到局部变量，再将同一变量用于 instruction 构造和 package report。新增真实调用 `package_final` 的回归测试，断言 package report、P-only instruction、state 与 pipeline status 均正确写入；`tests/test_package_final.py` 和 `tests/test_final_instruction_materialization.py` 通过。
- **范围与后续**：这是框架打包缺陷，不是 Navidrome 的语义问题；当前转换进程未终止，修复后会在 package 子进程重新导入代码时生效。该任务仍需等框架 pipeline 完成后再做框架外独立审计。

### 新增框架外审发现：命令回退测试绑定执行器

- **Ansible `ansible-34db` attempt_003**：框架 acceptance、Base/Gold 回放、P-only instruction 和 P2P（原始数量为 0）均通过；统一外审仍判 FAIL。`test_get_cpu_info_nproc` 把 `module.run_command` 设为返回场景专用值，P 只规定 affinity 不可用时回退到 `nproc`，没有规定必须经该 runner 执行。一个用 `subprocess` 调用同一 `nproc` 工具并返回正确事实的实现会在此测试中读到真实环境值，因而被拒绝。
- **框架问题**：语义自审将结果字典视为公共输出，但没有检查环境依赖的 mock 是否把未规定的执行机制变成了隐性接口。外审已按固定标准判为 binding 缺陷并安排重转。
- **处理**：该实例已因 attempt_001/attempt_002 的重复调用边界问题列入框架挂起清单。attempt_003/rev_006 的新外审证据并入该类别；保留包和报告，不再单任务重转，等统一框架复盘后再决定恢复。

### 新增框架内 QA 发现：断言未逐条绑定 P 原文

- **Navidrome `23bebe4e0612`**：`attempt_001/rev_009` 的 Base/Gold 与行为角色审查通过，正例 QA 通过；负例 QA 最终判 `rejected_negative_qa`。候选 `negative_003` 保持相同 JSON body 和 HTTP status，只把 `Content-Type` 改为 `text/plain`。Judge 判为 `EQUIVALENT`：P-only 描述要求客户端能查询支持的扩展，但没有规定 MIME type；functional verifier 仍因 Content-Type 断言拒绝该候选。
- **自检证据**：`self_review.md` 声称 Requirements/Interface 只是构造证据，却又说它们“confirm”了 public report contract，并把非 JSON Content-Type 作为拒绝条件。P-only 原文没有规定 Content-Type。该断言无法由 P/批准 addendum 支持。
- **归类**：转换器未把每个可执行断言逐项绑定到规范引文，语义审查接受了主题相近但更强的推断；是通用早期控制缺口的又一实例，超出 MIME type 特例。
- **通用修复**：更新 `prompts/converter.md`、`prompts/converter_focused.md` 和 `prompts/judges/semantic.md`，要求 `self_review.md` 提供逐断言的 P/addendum 精确引文或独立既有公开契约、并给出 P-conforming 反事实；明确 capability-discovery 的一般目的不自动规定 HTTP metadata、序列化格式或 schema。保持外审标准 v1 不变。
- **后续**：保留 rev_009 与 QA 失败证据；将实例排入当前重试链尾部，待现有重试批次完成后再转换。修订通过框架仍需独立审计，不因本次 QA 结果或 prompt 更新自动合格。

### 新增框架内终止失败：Flipt `84806a178447`

- Attempt：`attempt_001`，最终 revision：`rev_009`；framework pipeline 以 `rejected_semantic` 终止，`repair_count=8`，没有 accepted final package，也没有独立外审 PASS。
- 处理：依照 max-revision 挂起规则加入 `task_list/python_parked_for_framework_review_20261008.txt`；保留全部 revisions 和 semantic 报告，不再单条重试，继续其他 Stage 1 候选。
- `rev_009` 的 semantic 报告指出多项历史 F2P 成功行为被替换成缺资源/空状态错误检查：store build/copy/fetch/list 没有验证成功结果；配置加载漏掉 authentication、poll interval 和 invalid repository validation；defaults 只查 OCI config 非空，未检查 30 秒 poll interval 和 bundles directory 创建；schema 测试遗漏 poll interval。测试 accounting 声称保留/合并了这些义务，但真实 assertion 没覆盖它们。另有 `BundleDirectory`/`BundlesDirectory` 字段绑定风险、依赖 nil source 错误的非产品契约，以及基于 Go type 字符串的无行为断言。
- 候选框架类别：**历史 F2P 逐条行为到可执行 assertion 的闭环缺失**（trace/accounting 通过不代表最终测试覆盖）、**测试文件是否实际编译执行的证据不足**、**多轮修复仍未维持已确认行为义务**。这条属于框架 semantic gate 最终捕获的失败，不是框架接受后被独立审计打回。
- 证据：`runs/instance_flipt-io__flipt-84806a178447e766380cc66b14dee9c6eeb534f4/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、同目录 `validation/repair_feedback.json` 与 `control/state.json`。

### 新增框架内终止失败：Vuls `4c04acbd9ea5` 与 `d18e7a751d07`

- 两条均为 Stage 1 选定的 100 条之一。两者的 `attempt_001/rev_009` 都在 `max_revisions=8` 后以 `rejected_semantic` 终止，没有 accepted final package，因此不属于独立外审失败，也不进入新增合格名单。
- `vuls-4c04acbd9ea5`：语义门禁发现 Go 测试直接调用未导出的 `diff`、`formatList`，并固定 P 未规定的模型成员名和渲染字符串。该 revision 的语义报告还显示 `historical_test_sources` 为空，无法从源测试逐例核验 `TestPlusMinusDiff`、`TestPlusDiff`、`TestMinusDiff` 的原始行为。
- `vuls-d18e7a751d07`：语义门禁发现测试固定了 P 未规定的扫描器分组、扫描器数量、`Target` 到 `Path` 的对应关系，以及原始库切片的去重表示；P 仅要求非 OS 结果作为扫描库处理并稳定排序。
- **共同类别**：可执行断言没有被有效 P 逐项授权；语义报告虽能指出隐藏契约，但转换修复循环仍反复保留或引入实现/表示约束。`vuls-4c04acbd9ea5` 另暴露历史源测试证据未提供的问题。
- **处理**：按 8 次修订上限挂起并保留全部证据，不做逐任务特判或立即重试；纳入统一复盘“P 引文到断言授权、历史源测试可见性、实现替代反事实”的框架控制。两个实例已加入 `task_list/python_parked_for_framework_review_20261008.txt`。
- 证据：各任务 `attempt_001/intermediate/validation/stage2_pipeline.json`、`validation/repair_feedback.json` 与 `validation/semantic.json`（若存在）。

### 新增框架内终止失败：Vuls `ef2be3d6ea4c`

- Attempt：`attempt_001`，最终 revision：`rev_009`；在 `max_revisions=8` 后以 `rejected_artifact` 终止，无 accepted final package，也无独立外审 PASS。
- 最后 artifact gate 报告 `self_review.md` 缺少结尾 `SELF_REVIEW: PASS`。前一轮 semantic gate 已通过 artifact contract，却判定六条历史 F2P selector 仍为 `t.Errorf` 占位或 `t.Skip`；另指出若干 F2P 义务没有 P 依据或历史源案例映射。修复反馈后仍未完成可执行断言和逐条映射。
- **共同类别**：历史 F2P 到可执行 assertion 的闭环在多轮修复中未完成，且 trace 对行为的说明超出 P/源测试证据；与 Flipt `84806a178447`、Vuls `4c04acbd9ea5`、`d18e7a751d07` 的挂起原因相同。此记录作为跨任务框架复盘证据，不据此增加 Vuls 专属规则。
- **处理**：达到 8 次修订上限后挂起，不再单任务重试；保留 attempt、revision、semantic 及 artifact gate 证据。
- 证据：`runs/instance_future-architect__vuls-ef2be3d6ea4c0a13674aaab08b182eca4e2b9a17-v264a82e2f4818e30f5a25e4da53b27ba119f62b5/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、`validation/repair_feedback.json`、`control/state.json`。


### 新增框架内终止失败：Vuls `be7b9114cc95`

- Attempt：`attempt_001`，最终 revision：`rev_009`；达到 8 次修订后以 `rejected_semantic` 终止，没有 accepted final package。
- 语义报告定位到原始 selector `TestParse/image redis`：历史全结果断言还覆盖 `ScannedCves["CVE-2011-3374"]` 及其 affected package/CVE 内容，以及 `util-linux` 的多 binary `SrcPackages` 聚合；新 `redis_deb_os_packages` 只检查 `adduser`、`apt` 和 `adduser` source package，缺少上述输入和断言。
- **框架规则核对**：这不是提示缺少规则。`prompts/converter_focused.md` 已要求对 suite selector 枚举每个 table row、nested subtest、parameterized example 和 distinct outcome，并逐 case 写入 `self_review.md`；`prompts/judges/semantic.md` 已要求独立枚举源测试 case，并将无映射的可观察 case 判为 `under_conversion`。本次 self-review 把整个 `TestParse` 概括成一个行项，断言表也没有覆盖 redis CVE 与多 binary source aggregation；语义门禁正确拒绝了不完整映射。
- **处理**：达到通用 8 次修订上限，加入 `task_list/python_parked_for_framework_review_20261008.txt`，保留 `rev_009` 和审查证据，不再对该 instance 单独重试，继续其他 selected100 任务。当前证据不足以证明 8 次中反复收到同一条反馈，因此暂不据此调整通用 prompt 或重试上限。
- 证据：`runs/instance_future-architect__vuls-be7b9114cc9545e68fb0ee7bc63d7ec53d1a00ad/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、`validation/semantic/review.json`、`intermediate/converter/revisions/rev_009/self_review.md`。


### 新增框架外审失败：Flipt `21a935ad7886` 与 Teleport `87a593518b6`

- **Flipt `instance_flipt-io__flipt-21a935ad7886cc50c46852be21b37f363a926af0`**：`attempt_001/rev_007` 被框架接受，但固定标准 v1 外审 FAIL。原始 F2P `TestLoad` 的 8 类表驱动行为中，最终测试只覆盖 defaults、部分 advanced config 和 gRPC-level 行为；缺少 deprecated cache 两种情形、no-backend、memory cache、Redis cache、database key/value 配置。Trace 也只登记 default、advanced、grpc_level_provided。具体证据见 `runs/instance_flipt-io__flipt-21a935ad7886cc50c46852be21b37f363a926af0/attempts/attempt_001/review/independent_audit.json`。归类为历史 selector 子案例没有逐条连到可执行断言；已挂起，不进入合格清单。
- **Teleport `instance_gravitational__teleport-87a593518b6ce94624f6c28516ce38cc30cbea5a`**：`attempt_001/rev_005` 被框架接受，Base/Gold 与 QA 回放通过，但外审发现 SQL Server 两个新测试在 `verifier_sqlserver_test.go:85,141` 固定使用 `database.SQLServerPinger`。该具体类型只出现在原始 Requirements/New Interfaces，P 未规定名称或签名；替代的公开 pinger/constructor 实现会在编译阶段被拒。原始 P2P 为空，最终无排除；19/19 F2P 有映射；instruction 去掉了 Requirements/Interface，仅含 P 与记录在案的行为级补充。独立审计记录见对应 attempt 的 `review/independent_audit.json`。归类为重复出现的公开接口绑定；已挂起，不单条重试。
- 两条均已从后续 selected100 candidate snapshots 移除，避免重新入队；当前运行中的批次已加载自己的输入，不受快照修改影响。


### 新增有界重试后挂起：NodeBB `05f2236193f4`

- `attempt_001/rev_009` 与单次有界重试 `attempt_002/rev_009` 都在 8 次修订后以 `rejected_hard` 终止；两次语义审查均认为历史排序行为通过 `topics.getSortedTopics` 公共边界转换，Base/Gold 的目标功能选择器结果呈现预期差异。
- 阻断 hard replay 的是两条保留在 selector 清单中的旧选择器：`test/topics.js | Topic's .fork should update the user's bookmark ` 和 `test/topics.js | Topic's teasers should return empty array `。两次 replay 的 Base 和 Gold 都把这两条报为 `ERROR`，因此 P2P replay 不完整；同期 runner 输出中并没有对应的精确标题（teaser 有带 `if first param is empty` 的不同标题）。配置仍保留原始 selector 字符串，转换器无法通过改写 P2P 来规避。
- 该问题在两次完整修复循环中重复，属于 selector 到镜像测试身份解析/历史数据一致性类别，不应继续单任务重试。已加入挂起清单并从未来候选快照移除；保留两次 Base/Gold replay 证据，待统一解决 selector 不存在或标题漂移时的策略。注意：这两条没有计为通过或 P2P 排除；任务仍不合格。

### 新增框架内终止失败与已实施通用修复：Teleport `e6895d8934f6`

- `attempt_001/rev_009` 达到 8 次修订后以 `rejected_semantic` 结束，没有 accepted final package，不计入合格数据。语义审查指出同一个历史 F2P 混合了一个 Base-failing 的 P 支持行为和五个 Base-existing 行为；对应的子义务没有显式 `base_behavior_status`，但整行标为 `changed_or_missing`。转换器的自由文本说明声称这些子义务已分流，实际 schema fallback 却把它们全部继承成 changed。
- **通用缺口**：prompt 虽要求每个产品义务独立声明 Base 状态，`obligation_accounting_errors` 仍允许子义务继承 row-level 状态。因此 mixed row 的声明与可执行 F2P/P2P selector 角色可能矛盾；该不一致直到 semantic Judge 才被发现，之后多轮修复仍没有补上缺字段。
- **通用修复**：产品行为义务现在必须显式填写自身的 `base_behavior_status`；缺少时 artifact/schema gate 直接给出 accounting error，不再静默继承 row-level 值。更新了 converter JSON 示例和 semantic gate 规则。新增回归测试覆盖“row 有状态、子义务缺状态”的情形；conversion schema、converter checkpoint、revision selector contract 与 semantic evidence 相关测试共 38 项通过。
- **后续**：该 attempt 仍是 rejected，代码修复不追溯改写其审计结果，也不把它计入合格名单。其是否重试留在 selected-100 未合格队列中，在当前批次收尾后按新 schema 评估；保留 rev_001–rev_009 和原始 semantic 证据。
- 证据：`runs/instance_gravitational__teleport-e6895d8934f6e484341034869901145fbc025e72-vce94f93ad1030e3136852817f2423c1b3ac37bc4/attempts/attempt_001/intermediate/validation/stage2_pipeline.json` 与 `attempts/attempt_001/intermediate/converter/revisions/rev_009/conversion_trace.json`。

### 新增 QA 框架缺口：基础设施重放失败消耗语义候选额度

- **NodeBB `0c81642997ea` attempt_002**：positive 候选 `positive_001` 至 `positive_003` 的 Judge 均判 `VALID`，原始测试通过，functional verifier 输出 `verifier passed`；但容器结束检查因测试运行时留下未跟踪的 `appendonly.aof` 返回 92，replay 将其标为 `infrastructure_failure=true`。旧 runner 仍把每次结果记为普通候选 `fail`，三次耗尽 `max_positive_attempts`，最终生成 `rejected_positive_qa`，之后可能触发 converter 重写。
- **通用缺口**：虽然 false-positive 检测排除了 infrastructure failure，正/负 QA 候选收集器没有区分“候选语义失败”和“回放没有完成”，基础设施问题仍会消耗候选额度并污染转换修复环。
- **通用修复**：QA runner 对同一候选最多做配置的基础设施重试（默认 2 次），不调用 Judge，也不消耗新候选编号；持续失败以 `replay_infrastructure_failure` 单独记录。orchestrator 对该终态不启动 converter repair，保留 revision 与 replay 证据供恢复后重跑。新增 runner 与 orchestrator 回归测试；QA、pipeline、schema 相关测试共 49 项通过。
- **范围**：此修复不把存在 `appendonly.aof` 的候选算作通过；重放未干净完成时仍不能进入独立审计或合格清单。NodeBB 原 attempt 的历史结果不追溯改写，需要后续在适用的新 QA 流程下重跑。

### 新增批次运行缺口：初始 converter session 没有总时限

- **Navidrome `0a650de357bab` attempt_001**：初始 converter agent 等待 endpoint 连接约 51 分钟，进程一直停在 poll；revision 近 50 分钟没有变化，agent 日志只记录启动信息。该调用的有效 API request timeout 为 600 秒，但 `run_stage2_batch.py::_run_one` 对初始 `subprocess.run(agent_cmd)` 没有 wall-clock deadline。
- **通用缺口**：controller 为 repair agent 提供 3600 秒上限，批次 runner 的首轮 agent 却可能无限占用 worker。partial artifacts 能恢复，但没有 timeout 的进程不会进入 artifact gate 和 repair 流程。
- **通用修复**：批次 runner 新增 `--agent-timeout-seconds`（默认 3600）；到时先向进程组发送 SIGINT，让 agent 执行清理并写出中断状态，等待 30 秒后才升级为 SIGTERM/SIGKILL。只要 revision 目录存在，runner 仍把已有产物交给 pipeline 校验和修复。新增超时回归测试，Stage 2 runner 相关测试 4 项通过。
- **当前批次**：本批次进程在代码更新前启动，不能热加载新 deadline。已对该 Navidrome agent 发 SIGINT；它写入 `converter_interrupted`，batch 随后让 pipeline 接手并创建 `rev_002`。其他正在接收 endpoint 数据的 agent 保持运行。

### 新增框架内硬回放失败与通用修复：Teleport `73cc189b0e96`

- `attempt_001/rev_009` 达到 8 次修订后以 `rejected_hard` 结束，无 accepted final package。Base 与 Gold 均未真正运行 verifier：`test.sh` 直接调用 `/tests/run_script.sh`，但该文件权限为 `0644`，容器输出 `Permission denied`；两边因此都报告 selector 缺失。
- **通用缺口**：artifact contract 检查文件存在性，却未检查标准 runner 的可执行位，导致明显的打包错误直到两次 Docker replay 才暴露，并消耗完整修复轮次。
- **通用修复**：`src/swepro_trans/validation/revision.py` 在 artifact gate 检查 `tests/run_script.sh` 是否有执行位；缺失时提供 `chmod +x` 的直接修复反馈，避免进入 Base/Gold 回放。新增 `tests/test_artifact_script_permissions.py`，权限与 selector contract 定向测试 3 项通过。已用新 gate 重检 rev_009，得到预期的 `tests/run_script.sh must be executable (chmod +x)`。
- **后续**：不手工改写该任务的旧 revision 或回填通过结果。待当前 10 路批次结束后，将该 Stage 1 任务作为新 attempt 重试；新 attempt 使用通用检查与修复反馈，再按统一外审标准核验 P2P、功能化 F2P、P-only instruction 后决定是否入合格名单。
- 证据：`runs/instance_gravitational__teleport-73cc189b0e9636d418c4470ecce0d9af5dae2f02-vee9b09fb20c43af7e520f57e9239bbcf46b7113d/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、`.../revisions/rev_009/tests/test.sh` 与 `run_script.sh`。

### 新增框架内终止失败与 selector-role 反馈修复：Teleport `b5d8169fc0a5`

- `attempt_001/rev_009` 在 8 次修订后以 `rejected_artifact` 结束；没有 accepted final package，因此未进入框架外审计。trace 把 `TestConverterOSSMigration/AdminRoleMigrated` 和 `TrustedClusterMigrated` 同时用于 `changed_or_missing` 与 `already_satisfies` 两类行为。agent wrapper 的配置重建层已经拒绝这种双重角色，但本轮 artifact feedback 只呈现了 P2P 不匹配和 self-review 结尾错误，未直接展示 selector 冲突。
- **规则核对**：converter 与 focused converter prompt 已明确要求两种 Base 角色使用不同 selector；因此不再增加重复的任务提示。
- **通用修复**：artifact contract 现在直接从 obligation accounting 导出 delta/regression selector 集合并报告重叠项，使修复反馈准确指出冲突 selector。新增 `tests/test_artifact_selector_roles.py`，连同脚本权限和 selector contract 测试共 5 项通过。用新 gate 对 rev_009 重检后，两个冲突 selector 均被明确列出。
- **后续**：排入现有批次结束后的单次 bounded retry，让转换器能收到精确 gate 反馈；如果新 attempt 再次出现同类冲突，则挂起等框架统一复盘，不继续逐任务循环。旧 attempt 的拒绝记录不改写。
- 证据：`runs/instance_gravitational__teleport-b5d8169fc0a5e43fee2616c905c6d32164654dc6/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、`.../revisions/rev_009/conversion_trace.json`、`.../revisions/rev_009/repair_feedback.json`。

### 新增框架内终止失败：Teleport `c782838c3a17`

- `attempt_001/rev_009` 在 8 次修订后以 `rejected_semantic` 结束，没有 accepted final package，不进入框架外独立审计。历史 F2P selector `TestState` 是 gocheck suite bootstrap，实际运行完整 `CacheSuite`；转换器只发出一条 `cache.Config.Watches` 配置检查，漏掉资源写入、watcher 启动/事件和公开 getter 行为。
- semantic gate 从 `rev_004` 起多轮指出 suite-level selector 必须逐 case 映射，`rev_006` 还指出新增 `TestState` 与现有 bootstrap 同名会导致 Go 编译重定义；最终 `rev_009` 仍缺 case inventory 并欠测同一组行为。
- **规则核对**：converter、focused converter 和 semantic Judge 已要求对 suite/file selector 枚举子案例、参数化用例及独立结果。此次失败表明 8 轮反馈仍未收敛，而不是缺少此类通用要求；不添加 CacheSuite 专属 prompt。
- **处理**：达到修订上限后挂起，加入 `task_list/python_parked_for_framework_review_20261008.txt` 并从当前 pending 清单移除，保留全部原始 revisions 与语义反馈。和 Flipt/Vuls 的同类案例一起复盘“suite bootstrap 到实际子案例清单”的转换控制；不在本轮立即开启第 9 次单任务转换。
- 证据：`runs/instance_gravitational__teleport-c782838c3a174fdff80cafd8cd3b1aa4dae8beb2/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、`.../revisions/rev_004/rev_006/rev_008/rev_009/repair_feedback.json`。

### 新增通用语义探测缺口：Gold diff 中的 Go receiver method 声明

- **证据任务**：Vuls `instance_future-architect__vuls-54e73c2f5466ef5daec3fb30922b9ac654e4ed25` 的 `attempt_001/rev_009`。转换 verifier 直接调用 `VulnInfos.FilterByCvssOver`、`FilterIgnoreCves`、`FilterUnfixed` 和 `FilterIgnorePkgs`；这些方法由 Gold patch 以 Go receiver method 形式新增。P 未规定这些方法名或签名，独立审计发现这一接口绑定。
- **通用缺口**：deterministic Base-provenance probe 已扫描 verifier 的限定符表达式，也识别 Gold patch 中的 class/def 声明，但声明提取正则不识别 Go 的 `func (receiver Type) Method(...)`。因此即使 Base grep 证明同名方法不存在，`gold_defined_symbols` 仍为空；语义 Judge 也可能漏判。
- **通用修复**：声明提取现同时识别 Go 普通函数与 receiver method。候选 verifier 引用 Gold 新增方法且 P 未授权时，沿用现有 Gold-only deterministic gate 拒绝；没有加入 Vuls 方法名或其他仓库专属规则。
- **验证**：新增 `_gold_defined_symbols` 和真实 `_base_probe` 回归用例，分别检查 receiver method 解析、注释排除、Base 缺失和 Gold-only 分类。`tests/test_semantic_evidence.py` 与 `tests/test_semantic_binding_signals.py` 共 44 项通过。
- **后续**：当前批次 attempt_001 以 `rejected_behavior_roles` 结束。已排入当前批次结束后的单次 bounded retry，新 attempt 使用该通用检测；旧 attempt 不追溯改写，也不计入合格名单。

### 新增重试决策：Vuls `fd18df1dd4e4` 与 Teleport `e6895d8934f6`

- 两条 `attempt_001/rev_009` 均在 8 次修订后因语义门禁拒绝：混合历史 F2P 中已经由 Base 满足的义务仍被放进 `fail_to_pass`。trace 的子义务缺少 `base_behavior_status`，row-level `changed_or_missing` 被静默继承，和 selector 的实际 Base 行为冲突。
- 这是已经定位并修复的通用 schema 缺口：每个产品义务现在必须显式给出自己的 Base 状态，缺字段会在 artifact/schema gate 直接反馈。两条都进入 post-current selected-100 单次重试队列；attempt_001 保留为失败证据，只有新 attempt 通过全门禁并独立审计后才可合格。

### 新增框架内失败并挂起：Teleport `59d39dee5a8a`

- `attempt_001/rev_009` 在 8 次修订后以 `rejected_artifact` 结束。转换 trace 把同一 Go 父测试 `TestInitCACert` 下的多个 historical F2P 子 selector 列为 emitted tests，但实际源码只包含父 selector；artifact contract 因找不到每个历史子 selector 对应的 emitted test 而拒绝。`self_review.md` 终止标记也缺失。
- 这是 selector 身份与可执行子案例的映射缺口；连续 8 轮仍未修好，不做任务专属补丁或第九轮尝试。加入 `task_list/python_parked_for_framework_review_20261008.txt`，与 suite/subtest accounting 问题一并复盘。
- 证据：`runs/instance_gravitational__teleport-59d39dee5a8a66e5b8a18a9085a199d369b1fba8-v626ec2a48416b10a88641359a169d99e935ff037/attempts/attempt_001/intermediate/validation/stage2_pipeline.json` 与 `.../revisions/rev_009/conversion_trace.json`。

### 新增框架内终止失败与自检产物一致性问题：Navidrome `5001518260732`

- `attempt_001/rev_009` 达到 8 次修订后以 `rejected_artifact` 结束，没有 accepted package。直接的 artifact error 是 `self_review.md must end with SELF_REVIEW: PASS`。
- 该 self-review 正文虽然在中段写有 `SELF_REVIEW: PASS`，但其规范来源说明称 Requirements/Interface “expanded”了 Problem Statement，并将由这些材料提取的接口作为有效约束；这和当前 P-only 规范规则冲突。文件尾部另有多条 `repair audit marker` 注释追加在 PASS 标记之后，最后一条为 marker 44，导致末尾格式门禁拒绝。
- **待统一复盘的通用问题**：converter/repair agent 已有明确的 P-only 与结尾标记要求，但仍在 8 轮后留下自相矛盾的规范来源说明；repair 审计信息被写入 `self_review.md` 的终止标记之后，覆盖了已满足的文档后置条件。需要明确审计注释的存放位置及每次修订后重新生成/校验 self-review 的责任，并保证语义审查能检查“P 是唯一规范来源”的实际陈述，而不只依赖末尾标记。
- **处理**：加入 `task_list/python_parked_for_framework_review_20261008.txt`。本轮不再为该任务单独开启第九轮/新 attempt；保留全部 revisions 与 gate 证据，等统一复核规范来源追踪和 self-review 生命周期控制后再决定是否重试。该任务没有通过框架接受，也未进入独立外审或合格清单。
- 证据：`runs/instance_navidrome__navidrome-5001518260732e36d9a42fb8d4c054b28afab310/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、`attempts/attempt_001/intermediate/converter/revisions/rev_009/self_review.md` 与 `data/stage2_batches/stage2_pending_selected100_20261008_20261008T063640Z/instance_navidrome__navidrome-5001518260732e36d9a42fb8d4c054b28afab310/pipeline.log`。

### 新增框架内终止失败：Teleport `2be514d3c33b`

- `attempt_001/rev_009` 在 8 次修订后以 `rejected_semantic` 结束；没有 accepted final package，也没有进入框架外独立审计。
- 历史 F2P 包含 precomputation mode 激活、缓冲填充及重复激活等行为。P 明确描述了预生成并缓冲 RSA key pairs、激活模式后缓冲应及时填充，但没有规定一个可调用的公共激活入口。最终 revision 把这些义务映射到既有 `GenerateKeyPair()`：Base 的按需生成路径也满足它，因此没有 Base FAIL / Gold PASS 的区分；同时遗漏了激活预计算模式和缓冲开始填充的可观察行为。
- **待统一复盘的通用问题**：当 P 要求一种带有内部状态的功能，但没有规定触发该功能的公共操作时，转换器容易把不能从 Base 区分的旧行为误标为 `already_satisfies`，或者转而依赖 Requirements/Interface 中的实现入口。框架需要明确如何识别此类“规范行为存在、公共触发面未定义”的任务，并在形成测试前标记规范缺口/不可判定性；不能静默将内部结构升格为 solver contract。
- **处理**：加入挂起清单，并从可变 pending 清单移除，避免同一框架缺口被再次直接排队。待和其他规范授权、Base/Gold 区分及接口绑定案例一起复盘，再决定是否需要行为级澄清和一次有界重试。
- 证据：`runs/instance_gravitational__teleport-2be514d3c33b0ae9188e11ac9975485c853d98bb-vce94f93ad1030e3136852817f2423c1b3ac37bc4/attempts/attempt_001/intermediate/validation/stage2_pipeline.json`、`.../revisions/rev_009/repair_feedback.json`、`.../revisions/rev_009/self_review.md`。

### 新增框架外审失败：Navidrome `29b7b740ce46`

- `attempt_001/rev_003` 通过框架 acceptance 和正式 final audit；独立审计确认 P-only instruction、空 P2P 清单原样保留、两个历史 `TestCache` 新增行为映射完整，Base FAIL / Gold PASS 可复现。
- 阻断点在 `final/tests/verifier_options_test.go:15,58`：测试要求 `cache.Options` 和 `NewSimpleCache(...Options...)` 这一精确导出 API。P 只要求可配置容量/lifetime 及相应淘汰、过期行为；符号名、字段名和构造签名仅出现在 Requirements/Interface。一个通过 `NewSimpleCacheWithOptions(Config{...})` 或公开 `Configure(limit, ttl)` 实现相同行为的候选会被当前测试编译拒绝。
- **通用问题**：公开导出符号也可能是 Gold/Interface 单方面新增的未授权入口。转换器把“功能需要配置入口”误推成“P 授权了某个确切构造 API”，没有在 P-to-test authorization 阶段检查 callable 的名称、参数形状是否被 P 承诺。应与 Ansible/Teleport 的 public-interface binding 类别合并复盘；不是给 Navidrome 增加 Options 特判。
- **处理**：独立审计判 FAIL，不加入新增合格清单；加入框架复核挂起清单并从可变 pending 文件移除。后续是否行为级澄清及有界重试留待通用 access-contract 规则统一确定。
- 证据：`runs/instance_navidrome__navidrome-29b7b740ce469201af0a0510f3024adc93ef4c8e/attempts/attempt_001/review/independent_audit.json`、`.../review/final_audit.json`、`.../final/tests/verifier_options_test.go`。

#### 已实施通用修复：Go 新增命名类型的 Gold-only 来源检测

- **根因**：语义 Judge prompt 已明确要求不能用 Interface/Gold 授权 P 未规定的 constructor/signature；本例 converter 自检错误地把 Interface 当规范来源，Judge 也漏判。确定性 `_gold_defined_symbols` 只提取了 class/function 和 Go function/method，没提取 Go `type Options struct`，因此 `cache.Options` 没成为 Gold-only candidate。
- **修复**：Gold 声明扫描现在也提取通用 Go `type Name` 声明（struct、interface、alias 等）；原有 package-qualified Base probe 会据此把 verifier 引用的缺失类型标成 Gold-only，再由 P 授权规则决定能否通过。没有加入 `Options` 或 Navidrome 专属名称。
- **回归验证**：新增 `_base_probe` 集成式单测，模拟 `cache.Options` 在 Base 包不可用、Gold 新增 `type Options`，要求结果含 `cache.Options` Gold-only；`tests/test_semantic_evidence.py` 和 `tests/test_semantic_binding_signals.py` 共 45 项通过。原 `attempt_001/rev_003` 的 acceptance/audit 历史不改写。
- **后续**：该任务移出框架挂起表，进入 current batches 结束后的单次有界重试队列；若仍无 P 授权的公共配置入口，就保留 FAIL/HOLD 并记录访问契约缺口，不强行采用 Gold API。

### 新增通用回放缺口：Navidrome `c90468b895f6` 的旧 F2P 补丁阻断 Base verifier

- `attempt_001/rev_009` 在 8 轮后以 `rejected_behavior_roles` 结束。P2P selector 列表为空，但 hard replay 仍将完整的原始 `test_patch.patch` 同时打入 Base 和 Gold。原 F2P `TestModel` 在 `mediafile_test.go:62` 直接访问 Gold 才新增的 `Album.Paths`，因此 Base 在运行新 verifier 前就编译失败；所有转换 selector 被记为 `ERROR`，无法验证实际 Base/Gold 行为。
- **通用缺口**：框架把“为了运行未修改的 P2P 测试而暂存原始测试补丁”无条件用于 F2P Base/Gold replay。没有 P2P 时，原补丁没有任何保留用途；应用它反而让历史 F2P 的旧接口依赖遮蔽新 verifier 的结果。
- **通用修复**：hard replay 和 stability replay 现在仅当原始 P2P selector 非空时暂存原始测试补丁；正/负 QA replay 也按原始 P2P 清单决定是否注入，并将实际 staging 状态回传给 Stage 3 regrade。P2P 非空时仍沿用原补丁、原 selector 和原序列。
- **验证**：新增 P2P 为空时不注入补丁的 Stage 2/QA 回归测试；`tests/test_p2p_runtime_staging.py`、`tests/test_qa_judge_gate.py`、`tests/test_counterfactual_audit.py` 共 38 项通过，`git diff --check` 通过。
- **后续**：旧 attempt 记录保持失败，不追溯改写。该任务从 mutable pending 队列移除，加入 active batches 结束后的单次 retry 队列；新 attempt 再按统一标准检查 P2P、F2P 转换和 P-only instruction 后决定是否合格。
- 证据：`runs/instance_navidrome__navidrome-c90468b895f6171e33e937ff20dc915c995274f0/attempts/attempt_001/intermediate/validation/hard_replay/result.json`、`.../behavior_roles/audit.json`、`tasks/instance_navidrome__navidrome-c90468b895f6171e33e937ff20dc915c995274f0/original/tests/config.json`。
