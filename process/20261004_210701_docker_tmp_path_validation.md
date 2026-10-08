# Docker mini-swe `/tmp` 路径误拦截

- 时间：2026-10-04 21:07 UTC
- 分类：framework-level，路径检查／执行环境。

## 现象与关键证据

Element `attempt_005` 的 Converter 轨迹显示，agent 为 Jest 创建临时测试和日志时调用 `/tmp/...`；`run_bash` 在真正进入 Docker 前返回 `PermissionError: run_bash rejects absolute paths and parent traversal`。甚至只打印 `echo /tmp/foo` 也被拒绝。该轮到约 57 次模型调用仍没有正式测试源，且包含多次路径探查；已中断，未发布。

## 根因和影响范围

`MiniSWEEnvironment.execute` 借用宿主侧 `WorkspaceTools.validate_bash` 做词法检查，只把 `/workspace`、`/app`、`/testbed`、`/solution` 映射成相对形式，遗漏了 Docker 容器本地的 `/tmp`。Jest、pytest 等多语言测试 runner 都需要容器内临时文件，因此这不是 Element 特有路径。词法拒绝发生在 Docker 执行前，不能归类为 verifier 语义错误或 DeepSeek 响应慢。

## 通用修复

`src/swepro_trans/agents/mini_swe_session.py` 增加 `_docker_validation_command`：仅在检查副本中将已知 Docker 路径及容器本地 `/tmp` 映射成相对词法形式；真正执行的原始命令不变。其余绝对路径和 `..` 仍由原有检查拒绝。未加入 repo、instance、commit 或具体测试名特判。

## 验证

`tests/test_converter_checkpoint.py` 增加回归测试：允许容器 `/tmp`，拒绝 `/etc/passwd`、父目录穿越和 `/tmp/../etc/passwd`。与相关 schema、角色审计、语义证据测试一起运行：`PYTHONPATH=src .venv/bin/pytest -q tests/test_converter_checkpoint.py tests/test_conversion_schema.py tests/test_behavior_roles.py tests/test_semantic_evidence.py`，结果 23/23 通过。

## 残余风险与后续

修复后的 Element `attempt_006` 已初始化，但向 DeepSeek 发送具体 Element 任务及仓库上下文的执行被自动审批拒绝；未绕过审批。因此还没有真实 end-to-end 证据证明此修复令该任务完成，也不能据此声称精简 Converter 提示词成功。需要该具体数据外发获得授权后再复验。
