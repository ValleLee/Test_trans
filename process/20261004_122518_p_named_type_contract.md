# P 明确命名的新类型被误判为 Gold-only

时间：2026-10-04 12:25 UTC

## 现象

qutebrowser 的 P 标题写明“Switch to a `FontFamilies` class”，原始 F2P 在 Base 上调用不存在的 `FontFamilies` 而失败。旧转换仅通过 Base 已有的 `QtFont` 等入口验证解析输出，结果 Base 和 Gold 都通过，并把任务判为 `non_discriminative`。这不能证明 P 明确要求的新增类型已得到验证。

## 根因与范围

Converter 提示词、Semantic Judge 提示词和确定性 Gold-only 符号预检均优先要求使用 Base 现有入口。预检还要求 P 写出完整限定名，导致 P 只写类名、未规定未来模块路径时，连该类本身都会被视为隐藏契约。该错误适用于其他 P 明确命名新公共类／类型而不指定完整包路径的任务，并非按当前 instance 编写的特判。

## 修复规则

- P 明确要求的新公共类型是可测试的功能契约；需要行为测试，单纯检查类型存在不够。
- P 未指定的方法、构造参数、模块路径、内部表示仍不能从 R/I、Gold 或原测试中直接继承为唯一接口。
- 确定性预检允许 P 明确命名的新增类，但继续拦截未声明的新成员。
- 若 P 明确命名 Gold 新增类，而候选测试完全没有触及该类，则在 Semantic Judge 前报覆盖不足。
- `non_discriminative` 只适用于 P 未要求的实现机制确实是唯一差异的情形。

## 验证

`tests/test_semantic_evidence.py` 增加 P 命名类获授权、未命名方法不获授权、明确命名识别的测试。qutebrowser 新转换在独立 `attempt_019` 中执行；实际结果以其 revision 和 gate 文件为准。

## 转换实验中的追加发现

`attempt_019/rev_002` 由 mini-swe 生成了 11 条 F2P 映射，却在提交时被旧 schema 拦下：旧规则规定所有 `p_supported_behavior` 必须 `base_repo_observable=true`。P 明确要求新增类时，这个条件与 Base 缺失该类的事实冲突。现已改为仅对 `already_satisfies` 要求 Base 现有观察面；`changed_or_missing` 仍需经过语义审查和 Base/Gold 回放。

首轮 pipeline 的确定性预检又把测试源码中的 Python 文档字符串 `FontFamilies.from_str` 识别为执行依赖。探针现在忽略文档字符串，保留代码行；可选的访问路径仍交由语义 Judge 检查是否形成隐藏契约。相关规则均有定向单元测试。

## 最终实验结果

`attempt_019/rev_005` 通过完整 Stage 2 pipeline 并打包到 `attempt_019/final`。11 条 historical F2P 全部 `rewrite`，没有 drop；最终角色审计为 11 条 functional delta。Docker Base 中恰好 11 条转换测试失败，46 条保留 P2P 通过；Gold 的 60 条测试全部通过。稳定性复跑、Semantic Judge、Positive QA（不同内部表示的有效实现通过）和 Negative QA（相关错误实现被拒绝）均通过。最终 `final-audit` 为 PASS，`instruction_leakage` 为 PASS。

两条原 `to_str` 测试在 P 中缺少明确文本输出语义，经 `specification_gap` 自动生成最小行为补充：单项渲染为原名，多项按原顺序用逗号和空格连接。补充在最终 PR 描述内，不包含 `__str__`、模块路径或 Gold 私有实现。

打包核查另外发现 `tests/__pycache__` 被从 revision 带入 final。已在通用打包代码中排除缓存目录和字节码，并清理本次 final；最终审计重新通过。

## 第二轮审计：公开类的模块位置与执行即断言

人工复查 `attempt_019` 后发现，虽然其测试不限定解析方法或内部结构，类发现仍只搜索两个 Gold 相关模块；P 没有规定模块路径。新建独立 `attempt_020`，改为在项目包中定位顶层 `FontFamilies` 定义后才导入对应模块，并要求解析结果确实是该类实例。11 条 F2P 仍在 Base 失败、Gold 通过；46 条 P2P 保持通过。

本轮还暴露两个跨任务框架缺陷：语义 Judge 返回非 JSON 时，确定性兜底把合法的 `binding_detected=false` 误当空字段，并把 P 已命名的新类误报为 Gold-only；二者现已修复。Judge 协议故障现归为 `judge_transport` 并停止该 attempt，不再错误派发 mini-swe 修测试。补充了对应回归测试。

一次独立语义审查给 `rev_001` PASS，但完整 pipeline 的另一次审查发现更具体的欠转换：原始 Hypothesis 测试在所有随机输入上调用了 `str(families)`，候选测试只检查非空项，没有覆盖字符串渲染不抛异常。框架现明确要求识别“执行调用即检查不抛异常”的历史行为。管线已按该反馈生成 `rev_003`：同一 Hypothesis 域里增加 `str(parsed)`，账本分别记录非空项和无异常渲染。最终接受结果以该 revision 后续的硬校验、正负 QA、审计和打包为准。

`rev_003` 补回 Hypothesis 的无异常渲染后，语义 Judge 再次指出两条 `to_str` 仍只是 `str(parse(canonical_input)) == canonical_input`：直接回显输入的错误实现也能通过。控制器又把 Judge 同时给出的 `specification_gaps` 无条件解释为“规范尚缺”，诱导 agent 将这两条测试移到 gap，即使现有 addendum 已明确写出单项、多项渲染要求。这是反馈路由的通用错误，已改成优先核对有效 P＋现有 addendum；已有规范时保留 rewrite/merge 并增强测试，仅真正缺失的行为进入 gap。`tests/test_pipeline_transport.py` 覆盖这一情形。

`rev_005` 由 mini-swe 在修复后的反馈下生成：11 条 F2P 仍全部 rewrite；单项和多项序列化改用非规范输入，先验证解析后的集合，再验证规范化输出，因此输入回显不能通过。完整管线继续验证中。

## 完成状态（attempt_020）

`attempt_020/rev_005` 已通过完整管线并打包到 `attempt_020/final`。11 条历史 F2P 全部 `rewrite`，没有 drop 或缺口；46 条原 P2P 全部保留。Semantic Judge PASS，确定性 Gold-only 绑定预检 PASS，Docker Base FAIL / Gold PASS，行为角色审计与稳定性复跑 PASS。正向 QA 由 mini-swe 产生不同的正确实现，独立 Judge 为 VALID，原 verifier 与 functional verifier 都通过；负向 QA 的近似错误实现被 Judge 确认为 RELEVANT_NON_EQUIVALENT，functional verifier 使其失败。最终 `final-audit` PASS，含 `instruction_leakage` PASS，错误和警告均为空。

最终 instruction 保留原 PR 描述及外层工作说明、约束，只在 PR 内附加两条关于单项／多项字体集合用户可见文本形式的行为描述；最终 verifier 不限定 Gold 的模块路径、解析方法名或构造签名，并以非规范输入验证序列化不只是回显原输入。
