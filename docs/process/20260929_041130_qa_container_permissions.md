# 2026-09-29 QA 容器写权限修复

## 发现

正向 QA 的 mini-swe agent 可以读取 qutebrowser，但镜像中的 `/app` 属于 root；会话使用宿主 UID 启动，候选 agent 在修改源文件时收到 `Permission denied`，因此无法生成可回放的替代实现。

## 原因

Converter 只写 `/solution`，宿主 UID 足够；QA 的职责是临时修改 `/app` 并导出 patch，两种会话错误地复用了同一 UID 策略。

## 修复

- `MiniSWEEnvironment` 增加显式 `run_as_root` 选项，默认仍使用宿主 UID。
- 正/负 QA 会话在隔离的无网络容器中启用该选项，使镜像工作树可写。
- Converter 和其他只读/输出挂载会话行为不变。

## 验证

- 两个修改文件通过 `py_compile`。
- 重新运行正向 QA，随后继续负向 QA。
