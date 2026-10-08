# 2026-09-29 03:18:35 UTC — Stage 1 evidence 迁移问题

## 现象

修复 `layout.py` 的 `PROJECT_ROOT` 导入后，显式初始化 qutebrowser 仍失败：

```text
missing problem statement evidence:
runs/<id>/intermediate/source/problem_statement.md
(and no Stage 1 source at data/stage1/<id>/source)
```

## 原因

旧 run 被移出项目后，旧 source evidence 仍在归档目录中；此前的 Stage 1
准备流程曾经把 source 写入 run，而新契约要求：

```text
data/stage1/<id>/source/
runs/<id>/intermediate/source/  # 仅 Stage 2 选中任务的副本
```

## 修复

将归档 run 中的已生成 Stage 1 source evidence 迁移到：

```text
data/stage1/<id>/source/
```

原始 Harbor task 保持在 `tasks/<id>/original`，没有修改。

## 后续改进

新的 Stage 1 preparation 脚本必须直接写入 `data/stage1/<id>`；Stage 2 init
只从该位置 materialize source 到 run。
