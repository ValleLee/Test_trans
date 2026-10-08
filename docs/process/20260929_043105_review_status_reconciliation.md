# 2026-09-29 审阅状态修正

## 发现

接受和打包已经通过，但人工审阅报告仍显示第一次流水线中断时的 `rejected_positive_qa`。各门结果和 `acceptance.json` 已是通过状态，旧状态会误导人工审阅。

## 修复

`write_human_review.py` 在 acceptance=accepted、final 已打包时将报告状态判定为 `complete`；只有未完成的恢复流程才使用旧 stage report 状态。

## 验证

重新生成 review 后，`metrics.json`/`summary.json` 显示 `status=complete`，并保留所有正负 QA、语义审查和硬回放指标。
