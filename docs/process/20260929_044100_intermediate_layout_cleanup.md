# 2026-09-29 intermediate 目录精简

## 发现

已完成任务的 `intermediate/` 下有多组空目录，包括旧版 evaluation、converter staging/current、validation 预留目录和 QA judgments/mutants 等。它们来自初始化阶段的旧预创建清单，当前 Stage 2 代码没有读取这些路径。

## 修复

- `initialize_conversion_workspace()` 只预创建实际稳定产物的父目录：Converter revisions/trajectory、validation 三个 gate、QA candidates/replay、packaging、control 和 review。
- per-session sandbox、trajectory、replay log 等仍由对应阶段按需创建。
- 删除当前已完成任务中的空目录和一次中断遗留的 QA 临时 sandbox。
- 保留所有验证结果、转换轨迹、候选 patch、审阅指标和 `final/` 内容。

## 验证

- `layout.py` 通过 `py_compile`。
- 当前任务 `intermediate/` 不再包含空目录。
