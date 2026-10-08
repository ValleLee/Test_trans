# Classic-five 最终产物与框架稳定性审计

时间：2026-10-05 12:30 UTC

## 范围和方法

按用户确认，只审计 `data/classic_oracle_summary.json` 所列五条任务；未启动其他任务转换。检查五条当前 accepted attempt 的 `final/instruction.md`、`final/tests/`、原始 P、F2P 对账、正负 QA 和修复轨迹。重新运行 `PYTHONPATH=src .venv/bin/python -m swepro_trans final-audit --all-runs`，总体 `PASS`，五条均无 error/warning。框架测试重新运行 `PYTHONPATH=src .venv/bin/pytest -q tests`，30/30 通过。

## 五条结果

| 任务 | accepted attempt / revision | F2P 对账 | instruction | 门槛和 QA | 独立语义审查 |
| --- | --- | --- | --- | --- | --- |
| qutebrowser | attempt_020 / rev_005 | 11/11 rewrite | 原 P 加两条集合文本呈现的行为级澄清 | 全部通过 | 解析入口不限定 Gold 的 `from_str` 方法；P 标题明确要求 `FontFamilies` 类。未发现明确 Gold 专属调用断言。 |
| OpenLibrary 作者名 | attempt_001 / rev_004 | 6/6 rewrite；其中 4 条为 Base 已有行为的回归 | 与原 P 一致 | 全部通过；正向解原测试失败、新测试通过 | 从 `read_edition` 的作者输出观察 880 alternate names；`alternate_names` 是 Base 既有作者数据字段（`author.type`、作者页面和检索索引均使用），原 `name_from_list` helper 断言改由公开解析输出观察。 |
| OpenLibrary 查询 | attempt_001 / rev_007 | 1/1 rewrite | 与原 P 一致 | 全部通过；正向解原测试失败、新测试通过 | 从既有 `WorkSearchScheme.q_to_solr_params` 的 `workQuery` 输出观察 `work.` 字段归一化，未要求 Gold helper。 |
| Element | attempt_006 / rev_015 | 10/10 rewrite | 原 P 加加载中、缺少当前设备、仅一台设备时的菜单行为澄清 | 全部通过；正向解原测试失败、新测试通过 | 用渲染 UI、菜单操作和可见结果替代 mock 调用断言；但按全局 `aria-haspopup` 按钮数量等于 1 定位菜单，仍可能拒绝增加其他合法菜单的实现。 |
| Tutanota | attempt_001 / rev_004 | 2/2 rewrite | 与原 P 一致 | 全部通过；正向解原测试通过、新测试也通过 | **存在实现绑定风险**：测试要求 `DeviceEncryptionFacadeImpl.decrypt` 必须将底层异常转成现有 `DomainCryptoError`，并要求凭据层抛出 `KeyPermanentlyInvalidatedError`。两个异常类在 Base 中均已存在，后一种错误还见于凭据提供者接口文档；但 Base 的 facade `decrypt` 接口未声明精确错误类型，P 也没有规定必须由 facade 而非其他层进行异常转换。 |

五条合计 30 条 historical F2P 均有映射，没有账本意义上的 `drop`。这证明覆盖与运行门槛有效，**不自动证明 30 条全都充分摆脱实现绑定**。三个正向 QA 候选使原 verifier 失败而新 verifier 通过；qutebrowser 与 Tutanota 的原 verifier 也通过其正向候选，故这两条的 QA 没有提供“摆脱原结构依赖”的强反例证据。

## 框架问题和本次处理

### 1. 规格补充函数与测试契约脱节（已修复）

- 现象：完整测试初次运行 28/30 通过，两条 `tests/test_behavior_roles.py` 因 `addendum_exists` 旧参数触发 `TypeError`。
- 根因：通用函数已改为接收 `addendum_text` 以对已记录的行为提案去重，测试仍调用旧接口；另一个旧测试没有提供实际行为提案。
- 分类：跨任务的框架测试维护问题，不属于任何实例。没有改动生产判断逻辑。
- 修复：按现行接口更新两条测试，补充“相同提案已进入 addendum 后不得再次触发补充”的断言。
- 验证：完整测试 30/30 通过，五条最终审计仍为 PASS。

### 2. 语义 Judge 与正向 QA 的覆盖盲区（未修复）

- 现象：Tutanota 最终测试和正向 QA 都沿用“facade 转 `CryptoError`、凭据层再转 `KeyPermanentlyInvalidatedError`”两层结构；正向候选主要改写 try/catch 写法，仍使用相同类型和分层。它无法检验其他层处理相同用户可见故障的解是否会被错拒。
- 证据：`final/tests/functional_test.ts` 第 1–49 行；`intermediate/qa/positive/candidates/positive_001/candidate.patch`；原 P 只描述故障与后果；Gold patch 与最终断言的两层异常类型相同。
- 分类：当前 verifier 的语义风险；同时揭示“一个 VALID positive 即可证明实现无关”的通用 QA 推论过强。单例证据不足以直接加入一条强制禁止具体异常类型的硬规则，因为某些任务确实以类型为公共契约。
- 后续通用改进方向：语义审查要求说明每个精确类型／层级断言的 P 或 Base 公共契约依据；正向 QA 至少尝试一次改变相关架构决策的解，而不是只改同一路径的代码形状。改进后须在这五条中的已知问题上验证，不能仅凭提示变更宣称解决。

### 3. 产出成本与稳定性边界

Element 当前 attempt 共 15 个 revision、1021 次模型 API 调用。轨迹中曾出现构造器迟交产物、路径检查误拒、稳定性包装器递归、P2P selector 名称反馈不足；这些通用问题已有各自修复记录。Tutanota 初次会话 109 次调用后才在提交时发现义务账本数量不匹配，说明可前置校验仍有空间。当前五条 accepted 证明框架能在受监控的单任务流程内完成，但尚未证明新任务可稳定、低成本、无人值守批量转换。

## 结论

**五条已经转换并打包，程序门槛全部通过；框架可用于逐条实验和审计。不能据此宣称最终 verifier 全部足够实现无关，或框架已经适合无人值守批量使用。** 首要待解决质量问题是 Tutanota 的具体异常类型／处理层级约束，Element 的菜单唯一性断言属于较轻的包容性风险。Base 中已有异常类和 OpenLibrary 作者字段不改变上述判断：问题是强制特定处理层级，而不是这些符号是否存在。此次审计没有转换范围外任务，也没有改写已发布 verifier。
