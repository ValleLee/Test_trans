# 2026-10-01 11:06:47 UTC：框架打磨与五条任务 current-schema 终审

## 1. 本轮目标

用最新 Harbor-to-Harbor 框架逐条完成五个已开始转换的任务，并审计：

- 每条 historical F2P 是否都转成公开/可观察的功能测试；
- final instruction 是否只保留 P、原包装/约束和经审计的行为补充；
- 是否存在 Gold-only API、内部 UI helper、mock call shape 或路径绑定；
- semantic、Base/Gold、P2P、stability、Positive QA、Negative QA 和 final packaging 是否在同一 revision 上闭环。

## 2. 发现的问题与通用修复

### 2.1 functional verifier 修改仓库后未被识别

- 现象：生成测试、patch 或缓存可能遗留在 `/app`，单次测试仍返回预期码。
- 根因：只检查 test exit code，没有对运行前后工作树做等价性验证。
- scope：framework-level，所有语言和 runner 都可能发生。
- 修复：functional replay 前后记录 `git status --porcelain=v1 --untracked-files=all`；不一致返回 92。QA replay 将 91/92/timeout 归类为 infrastructure，不允许作为 negative semantic rejection。

### 2.2 retained P2P selector 只存在于 historical test patch

- 现象：Element 的 39 条 retained P2P 中有测试在 Base/Gold solution patch 后仍不存在。
- 根因：historical `test_patch.patch` 与 Gold solution patch 是两个独立资产。
- scope：framework-level，任何数据集都可能用 test patch 引入/修改 P2P。
- 修复：Converter 可把 historical test patch 原样打包为测试资产；verifier 执行前 apply，`EXIT` 中 reverse，并由 repo-clean gate 验证恢复。

### 2.3 repair revision 从空目录重建，消耗轮次且容易回退

- 现象：语义或 hard gate 只要求局部修复，agent 却重复分析全部 F2P，常在收尾前耗尽轮次。
- 根因：下一 revision 没有继承前一版完整资产。
- scope：framework-level。
- 修复：`pipeline/repair.py::seed_revision` copy-forward tests、trace、spec、review、manifest，排除 cache；结构化 feedback 包含 under-conversion、hidden contracts、drops、spec gaps 和 replay evidence；repair agent 从现有账本开始聚焦修改。

### 2.4 agent 已生成完整产物但 endpoint 长等待

- 现象：文件已完整写入，agent 仍可能在下一次 endpoint 请求上等待。
- 根因：提交协议和远端响应不是原子操作。
- scope：framework-level。
- 修复：完整 artifact 可由 controller 接管继续验证；缺少少量收尾文件时启动 bounded artifact-completion 会话。会话产物和 trajectory 均保留审计。

### 2.5 Judge 输出推理但没有闭集 JSON

- 现象：reasoning 模型可能只返回 reasoning content 或非 JSON，出现 `UNCERTAIN`/协议失败。
- 根因：provider response shape 与 gate schema 不一致。
- scope：framework-level。
- 修复：优先 JSON mode；从同一上下文做一次 schema continuation；只接受 PASS/FAIL、VALID/INVALID、RELEVANT_NON_EQUIVALENT/OFF_TARGET 等角色闭集；protocol/transport failure 不作为业务 PASS。

### 2.6 Base-existing 内部 helper 被误认为公开观测面

- 现象：Element rev_008 用 `Modal.createDialog/LogoutDialog` 的精确内部调用来证明用户已触发退出流程，虽然这些符号在 Base 存在。
- 根因：错误地把“Base 存在”与“公共产品边界”画等号。
- scope：framework-level，UI、router、store、event bus 等任务都会遇到。
- 修复：Converter 与 Semantic Judge 新增通用规则：UI 结果可直接观察时，必须断言 accessible dialog/text/role/control state/navigation；不得用内部 modal/router/store/component 调用代替。rev_009 改为验证可见的 Sign out 确认对话框、正文、按钮和菜单关闭。

### 2.7 TS ESM import 到 Base symbol 的映射不完整

- 现象：`.js/.mjs/.cjs/.jsx` import 在 TypeScript 源仓库中可能实际对应 `.ts/.tsx`，导致 Base presence 误判。
- 根因：semantic probe 只按 import 文本后缀查找。
- scope：framework-level。
- 修复：Base symbol resolution 加入 TypeScript 源变体映射。

### 2.8 空 P2P 仍启动 Docker

- 现象：没有 P2P selector 的任务做无意义 replay，增加耗时和假失败面。
- 根因：stability 未对空集合短路。
- scope：framework-level。
- 修复：P2P selector 为空时明确记录 skip，不启动容器。

### 2.9 同一 accepted revision 无法按新 packaging policy 重建

- 现象：修正 controller 生成的无语义文案后，`package` 因 final 已存在而拒绝。
- 根因：打包器只允许新 revision 替换旧 final。
- scope：framework-level，确定性打包规则变化也需要重建。
- 修复：同一 accepted revision 允许安全重新打包，旧 final 先进入 `archived/`，新 final 重新计算 hash 并更新 review/state。

### 2.10 addendum 的否定句触发 leakage 误报

- 现象：自动说明中的 “does not prescribe ... reference implementation” 被关键词扫描认作泄漏。
- 根因：生成文案与审计 pattern 发生自冲突。
- scope：framework-level。
- 修复：改为 “specific implementation design”，保留相同语义，不出现 leakage 关键词。

## 3. Element 最终修复链

Element 的最终 accepted revision 是 `attempt_002/rev_009`：

1. 前序 revision 已把 10 条 F2P 映射到菜单可达、当前退出、批量退出、loading/no-current inert、单设备隐藏批量退出等行为；
2. rev_007 补齐 historical test patch，但 semantic Judge 指出当前退出只检查菜单关闭，未证明退出流程启动；
3. rev_008 恢复了内部 `Modal.createDialog` spy，hard replay 通过，但人工功能边界审计认定仍然绑定内部 UI factory；
4. 框架规则增强后，rev_009 直接验证可访问的退出确认 dialog、标题、正文、确认按钮和菜单关闭；批量退出保留对公开 Matrix client 副作用及设备 ID 顺序的检查；
5. semantic、hard replay、两轮 stability、positive QA、negative QA 全部通过并打包。

关键结果：

- 10/10 F2P accounted；5 rewrite + 5 merge；0 drop；
- Base functional FAIL；Gold 45/45 required tests PASS；
- P2P 39/39 在 Base 和 Gold 中重复两轮 PASS；
- Positive QA：fresh Judge `VALID`，original PASS，functional PASS；
- Negative QA：fresh Judge `RELEVANT_NON_EQUIVALENT`，original PASS，functional FAIL；
- instruction leakage PASS。

## 4. 五条任务终审

命令：

```bash
PYTHONPATH=src .venv/bin/python -u -m swepro_trans.verifier_conversion \
  final-audit --all-runs --write
```

结果：整体 `PASS`。

| 任务 | accepted attempt/revision | F2P | decision | semantic | hard/stability | 正/负 QA | instruction | final |
|---|---|---:|---|---|---|---|---|---|
| Element Web | attempt_002/rev_009 | 10/10 | 5 rewrite + 5 merge | PASS | PASS | PASS/PASS | PASS | PASS |
| OpenLibrary alternate names | attempt_007/rev_002 | 6/6 | 6 rewrite | PASS | PASS | PASS/PASS | PASS | PASS |
| OpenLibrary work fields | attempt_002/rev_001 | 1/1 | 1 rewrite | PASS | PASS | PASS/PASS | PASS | PASS |
| qutebrowser | attempt_013/rev_001 | 11/11 | 11 rewrite | PASS | PASS | PASS/PASS | PASS | PASS |
| Tuta | attempt_002/rev_001 | 2/2 | 2 rewrite | PASS | PASS | PASS/PASS | PASS | PASS |

汇总：

- historical F2P：30；
- accounted：30；
- rewrite：25；
- merge：5；
- drop：0；
- unresolved specification gap：0；
- current schema：5/5；
- strict final audit：5/5 PASS。

qutebrowser 的 functional expectation 是 Base/Gold 都通过，因为目标行为已经可从 Base 的配置边界观察；框架没有为了制造 Base FAIL 而要求 Gold-only `FontFamilies.from_str`。其余四条为 Base FAIL/Gold PASS。

## 5. 修改范围

主要修改文件：

- `prompts/converter.md`
- `prompts/judges/semantic.md`
- `src/swepro_trans/agents/runner.py`
- `src/swepro_trans/agents/judge.py`
- `src/swepro_trans/agents/mini_swe_session.py`
- `src/swepro_trans/model_clients/openai_compatible.py`
- `src/swepro_trans/pipeline/orchestrator.py`
- `src/swepro_trans/pipeline/repair.py`
- `src/swepro_trans/validation/semantic.py`
- `src/swepro_trans/validation/revision.py`
- `src/swepro_trans/validation/stability.py`
- `src/swepro_trans/validation/final_audit.py`
- `src/swepro_trans/qa/replay.py`
- `src/swepro_trans/layout.py`
- `configs/experiment.yaml`

## 6. 验证

- `python3 -m compileall -q src/swepro_trans`：通过；
- Element rev_009 full pipeline：通过；
- 五条任务 strict final audit：通过；
- 每个 accepted attempt 的 `review/final_audit.json` 已写入；
- 所有共享规则都按 capability 实现，没有按 instance id、repo、commit、具体测试名或任务特有路径硬编码。

## 7. 残余限制

- LLM endpoint 的单次生成仍可能慢；框架保留 timeout、有限重试、trajectory 和 artifact takeover，但不会把无响应当成语义成功；
- 对“公共边界”的最终判断仍包含 LLM 语义审计，因此必须与 deterministic Base presence、Docker replay 和正负 QA 联合使用；
- historical test patch 的 apply/reverse 依赖 patch 可干净应用，失败会被 hard replay 或 repo-clean gate 拦截；
- `archived/` 仅在 final 被安全重建时出现，不属于当前发布任务内容。
