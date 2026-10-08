# 规范补充只能生成一次的问题

- 时间：2026-10-05 08:17 UTC
- 分类：framework-level，Stage 2 规范补充与自动修复路由。

## 现象与证据

Element `attempt_006` 已由两条历史 F2P 的缺口生成 `intermediate/specification_addendum.md`。下一轮独立 Judge 又识别“只有一个设备时不显示退出其他会话”这一未由基础 P 规定、但历史 F2P 涉及的产品行为。此时 controller 的 `_row_requires_specification_enrichment` 只检查 `addendum_exists`：只要文件存在，就无条件拒绝任何新提案。新缺口会在后续 revision 中反复被语义门槛拒绝，无法进入自动补充。

## 根因与通用性

增量规范被设计成一次性布尔状态，而历史 F2P 的行为缺口可以在多轮 Judge/repair 中逐步发现。这与 repo 或具体任务无关；任何后发现的第二个缺口都会受影响。

## 修复

`src/swepro_trans/pipeline/orchestrator.py` 现在按规范化后的提案文本判断是否已记录，只跳过已存在的行为；`_write_specification_addendum` 对新提案追加 section，并保留原有 section 与顺序。Base 已有回归仍不能扩写 P，meta-language 提案仍被拒绝。没有加入 instance、repo、commit 或测试名特判。

## 验证

新增 `tests/test_specification_enrichment.py`，覆盖初次生成、重复提案不再触发、第二个提案追加且不覆盖第一条、Base 回归不触发。连同 Converter/schema 相关回归测试运行：`PYTHONPATH=src .venv/bin/pytest -q tests/test_specification_enrichment.py tests/test_converter_checkpoint.py tests/test_conversion_schema.py`，12/12 通过。

## 残余风险

当前已运行的 pipeline 进程在启动时加载旧模块，需在其完成后以新进程复验真实增量补充。文本去重采用空白归一化，同义但措辞不同的提案仍可能重复；独立语义 Judge 和最终 instruction 审计需要检查最小性与无实现泄漏。
