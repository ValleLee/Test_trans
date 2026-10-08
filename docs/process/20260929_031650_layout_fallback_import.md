# 2026-09-29 03:16:50 UTC — layout fallback 初始化问题

## 现象

按 Harbor-to-Harbor 优化方案移出旧 run 后，执行显式任务初始化：

```text
PYTHONPATH=src .venv/bin/python -m swepro_trans init \
  --tasks-root tasks --instance-id <qutebrowser-id>
```

初始化在 `src/swepro_trans/layout.py` 访问 Stage 1 evidence fallback 时失败：

```text
NameError: name 'PROJECT_ROOT' is not defined
```

## 原因

`layout.py` 使用了 `PROJECT_ROOT / data / stage1 / <id> / source`，但导入列表中只有
`resolve_task` 和 `TaskPaths`。

## 修复

补充：

```python
from .paths import PROJECT_ROOT, resolve_task, TaskPaths
```

## 验证

修复后重新执行同一个显式 `init`，应创建：

```text
runs/<instance_id>/intermediate/
runs/<instance_id>/review/
runs/<instance_id>/intermediate/source/
```

不创建 `final/`，直到 acceptance 和 package gate 通过。
