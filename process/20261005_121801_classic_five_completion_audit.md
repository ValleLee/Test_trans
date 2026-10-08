# 已发布五条任务的功能转换收尾审计

时间：2026-10-05 12:18:01 UTC

## 范围与证据

`data/classic_oracle_summary.json` 的 `classic-five` 共 5 条，当前 `runs/` 中恰有对应的 5 个实例。`final-audit --all-runs` 返回总体 `PASS`，5 条均无 error/warning；所选 final 的 `tests/` 排除 `__pycache__`、`.pytest_cache` 后，与被 acceptance 选中的 verifier revision 逐文件 SHA256 相同。Tutanota 另以 **final/tests** 在官方 Docker 镜像实际回放：Base exit 1，Gold exit 0，整体 `pass`。

| 任务 | 原 F2P | P 支持改写 | Base 已有行为转回归 | 有证据排除 | 正向 QA | 负向 QA |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| qutebrowser | 11 | 11 | 0 | 0 | VALID，原/新 verifier 均通过 | 相关错误实现被新 verifier 拒绝 |
| OpenLibrary 0dc5 | 6 | 2 | 4 | 0 | VALID，原 verifier 失败、新 verifier 通过 | 相关错误实现被拒绝 |
| OpenLibrary 7232 | 1 | 1 | 0 | 0 | VALID，原 verifier 失败、新 verifier 通过 | 相关错误实现被拒绝 |
| Element | 10 | 10 | 0 | 0 | VALID，原 verifier 失败、新 verifier 通过 | 相关错误实现被拒绝 |
| Tutanota | 2 | 2 | 0 | 0 | VALID，原/新 verifier 均通过 | 相关错误实现被拒绝 |

总计 30 条 historical F2P，全部 `rewrite`，没有 `drop`。每条任务均完成语义 Judge、Base FAIL/Gold PASS、逐 selector 角色审计、稳定性和正负 QA。三个任务的正向 QA 提供了原 verifier 拒绝而新 verifier 接受的更强包容性证据；另外两条只证明了另一个经 Judge 确认有效的实现也可通过，不能夸大为原 verifier 必然过度绑定。

最终 instruction：两条 OpenLibrary 和 Tutanota 与源 P 字节内容一致；qutebrowser 和 Element 各有控制器记录的行为级 addendum，并通过 instruction 泄露审计。

## 范围边界

当前 `data/preparation_report.json` 已更新为 100/100 READY、100/100 镜像存在、100/100 preflight 通过；其中仅上述 5 条已有 `runs/`。`task_list/pilot.txt` 为 20 条。因此五条完成的证据只覆盖 `classic-five`，不能证明 pilot-20 或当前全部 100 条已完成。下一批范围需以用户对“其他几个”的明确答复为准。
