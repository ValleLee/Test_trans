# 2026-10-01：稳定功能性转换与发布审计

## 现象

此前同一批任务出现过三类问题：

1. 转换器把 Gold 新增的类或方法当成了解题者必须实现的接口；
2. verifier 在只读挂载的 `/tests` 下写日志或临时测试，导致 Docker 运行失败；
3. revision 账本、硬重放和最终发布目录各自选择路径，后续未完成 revision 可能覆盖已接受 revision。

这些问题都不是某个仓库的业务特例。它们分别来自共享的语义判定、容器写入边界和运行产物选择规则。

## 已落地的通用修复

- `validation.semantic` 从 Gold patch 的新增定义中提取候选符号，并阻止最终测试只依赖 Gold-only 的类、方法或模块；判定以 Base 的公共/可观察面为准。
- `validation.revision` 要求每个 `rewrite`/`merge` 行实际发出测试选择器，并在硬重放时使用转换账本推导的 Base/Gold expectation；不再把所有任务强行当成 Base FAIL/Gold PASS。
- Converter prompt 和 mini-SWE runtime 明确 `/tests` 是只读挂载；生成测试、pytest 输出、缓存和 parser 结果必须写入 `/tmp` 或日志挂载。
- 新增 `validation.final_audit` 与 CLI `swepro-trans final-audit`。它只读取 canonical `runs/<id>/latest_attempt.json`、接受记录和 revision，不猜目录，不会把后续未完成 revision 当成最终产物。它自动检查：
  - final Harbor 文件是否齐全；
  - canonical F2P 是否逐条记账且无重复、漏记；
  - 当前三分类与 decision 是否一致；
  - instruction 是否泄露测试 selector、Gold/reference implementation 或内部行为标题；
  - semantic、hard replay、stability、positive QA、negative QA 和 acceptance 记录是否全部通过；
  - hard replay 的 Base/Gold expectation 是否与 conversion trace 一致，Positive 是否有独立正确候选（或明确 Base reference），Negative 是否有 judge、回放和功能性拒绝证据。

## 为什么保留 legacy 标记

四个先前已接受的任务是在旧账本 schema 下完成的，已有 semantic、Docker hard replay、stability、positive QA、negative QA 和 acceptance 证据，但缺少后来新增的 `behavior_classification` 与 `base_behavior_status` 字段。自动审计将它们标记为 `legacy`，不会伪造字段，也不会把旧证据冒充为新 schema。今后的新 revision 必须通过当前严格 artifact contract；如果要重新发布旧任务，应重新生成当前 schema revision。

## 五条已下载任务的自动审计结果

| 任务 | 当前发布 attempt | F2P 账本 | instruction 泄露 | 运行门禁 | 结论 |
|---|---:|---:|---|---|---|
| Element Web | attempt_001 | 10/10，legacy | 通过 | 全部通过 | PASS（legacy） |
| OpenLibrary（alternate names） | attempt_006 | 6/6，legacy | 通过 | 全部通过 | PASS（legacy） |
| OpenLibrary（work fields） | attempt_001 | 1/1，legacy | 通过 | 全部通过 | PASS（legacy） |
| qutebrowser | attempt_013 | 11/11，current | 通过 | 全部通过 | PASS |
| Tuta | attempt_001 | 2/2，legacy | 通过 | 全部通过 | PASS（legacy） |

qutebrowser 的 current revision 使用 Base 中已有的字体配置公共边界，不再调用 Gold-only 的 `FontFamilies.from_str`。其 Positive QA 使用未打补丁 Base 作为独立正确实现，Negative QA 使用只改变空项处理的近正确变体；两者均已通过自动回放。

## 使用方式

审计单条任务：

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans.validation.final_audit \
  --task-root runs/<instance-id> --write
```

审计全部已有 run：

```bash
PYTHONPATH=src .venv/bin/python -m swepro_trans.validation.final_audit \
  --all-runs --write
```

`--write` 只在相应 attempt 的 `review/final_audit.json` 写入审计结果，不修改原任务、final verifier 或历史 revision。
