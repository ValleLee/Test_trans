# qutebrowser：功能补充的来源校验与修订轨迹

记录时间：2026-10-05 20:24 UTC。

## 现象

`attempt_020` 的解析适配器按每个用例的预期值临时选不同公开方法，独立审计用两个不完整解析方法构造出假阳性，因此旧 final 已标为 `audit_rejected`。`attempt_021` 由 mini-swe 修复为整个测试运行固定一个入口，但前两轮在账本中声称字符串输出行为已获说明补充，实际没有 controller 生成的补充，artifact contract 拒绝。第三轮正确进入 `specification_enrichment`，controller 却同时把一句“Historical Hypothesis property / internal robustness probe / no independent product outcome”写进解题者 instruction 的补充文件。这句是审计解释，不是功能要求。

## 根因与通用性

自动补充直接提升 Converter 的 `specification_proposal` 为规范文本，校验器只拦截了句首 `specify/clarify` 等元语言，没有拦截历史测试、verifier 或内部探针的审计说明。任何任务都可能把构造证据的描述误提升为解题要求；这不是 qutebrowser 路径或类名的特例。旧流程在补充无效时还有潜在的未捕获 `ValueError`，会让 controller 崩溃而不给 agent 结构化反馈。

## 通用修复

- `conversion_schema.specification_proposal_is_meta` 拦截历史测试、F2P、verifier、Gold-only、Hypothesis property、内部稳健性探针等来源元语言；只允许陈述可观察产品行为的补充。
- `pipeline.orchestrator` 捕获无效补充提案，转为 artifact gate 失败和自动 repair，而不把文本写进 solver instruction 或直接抛异常。
- `pipeline.repair` 对该失败提供明确反馈：保留独立产品行为的最小条件和结果；纯内部探针只在账本中有证据地排除，不写进补充。
- 新增相关回归测试；完整框架测试 **48/48 通过**。

`attempt_021` 已在发现污染后停止，状态为 `rejected_artifact`，没有可发布 final。下一轮应从补充前的修订复制，在新 attempt 中让 mini-swe 重新分类 Hypothesis 测试与字符串输出行为，随后逐门槛重放。修复尚未得到新 qutebrowser final 的实证，不能宣称该任务完成。

## 20:34 UTC 追加：取消从自由文本推断 specification gap

新 `attempt_022` 首版已经把两条 `to_str` 明确标为 `missing_product_behavior/specification_gap`，给出相同的最小功能提案；Hypothesis 行是 `p_supported_behavior/rewrite`，没有提案。但 controller 仍从该行 `problem_statement_support` 的“not explicit”措辞推断它也需补 P，并把 `behavior_intent` 中的“Verify ...”提入 addendum。说明结构化分类被非规范自由文本推翻，是所有任务都可能遇到的编排缺陷。

已将 `_row_requires_specification_enrichment` 改为只认通过 schema 校验的明确 `specification_gap` / `missing_product_behavior` 与非空 `specification_proposal`，不再从来源解释或 `behavior_intent` 推断题面新义务。保留现有独立语义 Judge 对分类真伪的审查。新增回归测试，完整本地测试 **49/49 通过**。发现后停止了正在错误修订的子进程；`attempt_022` 的原始 `rev_001` 没有污染的 addendum，将按新规则重新进流水线。

## 20:48 UTC 追加：异常类型静态信号误报

`attempt_022` 修订补回 Hypothesis 中对任意已接受输入执行 `str(parsed)` 的无异常 smoke 行为后，独立语义 Judge 指出此遗漏已修；但专项 exact-error 审查因测试夹具用 `except (OSError, UnicodeError, SyntaxError)` 跳过无法扫描的源码文件，把它误判为解题实现必须返回某个中间异常类的隐藏契约。同时，固定 UTF-8 读源码确实可能漏掉使用合法 PEP 263 其他编码的正确实现，这属于独立的扫描鲁棒性风险。

通用框架修复：`binding_signals.exact_exception_type` 不再把任意 `func(Error,...)` 都当成产品异常断言，只对 `assert/expect/raise/reject/throw` 等断言 helper 以及原有 `pytest.raises`、`instanceof` 等模式触发专项审查；保留对真实断言的检出。新增“夹具 except 不触发”和 `assertRaises` 仍触发的测试，完整框架测试 **51/51 通过**。mini-swe 当前修订仍需单独处理源码扫描编码问题；静态误报修复不能代替候选测试的实际验证。

## 21:09 UTC 追加：自动验收后的字符串回显反例

`attempt_022` rev_005 自动通过语义、Base/Gold、46 条原生 P2P、稳定性及正负 QA，完整 Harbor final 已打包。但独立审计发现两条 `to_str` 测试只用 `family` 和 `family1, family2` 这种原始输入本就等于期望输出的规范写法；Hypothesis 只保证 `str(parsed)` 不抛错。若实现把家庭名称解析成正确列表，而 `__str__` 直接返回未经规范化的原输入，全部这些断言可通过；对 `"One Font", Arial`，其输出仍带引号，违反补充后的“渲染解析后的名称”要求。该反例是产品转换验证的通用 identity/echo 漏洞，不取决于实例 ID、模块名或测试名。`attempt_022` 已写独立 FAIL、标为 `audit_rejected`，原自动 final 保留供追溯，不计完成数。

通用改动：Converter 与 Semantic Judge 提示加入“转换/规范化/渲染测试至少用一个期望输出不同于原输入的有效样例，检查简单回显实现是否会误过”；Negative QA 生成提示也建议尝试可运行的回显型近似错误解。该修复需在新修订里用真实 mini-swe、Judge 和回放验证；不能据提示文本本身声称已解决。

## 21:15 UTC 追加：回显反例修订已提交

新 `attempt_023` 复用了上一版 11 条 F2P / 46 条 P2P 的账本及经 schema 校验的一段功能补充。mini-swe 改写了两条字符串渲染用例：单项输入改为带额外空白与引号的 `"  'family'  "`，多项输入改为 `"  'family1' , 'family2' "`，期望分别是 `family` 和 `family1, family2`。因此原样回显输入会失败，而 Gold 的规范化输出应通过。候选刚进入全流程门槛；本记录不提前宣称 final 合格。

## 21:31 UTC 追加：独立审计与 final gate 通过

`attempt_023` 的 11 条 F2P 全部改写，46 条原生 P2P 保留。语义 Judge、Base FAIL / Gold PASS、稳定性、正负 QA 均通过；独立审计复核了非规范输入的字符串规范化反例和不同模块/入口/算法的真实替代解，结论为 PASS。重新运行 `final-audit --write` 以及 `review` 后，`certified_final=true`。此前被拒绝的 attempt 保留为过程证据，发布版本是 `attempt_023/final`。
