# 2026-09-29 03:20:45 UTC — WorkspaceTools 清理残留

## 现象

简化 Converter mount 后执行 `agent --dry-run`，mini-SWE import 失败：

```text
IndentationError: expected an indented block after 'if' statement
```

## 原因

删除旧 sealed boundary 检查时，只删除了异常处理语句，留下了空的
`if reject_hidden ...` 分支。

## 修复

移除已经没有有效策略的空分支。当前 Docker session 仍通过显式 mount 列表限制
Converter 的 evidence、reference、run、scratch 和 solution 路径。

## 后续约束

任何 workspace boundary 清理都必须先运行 Python import / dry-run，再进行真实
mini-swe-agent 调用。
