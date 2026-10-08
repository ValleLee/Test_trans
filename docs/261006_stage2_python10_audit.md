# 10 条 Python Functional Verifier 人工审核（2026-10-06）

## 审核范围与结论

- 审核对象：`task_list/stage2_python10.txt` 中的 10 条最终任务。
- 对照材料：原始 `source/problem_statement.md`、原始 F2P/P2P 配置、最终 `instruction.md` 与 `tests/`、`conversion_trace.json`、Base/Gold replay、Positive/Negative QA 摘要；另只读检查了 qutebrowser 镜像中的 `urlutils.py`。
- 10/10 最终 instruction 与各自的 `runs/<id>/source/problem_statement.md` **字节一致**；未把 R/I 或 Gold 说明加入 instruction。
- 10/10 的自动 Stage 2 关卡为 complete，均有 Base FAIL、Gold PASS、Positive QA PASS、Negative QA PASS 和最终包。原始 F2P 分别为 2、4、7、2、1、3、2、17、4、1 条，全部有 conversion trace accounting。
- 自动通过不等于 verifier 对所有正确实现都宽容、对所有违反 P 的实现都敏感。每条任务的 QA 各只验证了 1 个有效 alternative 和 1 个相关 mutant；以下静态反例仍需处理。

## 逐条审核

| 任务前缀 | 判断 | 依据与待处理点 |
| --- | --- | --- |
| `ansible-a6e671db` | 需调整 | AIX 数值与类型断言符合 P，但 `final/tests/run_script.sh` 的 `_CommandSequenceModule` 按固定三次调用顺序给出输出，且用整字典相等比较 `get_cpu_facts()`。一个返回正确五项处理器事实、但增加其他事实或多做一次探测的实现会被拒绝。应按命令语义提供样本输出，并只断言 P 指定的字段。 |
| `qutebrowser-e64622cd` | 基本符合 | 4 个 F2P 都调用 P 明确提到的 `signal_name`，且在同一选择器内先验证 bound 再验证 unbound。只覆盖镜像中的 PyQt5，不能据此证明所有 PyQt 版本。`rev_007/functional_specification.md` 第 35–36、65 行仍称 4 个 bound P2P / 8 个 emitted selectors，实际只有 4 个组合 F2P；说明文档需修正。 |
| `openlibrary-c8996ecc` | 种子范围内符合；P 覆盖有限 | `validate_record` 层验证 IA 与 Amazon 的 1399/1400/1401 边界，Amazon 1399 的拒绝测试已列入 P2P。没有 BWB 测试，也没有检查错误消息中的活动阈值或公共常量一致性。它们在 P 中，但未被原始 F2P 种子覆盖；若实验声明 verifier 覆盖整份 P，须单独扩展范围并记录依据。 |
| `openlibrary-03095f26` | 需调整 | 测试验证 `parse_log` 输出旧 work/author key，符合 P 中“包含当前和先前 key”的中间行为；但使用**精确列表相等**，额外返回新 work 等合理待索引 key 的实现会被拒绝。测试未观察 Solr 或搜索结果，因此不能证明源 work 已从索引移除。至少改为检查必要 key 的包含关系；完整产品结果需要更外层观察。 |
| `qutebrowser-fec187c2` | 优先调整 | F2P 只复制了历史新增的 `test path-search` 场景，并直接调用私有 `urlutils._get_search_url`。本地 Base 镜像中已有公开 `urlutils.fuzzy_url(..., force_search=True)`，它会经过同一搜索 URL 路径。私有函数可在正确重构中改名或移除，因此当前测试仍是实现绑定。其余裸引擎名、编码和开关场景主要靠 241 个历史 P2P；不能把这一条 F2P 解释为独立覆盖完整 P。 |
| `openlibrary-d109cc7e` | 符合 | P 明确要求 `ThingReferenceDict`、`Seed.from_json`、`_list` 与 `type` 行为；最终测试覆盖两条新增路径和一条 Base 已满足的 subject 构造回归。运行器解析器的 `rev_006` 修复已在真实 Base/Gold 日志与正式回放中验证。 |
| `ansible-9142be2f` | 需小幅调整 | 从私有 `_get_shebang` 转向 `modify_module` 合理，但测试额外要求 `module_style == 'new'`，P 未要求此内部分类。进一步只读检查 Base 执行链发现，动作插件把 `modify_module` 返回的 `shebang` 交给 shell 的 `build_module_command`，该返回值决定实际启动解释器；因此不应无依据地要求 `b_module_data` 首行也完全相同。 |
| `openlibrary-c12943be` | 符合 | 17 个原始 F2P 均在 trace 中；最终通过 `load()` 后 edition 的 `lccn` 观察规范化与无效值拒绝，避免把 Gold 新增的 `normalize_lccn` helper 当作产品 API。 |
| `ansible-70948496` | 种子范围内符合；P 覆盖有限 | 4 个原始 F2P 对应 malformed 行、OpenBSD 多行值和执行异常；断言不要求警告原文或命令调用形状。P 还明确要求非零返回码及 Linux/macOS 分隔符，最终选择器未覆盖；5 个原始 P2P 都因 Base 中不存在 patched test file 被排除。可在 `command_error` 同一行为种子中补非零返回码，另记录平台覆盖限制。 |
| `qutebrowser-6dd402c0` | 需调整 | 损坏缓存不抛异常且发出错误级消息符合 P，但测试固定 `adblock-cache.dat` 文件名（P 未规定），只检查消息非空，不检查它与缓存损坏相关，也未验证后续正常操作。换缓存文件命名的正确实现可能误拒；发出无关错误消息的错误实现可能误过。历史 F2P 中通过私有 `_engine` 注入无关 `ValueError` 的断言被排除，需明确记录这一风险。 |

## 建议的下一步

1. 在 Stage 3 前优先修 `qutebrowser-fec187c2` 的私有入口，以及 AIX、Solr、解释器、adblock 四条的具体误拒/漏检点。Ansible 解释器任务应去除无依据的 `module_style` 断言，并依据真实执行命令验证返回的 shebang；不把生成脚本的精确首行作为额外契约。每次新修订都重新执行原有 Stage 2 关卡。
2. 对 `openlibrary-c8996ecc` 与 `ansible-70948496`，先决定评测结论仅针对 historical F2P 转换范围，还是要声称覆盖整份 P；若是后者，按 `docs/optimize_rule.md` 的种子范围规则说明扩展依据。
3. 修正 `qutebrowser-e64622cd` 的非规范性说明，使它与实际配置、执行的 4 个组合选择器一致。

本审核没有改动最终测试或重新运行整批容器；上述结论来自最终工件、现有 replay/QA 证据及局部只读源代码核查。

## 2026-10-06 执行链核查更正

在 Base 镜像只读检查 `/app/lib/ansible/plugins/action/__init__.py`：`_configure_module` 返回 `(module_style, shebang, module_data, module_path)`，`_execute_module` 把 `shebang` 传给 `_connection._shell.build_module_command(...)`；`/app/lib/ansible/plugins/shell/__init__.py` 的该方法把 shebang 去掉 `#!` 后放进最终命令。因此原审计中“只检查返回 shebang 会漏掉实际使用通用解释器”缺少依据，已从上表撤回。后续 verifier 应接受不同的生成脚本布局，只要求实际执行遵从声明解释器。
