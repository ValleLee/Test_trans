# 2026-09-29 负向 QA 首次候选偏题

## 发现

负向 mini-swe agent 成功提交了候选，但 fresh Judge 给出 `OFF_TARGET`；回放中原 verifier 与 functional verifier 都通过，因此流水线拒绝该候选。

## 结论

这是 QA 候选质量问题，不是转换器误报。负向 QA 要求 mutant 只违反一个 Problem Statement 语义，当前候选没有达到该条件，不能进入接受阶段。

## 后续

保留候选及 Judge/replay 证据，重新生成负向候选。若重复偏题，再增强负向生成提示，要求先从功能测试对应的语义边界选择明确可观察的单一反例。

## 追加修复

首次负向 agent 没有获得 revision 的 `conversion_trace.json` 和功能测试文件，只能从完整仓库猜测一个问题，因而选择了未转换的 `FontFamilies.family` 行为。QA 会话现在把这两项作为只读 reference 提供，并在任务提示中要求 mutant 直接命中一个已发出的 F2P 测试。
