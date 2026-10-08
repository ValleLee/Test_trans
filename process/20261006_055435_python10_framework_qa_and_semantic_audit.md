# Python 10 条转换的 QA 门槛与语义审查诊断

时间：2026-10-06 05:54:35 UTC

## 现象与关键 evidence

`task_list/stage2_python10.txt` 的 10 条最终任务均自动通过 Stage 2；人工复核发现若干 verifier 仍可能误拒符合 P 的实现，或漏检特定错误。10 条最终 instruction 与原始 P 字节一致，Base FAIL / Gold PASS 正常，因此问题集中在 verifier 语义质量与 QA 证明力度。

- `configs/experiment.yaml` 设置 `eligible_mutant_target: 2`、`max_mutation_attempts: 5`，但 `src/swepro_trans/qa/runner.py` 只读取后者，并在第一个通过的候选后 `break`。本批 10 条的 negative QA 均为 `attempt_count=1`、`status=pass`。`confirmed_valid_count` 对 negative 恒记 0，不能表示合格 mutant 数。
- `src/swepro_trans/validation/acceptance.py` 只检查正负 QA 摘要 `status=pass` 与 revision，未检查合格候选数或不同 F2P 行为覆盖。因此配置中的目标 2 不影响发布。
- 主语义审查对 AIX、OpenLibrary Solr、qutebrowser URL、Ansible interpreter 和 qutebrowser adblock 的最终 revision 都返回 `PASS`、空 `binding_risks`，尽管人工审查指出固定命令序列与整字典相等、精确列表相等、直接调用私有 `_get_search_url`、断言非 P 的 `module_style`、固定缓存文件名等潜在绑定。`prompts/converter.md` 和 `prompts/judges/semantic.md` 已明确要求避免这类绑定；问题在执行一致性。静态 `binding_signals.py` 当前仅覆盖少数模式，没有这些 Python 风险的专门信号。
- 一个 Positive QA 和一个 Negative QA 只是各验证一个候选与一个破坏点；它们不能证明 verifier 接受所有正确实现或拒绝全部错误。该限制即使修复目标 2 也不会消失。

## Failure classification 与根因

1. **框架级确定性缺陷**：QA 目标配置未被 runner/acceptance 消费；任何任务都可能以少于配置目标的 mutant 数通过。
2. **框架级审查能力缺口**：Judge 对几种实现绑定给出假 PASS，现有静态信号和专项复审没有提示相应反事实。具体测试断言仍属于实例级 verifier 语义问题，应通过 Converter REPAIR 修订，不能靠放宽共享验收标准解决。
3. **按设计的范围限制**：OpenLibrary c899 的 BWB 等 P 行为和 Ansible 709 的部分平台/退出码未被 historical F2P seed 覆盖。依 `docs/optimize_rule.md`，不应仅因 P 包含这些行为就断言本次转换失败。qutebrowser e646 的说明文档数量过时是实例级记录问题。

## 通用修复方向

- 让 runner 按配置收集足够数量的合格 negative 候选，并在候选元数据和 Judge 结果中记录其 `source_f2p`；若目标是语义广度，应要求不同可用行为，而非仅数量。acceptance 必须复核数量、revision 与证据。若 2 个不同可用目标不存在，应明确配置降级或失败策略，避免静默放行。
- 对私有入口、精确整个容器相等、夹具严格调用顺序、未由 P 规定的内部分类或路径等加入通用风险提示及反事实复审。信号应触发有证据的检查，不应无条件拒绝合法公开契约。
- 对本批被指出的具体 verifier 逐条 REPAIR，并复用既有数据与镜像，从受影响的最早关卡重跑。修复前不要把自动 `accepted` 理解为人工语义认证。

## 修改文件、验证方法与结果

本次仅新增本诊断记录；没有修改共享框架、最终测试、验收状态或启动新 endpoint/Docker 运行。只读检查了配置、runner、acceptance、converter/Judge 提示词、10 条 QA 摘要、10 条语义 review 和此前人工审计。代码修复后需要单测证明配置目标被执行且验收会拒绝不足数量，再对受影响任务运行实际 QA 与 Stage 2 关卡。

## 残余风险

人工指出的是可构造的潜在误拒/漏检，尚未对每个案例提交完整替代补丁或 mutant 做动态复现；因此目前不能把全部 10 条判为失效，也不能给出错误率。两个 `eligible_mutant_target` 即使实现，也不能替代独立语义审核。

## 2026-10-06 06:33 UTC：用户确定单 mutant 策略

用户明确选择每条任务 1 个合格 mutant。以上“目标 2 未执行”的诊断保留为旧配置与旧实现不一致的历史记录；它不再是待修复的 QA 数量缺陷，也不要求 runner/acceptance 收集两个 mutant。三处配置的 eligible_mutant_target 已改为 1，现有 runner 的首个合格候选即停止，与该策略一致；max_mutation_attempts 仍是寻找这一个样本的重试上限。

另外，常规及精简 Converter 提示词现都在第一版测试前要求检查私有入口、整份结果相等、固定夹具调用序列和未由 P 指定的内部字段／路径；提交前还须对所有可执行测试（包括 shell 中生成的测试）构造 P 正确的替代实现反例并修正误拒。语义 Judge 的漏检风险仍在，提示词改动尚未由新一轮真实转换验证。
