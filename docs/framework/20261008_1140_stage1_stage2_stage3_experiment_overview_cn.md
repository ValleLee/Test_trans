# SWE-bench Pro OS v2：实验目标、三阶段框架与首轮结果

> 2026-10-08 11:40 CST 快照。本文可独立阅读；以仓库当前代码、配置及冻结结果为准。Stage 1/2 的批量转换与修复目前暂停，本文没有重新运行它们。Stage 3 首轮 20 任务实验已经完成，统计使用冻结补丁和统一交叉复判结果。

## 1. 实验要回答什么

官方任务给 solver 的 instruction 包含问题描述（下称 P）、Requirements（R）和 New Interfaces（I）；历史 verifier 由 fail_to_pass（F2P）和 pass_to_pass（P2P）测试构成。R/I 或历史测试可能固定某个实现路径、接口、文案或内部结构，使满足 P 的其他实现被拒绝。本实验尝试把历史 F2P 转成基于公共可观察行为的 functional verifier，并比较两种 instruction 和两套 verifier 对模型补丁的影响。

研究问题有两个层次：**生成条件**——移除 R/I 后，同一模型与 agent 会生成什么补丁；**判定条件**——对同一份补丁，原始 verifier 与 functional verifier 为何给出不同结果。预期的“旧测试拒绝、新测试接受”只是待审查现象，不能直接等同正确解增加；“旧测试接受、新测试拒绝”也不能自动认定新测试有错。补丁语义、P 依据和测试覆盖范围必须逐例核查。

本框架的基本边界是：P 为基础规范；R/I、Gold、历史测试、仓库与环境是转换时理解行为的证据，不能单独变成新正确性要求。转换范围由历史 F2P 限定，原始 P2P selector 字符串和顺序保留。历史 F2P 中若确有 P 遗漏的重要产品行为，控制器可生成经门禁检查的行为级 addendum，进入最终 instruction；这类任务在 Stage 3 中与“仅删 R/I”分层报告。新 verifier 旨在检验其重述的历史行为，实际实现仍可能误收、误拒或改变覆盖深度，需由 QA 和交叉实验检验。

### 1.1 总体 Pipeline

~~~text
┌──────────────────────────────────────────────────────────────┐
│ 官方 SWE-bench Pro OS v2：数据行 + Harbor 任务 + 官方镜像  │
└─────────────────────────────┬────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 1  数据准备                                            │
│ 选样 → 固定来源/镜像 → 原始 Base FAIL、Gold PASS → 总审计    │
│ 输出：original/、P-only source、READY（100/100）             │
└─────────────────────────────┬────────────────────────────────┘
                              │ READY
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 2  功能 verifier 转换                                 │
│ 历史 F2P 逐条追踪 → 公共行为测试；原始 P2P 原样保留         │
│ 多轮 revision：结构/语义/回放/稳定性/正负 QA → 打包与复审   │
│ 输出：final/ + 合格清单（本轮 20 项）                        │
└─────────────────────────────┬────────────────────────────────┘
                              │ 冻结原始/转换后任务及 attempt
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 3  比较实验                                           │
│ 原 instruction → patch O ─┬─ 旧、新 verifier                │
│ 新 instruction → patch F ─┴─ 旧、新 verifier                │
│ 每份同一 patch 双复判 → 四格矩阵 → 逐条语义审查             │
│ 输出：冻结结果、解释边界、返回 Stage 2 的缺陷证据          │
└──────────────────────────────────────────────────────────────┘
~~~

## 2. Stage 1：固定官方任务和可执行 oracle

**方法。** 从官方 V2 数据行选样，固定上游 commit，把原 Harbor task 复制到不可变的任务目录；记录数据行、任务树与镜像来源。使用官方任务镜像和原始 tests/test.sh，对未打补丁的 Base 与应用原始 Gold patch 的 Gold 分别重放。只有 **Base FAIL、Gold PASS** 才能证明原始 verifier 对该任务有基本区分力；失败实例替换后重新执行审计。此处是本地 Docker 重放官方脚本，不等同于 Stage 3 的完整 Harbor solver rollout。

### 2.1 Pipeline

~~~text
官方 V2 数据行 + 任务来源 commit + 语言/HARD 配额
                         │
                         ▼
               ① SELECT [SCRIPT]
               保留 pilot、选满 100 项并记录理由
                         │
                         ▼
               ② PREPARE [SCRIPT]
               稀疏检出 v2/tasks/<id>
               冻结 tasks/<id>/original/
               保存数据行/任务树 hash 与 P-only source
                         │
                         ▼
               ③ IMAGE [DOCKER]
               复用或拉取官方任务镜像，记录 digest
                         │
                         ▼
               ④ ORIGINAL ORACLE [DOCKER]
               同一原始 tests/test.sh 分别回放
                   ┌─────┴─────┐
                   ▼           ▼
                 Base         Gold
              不打补丁     打原 Gold patch
              必须 FAIL      必须 PASS
                   └─────┬─────┘
                         │
             未满足 ──────┴─────→ 记 rejected ID
                         │        → 补选、准备与预检
                     全部满足
                         ▼
               ⑤ FINAL AUDIT [SCRIPT]
               100 个唯一 ID；配额/任务集合；
               来源 hash、镜像 digest、Base/Gold 结果
                   │                 │
                 FAIL              PASS
                   │                 │
                   └→ 修复/替换     ▼
                              STAGE 1 READY
                              original/ + source + preflight
~~~

**当前结果。** [总审计](../../data/stage1/final_100_report.json)为 READY，100/100 个任务满足门禁；选样配额为 Python 40、Go 36、JavaScript 22、TypeScript 2。官方任务来源固定在 [准备脚本](../../dataprepare/prepare_swebench_pro_v2.py)所用 commit `66f92766bba642462d4bbe5479e83f91f9211862`。100 个 READY 是 Stage 1 的可进入数量，**不是** Stage 2 合格包数量。

**核心实现。** [选样](../../task_list/select_v2_100.py)、[镜像准备](../../dataprepare/pull_selected_images.py)、[Base/Gold 预检](../../dataprepare/preflight_selected.py)、[全量审计](../../dataprepare/audit_stage1.py)。输入与输出分别位于 `tasks/<id>/original/`、`data/stage1/<id>/source/`、`data/stage1/<id>/preflight/`；Stage 2 初始化后，共享 source 被移到 `runs/<id>/source/`，original 保持不变。

## 3. Stage 2：把历史测试转换为功能判定

**转换逻辑。** 转换器读取 P 以及作为证据的 R/I、原 F2P/P2P、Gold、Base 仓库。它对每个历史 F2P selector 在 conversion_trace.json 中说明原断言、行为义务、P 依据、公共观察面和去向。P 支持的行为改写/合并为 functional delta；Base 已满足的产品行为可转为回归测试；P 遗漏的重要历史产品行为先提出 specification gap，由控制器审核并形成行为级 addendum，再要求新 revision 落实测试；没有独立产品行为的实现细节可有证据地丢弃。不得借此给原 F2P 未覆盖的 P 条款补测。原始 P2P 保持原 selector 与顺序，追加的 converted regression 与其区分。

[控制器](../../src/swepro_trans/pipeline/orchestrator.py)对一个 attempt 的 revision 按以下顺序执行；可修复失败形成反馈并创建新 revision，终态 attempt 不原地改写。

### 3.1 Pipeline

~~~text
STAGE 1 READY：P / R / I / F2P / P2P / Gold / Repo / Env
                              │
                              ▼
                  ① INIT → attempt_NNN
                  original/ 不变；source 固定
                              │
                              ▼
             ┌────── Converter revision loop ──────┐
             │                                      │
             ▼                                      │
  ② FUNCTIONAL CONVERTER [mini-swe-agent]           │
     P 为基础规范；R/I/Gold/原测试等仅作构造证据     │
     逐条 F2P：原意 → P 依据 → 公共可观察行为        │
     识别实现绑定；保留原始 P2P selector 与顺序     │
     提交测试、conversion_trace、自审、manifest     │
             │                                      │
             ▼                                      │
  ③ ARTIFACT CONTRACT [SCRIPT]                     │
     文件/schema、F2P accounting、P2P 不删改        │
     P 遗漏重要历史行为？→ 行为级 addendum           │
                           → 新 revision ──────────┤
             │ PASS                                 │
             ▼                                      │
  ④ SEMANTIC REVIEW [Judge + deterministic checks] │
     P 支持、可观察效果、Gold/私有接口绑定          │
             │ PASS                                 │
             ▼                                      │
  ⑤ HARD REPLAY [DOCKER]                           │
     Base + 新 tests → FAIL                         │
     原始 Gold + 新 tests → PASS                    │
     原 test_patch 仅在临时容器准备 P2P              │
             │ PASS                                 │
             ▼                                      │
  ⑥ BEHAVIOR ROLE AUDIT [SCRIPT]                    │
     functional delta 在 Base FAIL                  │
     converted regression 在 Base PASS              │
             │ PASS                                 │
             ▼                                      │
  ⑦ STABILITY [DOCKER]                             │
     至少两轮 Base/Gold；逐条原始 P2P 均 PASS       │
     Base/Gold 均 PASS → non-discriminative          │
                         → 不发布 final/            │
             │ convertible + PASS                   │
             ▼                                      │
  ⑧ POSITIVE QA [mini session → fresh Judge]        │
     不同于 Gold 且满足 P 的解                       │
     原 verifier PASS/FAIL 只记录                   │
     新 verifier 必须 PASS                          │
             │ PASS                                 │
             ▼                                      │
  ⑨ NEGATIVE QA [mini session → fresh Judge]        │
     相关、非等价、违反 P 的 near-correct mutant    │
     新 verifier 必须 FAIL                          │
             │ PASS                                 │
             ▼                                      │
  ⑩ ACCEPTANCE [SCRIPT]：同一 revision 门禁齐全   │
             │ PASS                                 │
             ▼                                      │
  ⑪ PACKAGE FINAL [SCRIPT]                         │
     原 task/env/solution + 新 tests                │
     P-only instruction + 可选已审计 addendum       │
             │ PASS                                 │
             ▼                                      │
     final audit + 框架外 independent audit         │
             │ 两者 PASS、原 P2P 排除数 = 0         │
             ▼                                      │
     check/qualified_tasks.txt                     │
                                                    │
  ③—⑪可修复 FAIL → 结构化反馈 → REPAIR rev_NNN+1 ─┘
  框架外复审 FAIL → 挂起该包，保留证据，不自动重转
~~~

正向 QA 完成后才运行负向 QA；它们不是并行分支。

hard replay 的原始 test patch 只进入临时回放容器，使历史 P2P 源码可运行，不打包进新的 tests。Gold PASS 是**一个**兼容性门禁，不推出所有旧 verifier 能过的补丁都能过新 verifier。positive QA 的原始 verifier 结果仅作对照；可接受条件是 Judge 判定 P-valid 且新 verifier PASS。当前配置目标为 1 个有效正解和 1 个相关 mutant，上限分别为 3、5 次尝试，找到首个合格样本即可停止。因此 QA 能发现部分缺陷，不能穷举所有正确实现路线。

正式 `final/` 保留原 task.toml、environment、solution，替换 instruction 和 tests；instruction 为移除 R/I 的 P 文本，可附经过门禁的行为级 addendum。自动 accepted/package 只是框架内部完成。进入 [合格清单](../../check/qualified_tasks.txt)还需包完整、final audit PASS、框架外 independent audit PASS、原始 P2P 排除数为 0，并核查 F2P 转换与 instruction。当前合格清单为 **20 个任务：Python 19、TypeScript 1**，均记录明确 attempt；并不表示 100 个 Stage 1 任务都完成转换。

**当前发现的门禁边界。** [框架外复审记录](20261008_1038_external_review_findings_and_framework_questions_cn.md)已将四个自动 accepted 但语义不合格的包挂起、排除在合格清单外：精确警告次数和私有调用绑定、固定 repr 形状、无效 LCCN 结果欠检、Gold-only 私有 `_build_doc` 接口被误认为 P 要求。记录提出的是框架改进方向，当前代码尚未落实这些修复；不能把自动 accepted 视为独立语义证明。

## 4. Stage 3：两组生成、同一补丁双 verifier 复判

**设计。** 从合格清单冻结 20 个 instance 及其 accepted attempt。每个任务只做两次 solver rollout：一次读 original/instruction.md，一次读所选 `final/instruction.md`；模型、Harbor、mini-swe-agent、任务镜像、Base 仓库和 agent 设置保持一致。两组产生的是**不同补丁**，不能作为“同一补丁更换 instruction”的因果实验；而对**每份同一补丁**先后运行旧、新 verifier，构成配对判定。17 个任务仅删 R/I，3 个还含行为级澄清，统计分层展示。

### 4.1 Pipeline

~~~text
合格清单：20 个 instance + 明确的 accepted attempt
                         │
                         ▼
              ① PREPARE / FREEZE [SCRIPT]
              核验 original/、final/、accepted 证据
              固定 instruction、tests、任务/镜像 hash
              固定 Harbor、agent、模型与运行参数
                         │
                         ▼
          ② SOLVER ROLLOUT [同一 Harbor/agent/LLM]
                 ┌───────┴───────┐
                 ▼               ▼
       原始 instruction     转换 instruction
       (P + R + I)          (P + 可选 addendum)
                 │               │
                 ▼               ▼
              patch O         patch F
                 └───────┬───────┘
                         │ 每任务各 1 份；保存 patch/trajectory
                         ▼
              ③ CROSS-REGRADE [独立干净容器]
              对每份同一 patch 分别执行：
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       原始 verifier                   functional verifier
       原始测试准备规则               同等历史测试空间重置
                 └───────────────┬───────────────┘
                                 │
       patch/test patch 应用失败、超时或基础设施故障
             → 单列无效状态；保留日志，不计语义 FAIL
                                 │ 双有效 verdict
                                 ▼
              ④ PAIRED MATRIX [SCRIPT]
              双 PASS / 仅旧 PASS / 仅新 PASS / 双 FAIL
              原始、转换 instruction 分组并单列 addendum
                                 │
                                 ▼
              ⑤ SEMANTIC REVIEW [逐补丁]
              核查不一致 verdict 的 P 依据、补丁、
              测试日志及公共行为；标记覆盖扩大/误收/误拒
                                 │
                                 ▼
              ⑥ AGGREGATE / FREEZE
              check/stage3/<experiment_id>/manifest、
              patches、logs、aggregate、report
                                 │
                       若发现 verifier defect
                                 ▼
              作为 Stage 2 复核证据；修订并重冻后
              另起复评，不改本轮冻结 verdict
~~~

本轮使用 Harbor 0.22.0、mini-swe-agent 2.4.6、`deepseek-v4-pro-Code-PT-SWE-Pro-o-66`，每组每任务 1 次 rollout，最多 10 个任务并发。模型服务端版本未提供，未固定 seed。Harbor shared mode 的 `trial regrade` 不适用于这批任务，交叉复判由项目 Docker replay 执行；它在干净环境中按原始测试空间规则应用历史 test patch，区分补丁应用/基础设施失败与有效测试 FAIL。40/40 次旧 verifier 独立复判与 Harbor 原生 verdict 相同。评测前的基础设施失败和首次复判准备失误已留档；全部 40 份补丁在统一规则下重新复判，冻结原任务、final 测试及候选补丁未改动。执行和统计入口见 [Stage 3 控制器](../../src/swepro_trans/stage3.py)、[聚合分析](../../src/swepro_trans/stage3_analysis.py)、[Docker replay](../../src/swepro_trans/qa/replay.py)与[测试空间重置](../../src/swepro_trans/qa/stage3_p2p_reset.py)。

### 4.2 冻结结果

40/40 次 rollout 正常结束并生成非空补丁，80/80 个旧/新 verifier verdict 有效。以下每行的四格均针对**同一组的同一补丁**配对计算；行间 instruction 比较则涉及各自生成的补丁。

| Instruction | 旧 PASS／新 PASS | 旧 PASS／新 FAIL | 旧 FAIL／新 PASS | 双 FAIL | 旧通过 | 新通过 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 原始，20 份 | 16 | 3 | 1 | 0 | 19/20 | 17/20 |
| 转换后，20 份 | 3 | 0 | 10 | 7 | 3/20 | 13/20 |
| 合计，40 份 | 19 | 3 | 11 | 7 | 22/40 | 30/40 |

仅删 R/I 的 17 个任务：旧 verifier 原始→转换为 16→2，新 verifier 为 15→12。另 3 个含行为澄清任务：旧为 3→1，新为 2→1。一次 rollout、非随机抽取的 20 个任务，只能得出这批样本的描述统计，不能当作稳定的模型成功率或单一因素因果效应。正式 solver 墙钟跨度约 85.5 分钟；原始/转换组分别消耗输入 59,609,625 / 108,441,069 tokens、输出 536,184 / 651,276 tokens（输入量包含缓存命中）。Harbor 的费用字段不可用，不据此估算实际花费。生成结果、哈希、日志和汇总位于 [冻结实验目录](../../check/stage3/deepseek_miniswe_20_20261008/)；机器可读总表是 [aggregate.json](../../check/stage3/deepseek_miniswe_20_20261008/aggregate.json)。

### 4.3 判定不一致的解释

11 份“旧 FAIL／新 PASS”经逐补丁审查，**10 份**有足够 P 层行为证据支持正确；另 1 份 Ansible 转换组补丁错误拒绝合法完整单位名（如 `kilobyte`），新 verifier 漏检，故不能把 11 当作全部“挽救的正确解”。原始 instruction 组唯一旧 FAIL／新 PASS 是 Ansible `human_to_bytes`：补丁拒绝畸形输入，但异常文案不符原 Requirements 中的固定字符串 `Value is not a valid string`；原 instruction 下旧判定成立，删 R/I 后新判定对应保留的 Description。早期机器语义审查将其归因为 selector 不匹配，这一点已由原始 pytest 日志纠正。

3 份“旧 PASS／新 FAIL”中，两份 OpenLibrary 补丁只实现 helper，没有接入作者页或搜索调用路径；新测试发现 P 要求的产品效果缺失。不过新测试从历史 helper 断言延伸到了集成路径，**覆盖深度也增加了**，不能把这两例单纯解释为去除了实现绑定。Qutebrowser 补丁通过启动环境变量向 QtWebEngine 提供 `--lang`，而新测试只检查 `qt_args()` 返回值；独立探针验证了变量设置和既有 flags 保留，尚未验证完整浏览器中语言参数最终生效，语义结论待定。Stage 2 对该任务只接受过 1 份不同于 Gold 的正向 QA 解，且仍走 `qt_args()`；因此当时没有覆盖环境变量路线。

转换组另有 7 份双 FAIL：日志可见的失败包括 Ansible `tty_ify` 输出、OpenLibrary 语言值、Qutebrowser 字体解析等；其中 `sanitize_keys` 导入失败、Wikidata 标签和 locale 回退断言还需进一步区分补丁缺陷与测试绑定。双 FAIL 是两套测试的执行结果，尚非七份补丁全部违反 P 的语义裁定。

Stage 3 暴露的 verifier 疑点应作为 Stage 2 复核证据；若修订测试，须重新通过门禁、冻结 final 并复评相关任务。本轮 80 个冻结 verdict 保持原样。逐项证据与更完整的分析见[落地报告](../stage3/20261008_stage3_two_cohort_cross_verifier_results_cn.md)和[本轮详细分析](../../check/stage3/deepseek_miniswe_20_20261008/20261008_102821_stage3_design_results_analysis_cn.md)。

## 5. 核心 prompt 与可执行机制索引

[当前配置](../../configs/experiment.yaml)决定实际生效的 Stage 2 prompt；下表列出用途，不把 prompt 文本误当硬门禁。转换器另有其他历史/聚焦文件，但未列入当前配置映射的不在此表中。

| 角色 | 生效 prompt | 关键约束 |
| --- | --- | --- |
| F2P 转换器 | [converter.md](../../prompts/converter.md) | 逐条恢复历史行为与 P 依据；公共可观察边界；分清 P 行为、Base 回归、P 缺口和实现细节；反事实自审；保留原 P2P。 |
| 语义 Judge | [semantic.md](../../prompts/judges/semantic.md) | 检查实际测试正文、P 支持、Gold/私有接口绑定、产品效果及遗漏的行为义务。 |
| 正向 QA 生成器 | [positive_generator.md](../../prompts/qa/positive_generator.md) | 构造与 Gold 实质不同、仍满足 P 的可运行实现，改变有风险的设计轴。 |
| 正向 QA Judge | [positive.md](../../prompts/judges/positive.md) | 独立核查 P 正确性、相关路径和实质差异；不能仅凭 verifier PASS 判正确。 |
| 负向 QA 生成器 | [negative_generator.md](../../prompts/qa/negative_generator.md) | 构造接近正确、仅违反相关 P 行为的可运行 mutant。 |
| 负向 QA Judge | [negative.md](../../prompts/judges/negative.md) | 核查明确 P 义务与非等价性，排除无关崩溃或等价变更。 |

| 机制 | 当前实现 | 实际作用 |
| --- | --- | --- |
| F2P accounting 与包结构 | [conversion_schema.py](../../src/swepro_trans/conversion_schema.py)、[revision.py](../../src/swepro_trans/validation/revision.py) | 约束每条历史 selector 的去向、P2P 原样保留、文件与 Base/Gold 回放。 |
| 编排、addendum 与修复 | [orchestrator.py](../../src/swepro_trans/pipeline/orchestrator.py)、[repair.py](../../src/swepro_trans/pipeline/repair.py) | 固定门禁次序；反馈失败；规范缺口形成行为级 addendum 和新 revision。 |
| 语义/行为/稳定性 | [semantic.py](../../src/swepro_trans/validation/semantic.py)、[behavior_roles.py](../../src/swepro_trans/validation/behavior_roles.py)、[stability.py](../../src/swepro_trans/validation/stability.py) | 判定 P 依据、Base/Gold 行为角色、重复回放与 P2P 状态。 |
| 正反 QA 与验收 | [QA runner](../../src/swepro_trans/qa/runner.py)、[acceptance.py](../../src/swepro_trans/validation/acceptance.py) | Judge 和 verifier 双条件，核对同一 revision 的门禁。 |
| 发布与合格审核 | [layout.py](../../src/swepro_trans/layout.py)、[final_audit.py](../../src/swepro_trans/validation/final_audit.py) | 写正式 Harbor 包、检查审计证据；框架外 independent audit 由外部流程生成。 |

证据阅读顺序：先看 [Stage 1 总审计](../../data/stage1/final_100_report.json)和[合格清单](../../check/qualified_tasks.txt)，再顺着一个明确 attempt 的 `source/ → revisions/ → validation/ → qa/ → final/ → review/`，最后看 Stage 3 的 [manifest](../../check/stage3/deepseek_miniswe_20_20261008/manifest.json)、[aggregate](../../check/stage3/deepseek_miniswe_20_20261008/aggregate.json)、逐实例 patch 与复判日志。旧设计文档可解释动机；当文档与实现或冻结证据不一致时，以本节所列代码及本轮冻结记录为准。
