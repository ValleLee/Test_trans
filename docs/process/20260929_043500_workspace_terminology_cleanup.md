# 2026-09-29 workspace 边界术语清理

阶段二现在只使用 `evidence/`、`reference/`、`run/`、`scratch/` 和 `/solution`。清理 `WorkspaceTools` 中不再使用的 `sealed/`、`public/repo` 术语，统一按调用者提供的可见/可写根目录执行边界检查；不改变当前 Converter/QA 的挂载和权限行为。
