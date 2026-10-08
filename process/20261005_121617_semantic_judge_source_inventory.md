# Semantic Judge 测试文件证据清单修复

时间：2026-10-05 12:16:17 UTC

## 现象与关键证据

Tutanota 转换的 `attempt_001/rev_003` 包含 `tests/build_verifier.cjs`，`tests/test.sh` 调用它；Semantic Judge 却返回“supplied revision_tests 中没有该文件”，并触发 rev_004 修复。文件实际位于 rev_003 的 `tests/` 下。这不是对 P 的语义分歧，而是 Judge 输入证据遗漏。

## Failure classification 与根因

**framework-level / evidence assembly**。共享 `validation/semantic.py` 只枚举 `tests/` 第一层，紧凑 Judge payload 只传 `.sh/.py/.ts/.tsx/.js/.jsx` 等后缀源码，因此 `.cjs` 被静默略过；Judge 把“输入里看不到”误推成“提交物不存在”。任何使用 CJS/MJS 构建器、其他语言辅助源码或嵌套测试文件的 Harbor 任务均可能遇到同类误判，不能按 repo 或 instance 特判。

## 通用修复

- `src/swepro_trans/validation/semantic.py` 递归发现 `tests/` 文件；紧凑证据始终包含完整路径清单及各文件哈希、大小。
- 对 CJS/MJS、Go、Rust、Java 等常见源文件附上限长内容；明确告诉 Judge 清单内文件存在，即使内容因上下文预算被截取。
- `tests/test_semantic_evidence.py` 覆盖 CJS、嵌套 MJS、配置尾部 selector 和非代码文件仅列清单的行为。

## 验证与残余风险

`PYTHONPATH=src .venv/bin/pytest -q tests/test_semantic_evidence.py`：6/6 通过。更新后的 Judge 对同任务 rev_004 返回 PASS，未再声称构建脚本缺失；后续 Base FAIL / Gold PASS、稳定性、正负 QA 和最终包独立 Docker 重放均通过。限长源码仍可能隐藏文件尾部语义；完整路径清单只证明文件存在，不能替代运行校验。Judge 也可能犯其他语义错误，仍须保留独立硬回放与 QA。
