# 2026-09-29 run source 目录归属调整

## 发现

`data/stage1/<id>/source` 与 `runs/<id>/intermediate/source` 内容重复，且 Stage 2 的固定输入证据与过程产物层级混在一起。

## 修复

- `TaskPaths.source` 统一为 `runs/<id>/source`，与 `intermediate/`、`final/`、`review/` 并列。
- Stage 2 `init` 将选中任务的 Stage 1 source 移入 run，而不是复制；未选中任务继续保留在 `data/stage1`。
- Converter、semantic Judge、QA、artifact validator、package report 和配置全部使用 `source/`。
- 当前 qutebrowser 已完成迁移；删除了 `data/stage1/<id>/source` 的重复副本，保留原始任务、Stage 1 报告和所有 Stage 2 审计产物。

## 原始任务读取边界

`tasks/<id>/original` 仍是不可变 Harbor 原任务。Converter 从中读取 historical tests、task.toml、Gold patch 和 solve.sh；hard replay/QA 从中读取原始 tests、镜像配置和 Gold；`runs/<id>/source` 只承载 Stage 1 整理后的 instruction/evidence。
