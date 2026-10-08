# 2026-09-29 instruction 保留边界修复

## 发现

Stage 1 原先直接把数据集的 `problem_statement` 字段写入 solver instruction，导致原始 Harbor instruction 的 `/app` 前言、`<pr_description>` 包装和 `Constraints` 被删除。

## 修复

- Stage 1 现在以不可变的 `tasks/<id>/original/instruction.md` 为源。
- 只删除 `## Requirements` 和 `## New Interfaces` 两个 Markdown 章节及其内容。
- 保留其他文本，包括 PR 包装、任务描述、复现步骤、实际/预期行为和 Constraints。
- `instruction_policy.json` 记录源文件和删除章节；requirements/interface 继续作为 Converter construction evidence。

## qutebrowser 同步验证

- `data/stage1/.../source/problem_statement.md` 和 `runs/.../final/instruction.md` 已更新。
- Semantic Judge：PASS。
- Base/Gold 硬回放：Base FAIL、Gold PASS。
- Positive/Negative QA：保留并通过。
- Acceptance：accepted；final instruction 的打包哈希已同步。
