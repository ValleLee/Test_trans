# 聚焦 Converter 提示词缺少精确 schema 契约

- 时间：2026-10-05 07:37 UTC
- 分类：framework-level，prompt/schema contract。

## 现象与关键证据

Element `attempt_006/rev_001` 由 mini-swe/DeepSeek 写出了 10 条 F2P 账本、Jest 测试、自审与 manifest，并提交。`swepro-trans validate` 在 artifact contract 阶段拒绝：全部 F2P 行使用 `decision: preserve`；若干行使用 `behavior_classification: delta` 或 `mixed_base_regression_and_delta`、`base_behavior_status: mixed/failing`，顶层 `task_disposition: complete`，且每个 `obligation_accounting` 条目缺少必需字段。未进入语义 Judge 或硬回放。

## 根因、影响范围与通用修复

`prompts/converter_focused.md` 以自然语言解释四类行为和混合增量/回归，却未列出 `src/swepro_trans/conversion_schema.py` 的 JSON 字段合法枚举及义务对象必填项。模型把说明词误放进机器可读字段。该接口由所有任务共享，错误并非 Element 特有。

已在聚焦提示中直接列出分类、对应 decision、Base 状态、task disposition 及 `obligation_accounting` 必需字段；明确混合一行时行级与逐义务状态如何分工，禁止把 `preserve`、`delta`、`mixed_base_regression_and_delta` 当作枚举值。没有放宽 schema、修改任务代码或加入 instance 特判。流水线已从 rev_001 的失败证据创建 rev_002，交给 mini-swe 自动修复。

## 验证与残余风险

验证证据目前是 rev_001 的确定性 schema 失败和 rev_002 已收到的结构化反馈；提示词修复本身尚需 rev_002 的真实结果证明。即使 schema 修复通过，也不能证明测试面向功能：初稿仍有精确 DOM 属性、test id 和 mock 调用形状，必须由独立语义 Judge、Base/Gold 回放及正负 QA 继续审查。
