# 错误提示的时间关联与文案宽容度

时间：2026-10-06 07:02:29 UTC

## 现象与关键 evidence

qutebrowser 缓存损坏任务的 rev_001 使用四个英文词根限定“适当错误提示”，同时可能读取故障前已有的 error 消息。离线 Gold 反事实仅把提示改成 “Unable to restore saved blocking rules; refresh the rules to recover.”，保持损坏缓存捕获和错误级别，rev_001 仍误拒。证据在该任务 attempt_002/review/offline_evidence/qute6dd_alt_message.log。P 只要求适当提示和继续运行，没有规定语言、这些词根或具体命令。

## Failure classification、根因及影响范围

这是实例级 verifier 断言问题，也暴露通用提示词/审查缺口：自然语言错误消息若被实现成固定关键词白名单，会把偶然措辞提升为 solver 契约；若不按故障发生时序隔离消息，又可能让旧的无关提示误过。同类模式可能出现在任何错误恢复任务。

## 通用修复、修改文件和验证方法

已更新 prompts/converter.md、prompts/converter_focused.md、prompts/judges/semantic.md，要求只看目标故障后新发的错误消息，检查错误级别、非空和语义关联，构造合理改写或本地化的正确反例。没有写死仓库、任务 ID、消息词语或路径。qutebrowser rev_002/repair_feedback.json 也纳入已实测的替代文案，供后续 Converter REPAIR。

静态检查确认三份提示词与反馈已写入。动态证据限于上述 Gold 文案反例；正式新 revision、Semantic Judge、QA 尚未完成，因为新的内部模型 endpoint 调用被自动审批拒绝，仍待用户消息明确目的地与材料范围授权。

## 残余风险

纯运行时断言无法形式化判断任意自然语言提示是否“适当”。故障后新错误的时序证据和正负 QA 可以降低误过与误拒，但仍需独立语义审核；不能以一个通过的 Gold 文案替代完整审计。

## 07:08 UTC 追加：过度放宽的反例

离线原型把文案约束降为“故障后新发一个非空 error”后，合理改写通过，但把 Gold 错误文案替换为无信息的 “Oops” 也通过；漏检实测证据将保存于 qutebrowser attempt_002/review/offline_evidence。另一个 near-correct mutant 捕获异常却完全不提示用户，被原型拒绝。说明时间隔离解决旧消息误过，但不能单独保证“适当”的信息量。

通用提示词再要求双向反例：至少两种合理改写均可通过，一个无信息泛化提示必须失败；不能简单回到 Gold 原句或四个英文词根。仍需在正式 Converter/Judge 和负向 QA 中核验具体谓词。
