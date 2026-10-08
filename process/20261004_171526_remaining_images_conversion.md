# 已下载镜像任务的逐条转换与审计

时间：2026-10-04 17:15 UTC

## 范围与验收

按 `docs/optimize_rule.md`，对已下载且 Stage 1 READY 的其余任务逐条运行当前 Stage 2：逐条 F2P 行为记账、Semantic Judge、Base/Gold 和 P2P 回放、稳定性、正负 QA、打包和 final audit。每条任务还要审阅最终 instruction 是否只加入必要功能语义，测试是否能容纳不同正确实现。只修复有跨任务意义的共享框架缺陷。

镜像盘点：qutebrowser 已在 `attempt_020` 完成；仍待转换的 READY 任务是两条 Open Library（原始 F2P 分别为 1、6 条）、Element Web（10 条）和 Tutanota（2 条）。Navidrome 镜像存在，但 Stage 1 因发布镜像缺少 Go runtime 被拒绝，不能进入 Stage 2。

## 旧 source 归档造成的入口缺失

- 现象：Open Library 的 Stage 2 `init` 提示规范 `runs/<id>/source` 与 `data/stage1/<id>/source` 都不存在。
- 证据：四条待转换任务的 Stage 1 source 全部保存在 `runs/old2/<id>/source`，包含 problem statement、provenance、R/I 与数据行；当前 `tasks/<id>/original` 和阶段一 Oracle 通过记录仍在。
- 分类：本次目录归档迁移造成的基础设施数据位置问题。`init` 的规范路径契约正确，不把 `runs/old2` 硬编码进共享框架。
- 处理：对四条任务核对 `provenance.instance_id`，将旧 source 快照复制回规范 `data/stage1/<id>/source`，逐文件 SHA-256 与归档相同。`init` 再将所选任务的 source 提升到当前 `runs/<id>/source`；旧归档和原始任务未改。
- 验证：Open Library 0dc5… 已成功初始化 `attempt_001`。
- 残余风险：其余三条尚未初始化和转换；恢复的 source 快照必须继续与各任务的 Stage 1 READY 记录核对。

## 转换顺序

1. Open Library 0dc5…（6 条 F2P，55 条 P2P）
2. Open Library 7232…（1 条 F2P）
3. Element Web 776f…（10 条 F2P，39 条 P2P）
4. Tutanota de49…（2 条 F2P）

每条任务的 gate 结果、审计发现与通用框架修改继续追加在本文。

## Converter 检查点阻塞（Open Library 0dc5…，2026-10-04 17:32 UTC）

- 现象：框架启动 mini-swe-agent 并调用配置的 DeepSeek API 后，代理已执行 13 次有效探索操作；第 12 次以后的证据读取被 `[CONTROLLER ARTIFACT CHECKPOINT]` 以 returncode 2 拒绝。主会话及自动协议重试都在该点出现连续无 bash tool call 响应，终止为 `RepeatedFormatError`。rev_001 只有会话报告，没有测试产物。
- 根因：共享 `MiniSWEEnvironment.execute` 对所有任务固定在第 12 次操作后要求八类产物和全部 F2P 行一次写齐。这个条件早于复杂任务读完证据，并且直接拒绝工具读取；这类检查点与任务具体 ID、语言、仓库无关。API 仍成功返回过有效工具调用，现有证据不足以认定是 endpoint 故障。
- 通用修复：保留缺失产物提示，但允许原本的证据读取执行并在工具结果后附加提醒。正式产物的完整性、语义和 Docker 回放门槛保持原状，缺失产物仍不能通过提交。
- 验证：`tests/test_converter_checkpoint.py` 模拟第 12 步、缺失所有骨架文件时的证据读取，确认命令实际执行、returncode 为 0、提醒列出缺失文件；`1 passed`。修正后重新用框架调用 DeepSeek 转换同一 revision，结果待记录。

## Converter 缺少早期正式产物（2026-10-04 17:53 UTC）

- 现象：去除第 12 步硬阻塞后的同一任务转换会话持续有效读取 Base、Gold、历史测试和本地 pytest，但直到步数上限仍未写出任一正式 verifier 文件，以 `LimitsExceeded` 结束。说明前一修复解除死锁，但单靠提醒不足以让模型在预算内完成八类产物和 F2P 账本。
- 根因：框架把可确定的历史 F2P selector 盘点也交给生成代理，在复杂任务里代理先做大量探索，迟迟没有可增量编辑的正式结构。它并非 Open Library 专属：每个 Harbor 任务的历史 selector 都可由原 `tests/config.json` 机械取得，语义内容则必须由代理完成。
- 通用修复：在空 revision 启动前仅预填 `conversion_trace.json` 的全部历史 selector 和未解决占位值；不覆盖已有 trace，不自动生成行为分类、测试或 instruction。未解决字段仍被语义/最终化门槛拒绝。代理任务提示改为填写预置账本、尽早写测试文件。
- 验证：`tests/test_converter_checkpoint.py` 新增验证 selector 数量与顺序、必需字段结构、占位值会被拒绝以及不覆盖已有文件；与检查点测试合计 `2 passed`。改良版重新调用 DeepSeek 的结果待记录。

## Docker 孤儿容器导致启动超时（2026-10-04 17:58 UTC）

- 现象：预填账本后的新 Converter 在 `docker run -d` 上等待满 180 秒，尚未向 DeepSeek 发送有效转换会话请求即失败。
- 证据：Docker 当时共运行 59 个容器，其中 39 个 `mini-swe-*` 容器挂载本项目路径，启动于数小时至数天前；宿主机没有对应的活跃 `swepro_trans` 或 `docker exec` 进程。另 3 个旧项目容器不属于本项目。
- 处理：只移除 39 个无活跃进程且挂载本项目的孤儿容器；`docker rm -f` 返回 0，清理后只剩 3 个旧项目 `mini-swe-*` 容器。没有删除任务文件或 revision。
- 结论：这次 180 秒等待是 Docker 启动超时，不是 DeepSeek API 慢。当前框架的容器清理是尽力而为，异常退出仍可能遗留容器；后续若再次出现，应设计有所有权标识的孤儿回收，而非删除其他项目容器。

## Open Library 0dc5…：语义门槛识别 Gold helper 绑定（2026-10-04 18:19 UTC）

- 改良框架生成 rev_001 的 6 条 F2P 账本、Harbor verifier 与自审。初次提交的两个布尔字段被写成说明文字，`artifact_contract` 以 12 条类型错误拒绝；pipeline 自动复制到 rev_002，向 mini-swe/DeepSeek 反馈后在 8 次模型调用内修复并提交。
- rev_002 Semantic Judge 给出 `FAIL`：4 条历史 `name_from_list` 测试仍直接调用 Gold 引入的 helper，而 Problem Statement 只规定通过 MARC 880 linkage 导入作者 alternate-script names，没有规定该 helper 名称或标点归一化细节。Judge 要求从公开 `read_edition` 等产品输出改写可保留的行为，或对确实只属实现细节的断言给出证据。
- 独立审计与 Judge 结论一致；目前没有手工修改任务测试。下一轮由框架自动将语义反馈交给 mini-swe 修复。

## Open Library 0dc5…：rev_003 Judge 通过但 Gold 回放失败（2026-10-04 18:28 UTC）

- rev_003 的首轮 Judge 因模型没有输出闭合 JSON 被归类为 `judge_transport`，pipeline 对同一 revision 重试，不把协议故障当作 Converter 语义缺陷。重试得到 `PASS`：四条历史 helper 行改为通过 `read_edition` 的 Base 既有行为回归测试。
- 随后 Docker 硬回放：Base 6 个新 selector 失败、55 个保留 P2P 通过；Gold 仅 57/61 通过，四条归一化用例失败。traceback 指向代理构造的 `MarcXml` 缺少 `get_linkage`，导致 `read_edition` 的 Gold 路径抛 `AttributeError`。
- 判定：这是生成 verifier 的输入构造/运行缺陷；不能因 Judge PASS 发布。pipeline 已将 hard replay 证据交给 rev_004 mini-swe 修复；仍不手工改测试。

## Open Library 0dc5…：rev_004 硬门槛通过，QA 进行中（2026-10-04 18:48 UTC）

- rev_004 的 Semantic Judge 为 `PASS`；Docker hard replay 为 `pass`：Base 61 个必需 selector 中 59 个通过、两条 alternate-script 功能增量失败；Gold 61/61 通过。稳定性报告为 `pass`。正向 QA 已启动，负向 QA 尚待执行。
- 独立检查生成测试：两条功能增量由 `read_edition(MarcBinary(...))` 的 `authors[*].alternate_names` 观察；四条原 helper 断言改从既有 `read_edition(MarcXml(...))["authors"][0]["name"]` 观察，并归入 Base 已满足的回归 selector。最终测试未直接调用 Gold-only `name_from_list`。测试仍包含具体 fixture 的预期值，需要正向 QA 证明不同正确实现可通过。
- 暂不认定完成：正向不同解、负向近似错误解以及最终 instruction/package 尚未通过。P 提及 100/700/720 三种字段，目前转换的历史 fixture 直接覆盖 700；该覆盖边界需在最终审计中如实记录，不因说明文档声称三个字段就算已测试。

## Open Library 0dc5…：rev_004 转换完成（2026-10-04 18:57 UTC）

- 框架流水线状态 `complete`，rev_004 已被接受并打包到 `attempt_001/final`；没有手工编写或修改该任务的 verifier。
- 正向 QA：独立 Judge 判定候选为不同的正确实现，原 verifier 失败，新 verifier 通过。负向 QA：独立 Judge 判定候选确实违反 P 的行为，功能性 verifier 拒绝。
- `final-audit --write` 为 `PASS`：历史 6 条 F2P 全部记账；2 条功能增量、4 条通过 Base 公开行为保存为回归；原 55 条 P2P 全部保留。语义、硬回放、稳定性、正负 QA、instruction 泄漏检查全部通过。
- 最终 instruction 与原 P 一致，没有附加 R/I 或 Gold helper 的实现要求。覆盖边界仍是：当前功能增量 fixture 直接测试 700 字段，P 还提及 100 和 720；不能声称已完整覆盖 P 的所有例子。
- 过程教训：Converter 初稿违反 P/R/I 优先级，独立 Judge 在 rev_002 捕获；prompt 中已有该规则，但 376 行长提示、多产物生成与探索工作易稀释优先级。先在后续任务观察是否重现，再做跨任务的前置自审改良；不能仅据一例认为替换 Judge 提示词就足够。

## 第二条 Open Library：构造器源证据误用与静态探针误报（2026-10-04 19:12 UTC）

- `723212…` 的 rev_001 由 mini-swe/DeepSeek 自动生成，直接要求 `luqum_replace_field`。P 只要求搜索查询中的 `work.` 字段正确解析，没有命名该函数；函数名来自 R/I/历史测试。rev_002 独立语义 Judge 明确拒绝这个隐藏 API 契约，pipeline 已进入自动修复。与前一条 Open Library 一样，说明 Converter 虽然读到既有的 P 优先规则，仍会在构造测试时继承旧测试的具体入口。
- rev_001 还被 Gold-only 静态预检错误标记 `field.partition`：这里的 `field` 是测试本地 `str` 参数，`partition` 是普通字符串方法，只因 Gold 补丁中也使用同样表达式就被认作新增 API。根因是预检把 Gold 新增行里的任意使用表达式当作声明证据。通用修复改为只匹配 Gold 真正新增的类/函数声明，其他情况交给独立语义 Judge；`tests/test_semantic_evidence.py` 的 6 项测试通过。已运行的 pipeline 进程使用启动时加载的旧模块，因此本轮结果仍须按旧门槛解读；下一次新进程才应用修复。
- `prompts/converter.md` 在最前面加入“先找 F2P 产品行为、P 原文支持和拟断言符号的来源，再写测试”的简短核对，明确 P 未命名 API 时从现有产品边界验证行为，并要求提交前自审。此修改对后续新建 mini-swe 会话生效；当前 rev_003 的 prompt 在会话开始时已固定。

## 第二条 Open Library：混合义务角色与 runner 路径（2026-10-04 19:32 UTC）

- rev_003 改用原仓库已有的 `WorkSearchScheme.q_to_solr_params` 检查 `workQuery`，不再要求 Gold-only helper；独立语义 Judge 未再报隐藏函数名。它随后反复拒绝一项 Base 已有行为被列为 F2P。
- 根因是共享 `converted_selector_groups` 只读取整条 historical F2P 的 `base_behavior_status`，却允许该行的 `obligation_accounting` 分别写 `changed_or_missing` 与 `already_satisfies`。一条历史测试混合增量和回归时，提交端每次都会把所有生成 selector 写进 F2P，导致 agent 无法单独修复。已改成逐义务派生，并让 Docker `behavior_roles` 对每个 selector 独立验证 Base/Gold 状态；16 项相关测试通过。
- 用修正框架重提交 rev_005 后，自动生成 3 个 F2P 和 1 个 converted P2P；Semantic Judge 通过。Docker 回放显示 Base 3 失败/1 通过，Gold 4 通过，但 pytest 报告名 `../tmp/...` 与 config 的 `/tmp/...` 不一致，导致 Gold 被误判缺失。pipeline 已交给 mini-swe 进行 rev_006 runner 修复；仍需验证。

## 第二条 Open Library：rev_007 转换完成（2026-10-04 19:47 UTC）

- mini-swe/DeepSeek 在 rev_006 修正 pytest `../tmp/...` 与 config `/tmp/...` 的 selector 不一致；该轮语义和 Base/Gold 回放均通过。后续行为角色审计又因只识别 `output.json` / `parsed_results.json`，没有读取 Harbor parser 的 `results.json` 而误报全部 selector 缺失。共享审计器已补充该文件名，相关 17 项测试通过。rev_007 同时输出可被原审计器读取的 `output.json`，新流水线完整通过。
- rev_007 正向 QA：独立 Judge 认可不同于 Gold 的正确实现，新 verifier 接受；负向 QA：独立 Judge 认可行为缺陷，新 verifier 拒绝。pipeline `complete`，自动打包到 `attempt_001/final`。
- `final-audit --write` 为 `PASS`：原 1 条 F2P 全部记账，生成 3 个 Base-fail/Gold-pass 功能增量 selector 和 1 个 Base/Gold 均通过的 converted regression selector；语义、硬回放、角色审计、稳定性及正负 QA 全通过。最终 instruction 与原 P 一致，未加入 `luqum_replace_field` 等 R/I 具体接口。

## Element：预置账本与强制检查点造成的失败重试（2026-10-04 19:57 UTC）

- 第一轮 `attempt_001`：`agent` 把预置 `conversion_trace.json` 视为部分已有产物，采用 50 步补全模式；初次 50 步及自动补全 50 步都只做仓库探索，没有正式 verifier，退出 `converter_failed`。根因是初始化前置 inventory 与会话模式判断冲突；已让纯预置账本不触发短补全模式，并用测试覆盖。
- 重启旧 revision 又受到第 40 步的 `CONTROLLER FINALIZATION CHECKPOINT` 硬拒绝证据读取，代理反复收到 returncode 2 并写占位文件。该硬拒绝会使需要大量 JS 证据的任务无法正常完成；已改为执行原命令并附加提醒，提交时 artifact/语义/Docker 门槛仍保留，4 项检查点测试通过。
- 旧 revision 被失败会话部分改写后，短模式判断仍适用，因此保留 `attempt_001` 作为失败证据，并以 `init` 创建干净 `attempt_002`。用 `--config configs/agent.yaml` 启动的 mini-swe 轨迹确认 `step_limit=160`，后续结果待记录。

## Element：长提示造成重复探索（2026-10-04 20:10 UTC）

- 干净 `attempt_002` 使用 160 步会话和软最终化提醒，证据读取不再被第 40 步拦截；但到 95 次调用仍只有预置 `conversion_trace.json`，轨迹重复读取同一补丁并猜测不存在的 `evidence/test_patch.patch` 路径。继续放宽预算不能解决产物优先级与路径不明。该会话已中断，保留轨迹。
- 通用任务提示现在给出实际挂载路径：`evidence/problem_statement.md`、`evidence/historical_tests/config.json`、`evidence/historical_tests/test_patch.patch`、`evidence/gold_patch.diff`、R/I；直接列出当前 F2P selector，要求先做必要的 Base 入口检查、写可迭代的 `solution/tests/` 草稿并填写账本，再做扩展探索。移除了固定“ten-row”措辞，逐义务角色说明同步于 schema。框架相关测试 21/21 通过。
- `attempt_003` 用同一 mini-swe/DeepSeek endpoint、160 步配置验证新提示的效果；未手工写入任务测试，结果待记录。

## Element：聚焦提示对照实验（2026-10-04 20:45 UTC）

- `attempt_004` 采用原 376 行 Converter 提示与长动态任务，虽然预置了原 Harbor parser/runner/config、给足 160 步，到 128 次 API 调用仍没有 `test.sh` 或任何功能测试源，只有机械预置文件。已停止并保留轨迹；此前数次同类失败说明增大预算和复制外壳不能单独解决产物优先级。
- 新增通用 `prompts/converter_focused.md` 和 `configs/focused_converter.yaml`：保留 P 规范、R/I/Gold 证据、四类 F2P 判断、逐义务角色、公开观测面和所有最终门槛，但把首要交付明确为可运行测试，再补 trace/自审。runner 的聚焦模式使用短任务说明，不再叠加原长动态任务；仍调用同一 mini-swe/DeepSeek。框架相关测试 22/22 通过。
- `attempt_005` 为独立对照，使用聚焦配置；不手工写任务 verifier，结果待观察。

## Element：聚焦提示实验暴露 Docker 临时路径误拦截（2026-10-05）

- `attempt_005` 的 mini-swe/DeepSeek 轨迹到约 57 次调用仍未生成正式测试。直接证据是构造器试运行 Jest 时使用容器内 `/tmp`，`run_bash` 的通用词法检查将合法 `/tmp` 当成不允许的宿主绝对路径，甚至拒绝 `echo /tmp/foo`。模型之后多次探查工具边界，耗掉转换预算。会话被中断，未把该尝试发布为最终任务。
- 根因属于跨语言基础设施：JavaScript/Jest 和其他测试 runner 常把临时配置、日志及生成测试放在容器内 `/tmp`。修复仅在 Docker 命令检查前把已知容器挂载路径及容器本地 `/tmp` 映射成相对词法形式，真正执行的命令不变；其他绝对路径和 `..` 继续拒绝。相关测试 23/23 通过，含 `/tmp` 准入及 `/etc`、父目录穿越拒绝。
- 已用 `init` 创建干净 `attempt_006`，准备在同一 Element 任务上复验聚焦提示；调用被自动审批拒绝，理由是向 DeepSeek endpoint 发送这份具体 Element 任务和仓库上下文缺少明确授权。没有绕过审批，`attempt_006` 尚未开始真实转换。需要用户明确批准该具体发送后才可继续。
- 因此目前能确认路径检查缺陷与通用修复，不能声称聚焦提示已改善最终转换质量；独立语义 Judge 仍保留为候选稿的外部校验门槛。

## 两条已完成 OpenLibrary 的补充人工审计（2026-10-04 21:07 UTC）

- 对照原始 Harbor `tests/config.json`、最终 instruction、接受 revision 的 `conversion_trace.json` 和实际测试代码。0dc5… 原 6 条 F2P 全部有一对一行为账本与独立 emitted selector，6 条均为 rewrite；最终 2 个 Base-fail/Gold-pass 增量 selector、4 个 Base/Gold-pass 转换回归 selector，原 55 个 P2P 仍在 config。723212… 原 1 条 F2P 被拆为 4 个公开搜索边界测试：3 个增量、1 个回归，无 drop。两条最终 PR 正文相对原 instruction 仅删 R/I 部分，外围约束保留；语义、硬回放、正负 QA 均为 PASS。
- 0dc5… 测试通过 `read_edition(MarcBinary/MarcXml)` 返回的作者数据验证 alternate-script 名称及既有名称归一化；723212… 从 Base 已有 `WorkSearchScheme.q_to_solr_params` 的 `workQuery` 输出验证 `work.` 字段处理。未发现要求 Gold-only helper 名称的断言。正向 QA 各有一个不同实现通过，能提供有限的多解兼容证据；不据此宣称对所有正确实现都完备。
- 限制：0dc5… 的直接 F2P fixture 主要覆盖 700 作者，不覆盖 P 文本中的全部 100/720 情形；按规则 historical F2P 定义转换范围，不应凭此补加无 seed 测试。该任务的 `run_script.sh` 在仓库可写时临时复制测试源进 repo，并在退出时清理；`test.sh` 还删除 `__pycache__`、`.pyc` 和 `.git/index.lock`。这属于该最终 verifier 的运行副作用风险，非功能绑定证据。目前仅见该任务采用此复制方式，不据此修改通用框架；后续若需要修复应由 Converter 生成新的 revision 并重过全部 gate。
- 路径误拦截的完整 framework issue 记录见 `process/20261004_210701_docker_tmp_path_validation.md`。

## Tutanota 下一任务的本地预检（2026-10-04 21:07 UTC）

- 只读核查 `data/stage1/<id>/preflight/report.json`：`preflight.status=pass`、`structural.status=pass`；原 Harbor task 有 2 条 historical F2P、0 条 P2P。题面描述 Linux/GNOME 已保存凭据因密钥链材料不匹配而无法解密，应用未识别该失败，导致未处理异常和无法重新登录；R 进一步给出两个具体异常类传播要求。后续 Converter 应以题面用户可见的失效凭据处理为准，审慎判断这些异常类是否有 Base 公共契约依据，不能仅从 R 把类名当成唯一答案。
- 目前未调用 DeepSeek、未生成 Tutanota verifier。Element 的外发审批阻断未解决，保持单任务转换顺序，不并发启动此任务。

## Element attempt_006：授权后真实 Converter 运行（2026-10-05）

- 用户明确允许发送本条 Element 任务上下文后，从已初始化的 `attempt_006` 启动 `configs/focused_converter.yaml` 的 mini-swe/DeepSeek Converter。容器 `/tmp` 检查修复后，Jest 临时输出路径可正常使用；不再出现上轮 `echo /tmp/foo` 被拒的同类错误。
- 聚焦提示在约第 38 次模型调用时生成首份 Jest 测试和 `test.sh`，较前几轮仅探索到上百次仍无测试文件有实质改善。但初稿的独立 Jest 配置遇到仓库依赖组合的 `babel-jest` 错误，agent 正调整运行配置；尚未通过硬回放。
- 初稿扩展到会话管理测试后，独立审计发现精确 `data-testid`、`aria-expanded`/`tabindex` 形状以及 `Modal.createDialog`、`deleteMultipleDevices.mock.calls` 等断言，可能仍与历史实现绑定。当前只是未提交草稿，不能当作通过或最终缺陷结论；后续必须看 Converter 自审、语义 Judge 及正向 QA 是否要求改为用户可见动作与结果。没有手工改写任务测试。

## Element rev_001 提交后被 schema 拒绝（2026-10-05 07:37 UTC）

- mini-swe/DeepSeek 在 160 步内提交完整 rev_001，Base 试跑有 10 个新测试失败；但 `artifact_contract` 先于语义门槛拒绝：`decision=preserve`、`behavior_classification=delta/mixed_base_regression_and_delta`、`base_behavior_status=mixed/failing`、`task_disposition=complete` 等值不符合通用 schema，逐义务对象字段也不全。不能把此 revision 标为成功。
- 已修正通用聚焦提示的精确 JSON 词汇与混合义务写法，保持 schema 门槛不变。pipeline 自动创建 rev_002 并携带结构化反馈给 mini-swe 修复。完整问题记录见 `process/20261005_073717_focused_converter_schema_contract.md`。
- 当前仍需语义 Judge 专门处理草稿的 DOM/test id/mock 调用绑定风险，随后才可进行 hard replay 与 QA。

## Element rev_003：语义 Judge 拦截内部实现绑定（2026-10-05）

- rev_002 的 schema 修复后仍有 JSON 布尔和 canonical P2P 顺序问题；rev_003 由 mini-swe 修复并通过 artifact contract。独立 Semantic Judge 对 rev_003 给出 `FAIL`，hard replay、稳定性、正负 QA 均未运行，任务未发布。
- Judge 明确指出：退出当前会话用例断言 `Modal.createDialog` 的第一个参数是指定组件；退出其他会话用例断言 `deleteMultipleDevices.mock.calls` 的数组内容和顺序；若干用例使用精确 CSS class、`data-testid`、ARIA/DOM 形状。这些仍约束某种实现而非只看用户可见结果。Judge 还指出加载中／没有当前设备时的菜单禁用行为并非基础 P 明文要求，若是独立产品行为需经最小行为级 addendum，而不能偷偷算作 P 已支持。
- 这些是当前候选 verifier 的语义缺陷，不通过改 Docker、schema 或 runner 掩盖。pipeline 已生成 rev_004，将结构化语义反馈交给 mini-swe 修复；需要重新经过 Judge 与后续门槛。未手工改写任务测试。

## Converter 提交前自审补强（2026-10-05）

- 现象：Element rev_003 的自审写 `SELF_REVIEW: PASS`，但独立 Judge 立即指出 mock call shape、CSS class、test id 等具体实现绑定；同类风险可出现在其他 UI 或 service 任务。根因不是缺少“优先公开行为”的原则，而是构造器没有逐文件搜查实际 emitted tests 的绑定模式。
- 通用修复：在 `prompts/converter_focused.md` 加入提交前逐测试源检查 `mock.calls`、`toHaveBeenCalledWith`、`getByTestId`/`queryByTestId`、CSS class、snapshot、Gold 新符号的动作，要求区分测试夹具和最终断言，并把必要公共边界证据写入自审。此提示不会自动放宽任何门槛，已运行中的 rev_004 会话在启动时读取旧提示；后续新会话才会验证效果。
- 残余风险：静态模式本身不能判定所有语义；独立 Judge 与正负 QA 仍必须保留。当前未手工修改 Element verifier。

## Element 新发现缺口触发增量 addendum 框架修复（2026-10-05 08:17 UTC）

- rev_005 的 artifact contract 通过后，controller 自动把“加载中／无当前设备时禁用当前会话操作入口”两条行为写入 addendum。恢复流水线后，独立 Judge 拒绝 rev_005：这两条已成为有效规范却仍无 emitted tests；原第 0 条 F2P 的无设备禁用义务也未映射。Judge 另发现单设备时不显示“退出其他会话”同样需要规范依据，且当前测试使用 `getByLabelText('Sign out')`，可能依赖特定 label 形式。
- 现有 controller 只要 addendum 文件存在便不允许追加新提案，属于跨任务缺陷。已修复为增量追加与去重，相关 12 项测试通过；正在运行的 rev_006 会话使用旧加载代码，后续新 pipeline 进程才可实际验证。完整 issue 见 `process/20261005_081728_incremental_specification_addendum.md`。

## Element rev_006：禁用状态已补测，单设备缺口仍待处理（2026-10-05 08:28 UTC）

- mini-swe 提交的 rev_006 把加载中和无当前设备时的禁用状态加入测试，并修正对应 F2P 映射；artifact contract 与确定性 Gold-only 预检通过。
- 独立语义 Judge 仍给 `FAIL`：单设备时不显示“退出其他会话”尚未写入有效规范；退出其他会话测试只检查列表消失，没有确认当前会话仍存在；通过标题的 `parentElement` 找按钮也依赖 DOM 结构。不能据此宣称转换完成。
- 旧 pipeline 进程自动启动 rev_007 修复，但它在启动时加载了旧版 addendum 控制逻辑。当前轮结束后须由新进程读取已修正的增量追加逻辑，再验证新缺口和其余断言。

## Element rev_007：Gold Jest 通过但 harness 退出码错误（2026-10-05）

- mini-swe 提交的 rev_007 经独立语义 Judge 判为 `PASS`，退出其他会话的用例现在同时检查其他会话消失和当前会话保留。该次 Judge 把“仅有当前设备时不显示退出其他会话菜单项”解释为 P 可推导行为，虽 rev_006 Judge 曾判定需补充；发布前仍须复核这种推导是否过度约束其他正确 UI。
- Docker 硬回放显示 Gold 的 generated Jest 15/15 通过，Base 有 10 个预期失败；但候选 `tests/test.sh` 尾部无条件 `exit 0`，使 Base 和 Gold 的容器退出码都为 0，因此硬门槛正确拒绝。rev_008 已收到结构化回放反馈，须修复 harness 退出码，重新运行全部门槛。

## Element rev_008：Base/Gold 通过后角色审计缺少结构化结果（2026-10-05）

- rev_008 修复了 `test.sh` 的退出码，独立语义 Judge 与 Base FAIL / Gold PASS 硬回放均通过。
- 下一门槛 `behavior_role_audit` 拒绝：容器保留了 Jest 原生 `stdout.json` 和 `generated.json`，却没有留下 Harbor 结构化 `/logs/verifier/output.json`，因此逐 selector 状态全部为 `MISSING`。这是候选 verifier 的 parser/运行合同缺陷，不应把所有角色改成其他类别来掩盖。
- pipeline 已把缺失证据交给 rev_009 mini-swe 修复，随后需要重新做语义、硬回放和逐 selector 审计。

## 通用聚焦提示补齐 Harbor 输出合同（2026-10-05）

- 现象：Element rev_007 的 Gold Jest 全通过、Base Jest 按预期失败，但 harness 始终返回 0；rev_008 修复退出码后，仍只保留 Jest 原生 JSON，逐 selector 角色审计找不到结构化 `output.json`。
- 根因：`prompts/converter_focused.md` 仅笼统要求保存解析结果，没有明确 Harbor 验收的退出码和 `tests[{name,status}]` 输出合同。任何 pytest/Jest/Go 任务都可能出现同样漏项，不是 Element 特例。
- 通用修复：在聚焦构造器提示中明确 `test.sh` 必须传播任何必需 selector 的失败、用镜像内可用的解析器（`parser.py` 或等价实现）生成 `/logs/verifier/output.json`，要求 selector 名与 `config.json` 完全一致及保存原生诊断。既有硬回放和角色审计门槛不放宽。rev_009 会话启动时已读取旧提示；后续会话才受新提示影响。
- 验证：当前仍由 rev_009 及其后续门槛检查，不能仅凭提示改动宣称修复完成。

## 稳定性 P2P 包装器递归与通用修复（2026-10-05）

- 现象：rev_009 的语义、硬回放、角色审计通过后，稳定性校验的 P2P 专用容器持续运行超过九分钟。进程显示框架包装的 `test.sh` 调用候选 `run_script.sh`，而后者再调用 `test.sh`，形成循环。仅停止这条任务的该容器和旧控制器；已通过的 rev_009 产物与证据保留。
- 根因：共享 `_p2p_tests` 假定 `run_script.sh` 可独立作为原生 selector runner。这不是 Harbor 对 `run_script.sh` 的统一合同，任何语言/任务都可能委托回 `test.sh`。因此问题不是 Element 的偶然路径。
- 通用修复：稳定性只重复运行最终候选 Harbor verifier；每次从它在 Base 和 Gold 产生的结构化结果中逐一核对全部 retained P2P 与 converted regression selector，要求两侧均 `PASS`，同时保持 F2P 的 Base FAIL / Gold PASS。移除可能递归的临时 wrapper 和额外 Docker 运行。只复用同一 revision 的首轮硬回放，避免拿旧 revision 的结果。
- 验证：`tests/test_stability.py` 覆盖通过、失败 selector 和 `repeats=2` 仅调用一次新增候选回放的合同；与邻近转换测试合计 8/8 通过。还需用 rev_009 的真实 Docker 回放复核，以及继续正负 QA。

## Element rev_009：重新独立 Judge 拦截单设备过度推导（2026-10-05）

- 新控制器从未更改的 rev_009 重新开始，独立语义 Judge 这次给出 `FAIL`：P 说其他会话退出可从当前会话区发起，却不严格蕴含仅有一个设备时必须隐藏该菜单项。先前同一语义曾被 Judge 接受，说明一次通过不足以证明没有隐形 UI 合同。
- 该测试验证的是有意义的用户可见状态，不应简单删除；应把“单设备时不提供退出其他会话项”写为最小行为级 addendum，再让 mini-swe 保留公开菜单测试。rev_010 已收到反馈，新控制器包含此前验证的增量 addendum 修复。
- 这是语义推导与规格边界问题，不能用 Base/Gold 通过掩盖；最终仍需独立正向 QA 检验不同正确 UI 实现。

## Element rev_010：增量 addendum 在真实任务通过（2026-10-05）

- mini-swe 在 rev_010 按语义反馈把单设备菜单 F2P 改列 `missing_product_behavior/specification_gap`，保留行为级提案。修正后的控制器在既有两项 addendum 后只追加一项：“When the user has only one device, opening the current-session options menu shows no Sign out all other sessions option.”
- 这验证了通用增量 addendum 修复在真实任务上生效；rev_011 正在依据新有效规范继续修订测试，尚未通过后续门槛。

## Element rev_011：P2P describe 层级导致 selector 不同名（2026-10-05）

- rev_011 的语义、Base FAIL / Gold PASS 硬回放和 F2P 角色审计通过；修正后的稳定性门槛完成两次候选 verifier 回放，没有再次陷入递归。
- P2P 逐项检查发现一条历史 selector 在 Base/Gold 均缺失：config 的“opens encryption setup dialog when verifiying current session”前面含 `current session section` describe 层级，而实际 Jest 报告中的同一行为没有该层级，测试状态本身是 `PASSED`。历史补丁曾调整 describe 层级，说明这是 selector 命名/解析差异，不是功能测试失败。
- 框架保持严格名称门槛并向 rev_012 反馈，不将缺失当作通过。候选 verifier 应在语言适配层把实际运行结果与 canonical selector 正确对账，并保留该回归行为；若确实无法稳定选择，须提供排除证据，不得无声删除。

## Element rev_012：严格缺失检查正确拒绝未映射 P2P（2026-10-05）

- rev_012 加入 required-selector 缺失和 P2P 未通过检查；语义 Judge 通过，但仍未把实际 Jest 短层级名称映射到 config 中的 canonical 名称。Docker 中 Base 与 Gold 都以退出码 1 失败，硬回放正确拒绝。
- 控制器自动启动 rev_013；下一步必须修复名称映射或有证据地处理不稳定 selector，而非回退严格缺失门槛。

## rev_013 暴露缺失审计理由与反馈不足（2026-10-05）

- rev_013 未实质修改 verifier；再次语义审查时，Judge 对 6 条 F2P 的顶层空 `rationale` 给出 `FAIL`。同样的 trace 在较早修订曾获 PASS，说明非空必填字段不能依赖一次 LLM 判断。
- 通用修复一：在共享 `classification_errors` 中确定性拒绝空 `rationale`，由 artifact contract 先于语义 Judge 执行；保留每个 obligation 已有的非空理由检查。
- 通用修复二：修复反馈新增跨语言的 selector 名诊断：对缺失 P2P canonical selector，从 Base/Gold 结构化输出寻找同文件、同叶测试名的真实执行记录，连同状态提供给 mini-swe。只能在一对一证据明确时映射，不能虚构 PASS 或因 describe 层级变化删除有效回归。
- 验证：`test_conversion_schema.py`、`test_repair_feedback.py` 和 `test_stability.py` 合计 7/7 通过。当前 pipeline 进程已结束，后续须新进程加载修复并继续 Element。

## Element rev_015：名称诊断反馈在真实任务生效（2026-10-05）

- rev_014 补齐所有顶层 F2P `rationale`，artifact contract 和语义 Judge 通过；硬回放仍因同一 canonical P2P selector 在 Base/Gold 均缺失而拒绝。
- 新的通用反馈生成器在两侧结构化输出中分别找到同文件、同叶标题且状态 `PASSED` 的实际短名称，并把完整 canonical/actual 对和状态写进 rev_015 的 `repair_objectives`。这一通用诊断已在真实数据上验证，mini-swe 正据此修正语言适配层。

## Element 多轮修订轨迹审计（2026-10-05）

- 统计 `attempt_006/intermediate/converter/trajectory/rev_001` 至 `rev_015`：15 次 mini-swe 会话共记录 1021 次模型 API 调用。其中 rev_001、004、006、007、009 分别为 160、150、133、143、114 次；长耗时来自多步 agent 探索与重试，不能仅归因于一次 API 请求。
- rev_001–002 主要被转换 schema/accounting 拒绝；rev_003–006 主要处理内部调用形状、DOM 结构、规范缺口和 F2P 对账；rev_007–009 才补齐 Harbor 退出码与结构化结果；rev_009 之后的稳定性包装器递归属于共享框架缺陷；rev_011–015 的主要阻碍是 P2P canonical selector 与实际 Jest 名称差一层 describe，而反馈起初没有给出可执行的名称对照。rev_013 仅改动少量元数据却重新触发语义 Judge，暴露顶层空理由此前没有确定性检查。
- 结论：这些修订并非 15 次独立的功能转换难题。部分轮次用于补框架自身的输入/输出合同、修复校验器、澄清 Judge 结果及提高反馈精度。已经落地的通用修复见上文：聚焦提示补 Harbor 合同、稳定性重放改用完整候选 verifier、空理由前置到确定性 schema、缺失 selector 反馈给出 Base/Gold 实际名称及状态。
- 尚待优化：为语言适配层提供可复用的 selector 对账规则并要求唯一、可回溯的执行证据；把便宜的运行合同预检前移；对仅变动无关审计元数据的轮次检测无实质进展，避免整套 Judge 重跑。缓存语义结果必须覆盖会改变有效断言的测试脚本和配置内容，不能按 revision 名或测试文件数量跳过。配置允许构造/修复轮最多 160/180 步，预算调整应在前述确定性预检之后实施，不能只粗暴缩短上限。

- rev_015 后续验证：独立语义 Judge `PASS`，Base/Gold 硬回放 `pass`，完整候选 verifier 稳定性重放 `pass`；正/负 QA 仍在进行，尚不能标为最终转换完成。

## Element 完成与最终审计（2026-10-05）

- `attempt_006/rev_015` 已通过 artifact、语义 Judge、Base FAIL / Gold PASS、角色审计、两次稳定性重放、正向 QA（原测试失败且功能 verifier 通过）和负向 QA（相关错误实现被功能 verifier 拒绝）；pipeline `accepted` 并打包 `attempt_006/final`。
- 独立 `final-audit --write` 为 `PASS`，无 error/warning；原 10 条 F2P 全部对账，最终 10 条 functional selector；原 39 条 P2P 中 2 条有证据排除、另加入 5 条转换后的 Base 回归行为，最终 42 条 P2P；instruction 泄露检查 `PASS`。

## Tutanota rev_001–003 与通用 Judge 文件清单修复（2026-10-05）

- 初始 mini-swe 会话用了 109 次 API 调用，提交时才发现两条 F2P 都是 2 个 `behavioral_obligations` 却各只有 1 条 `obligation_accounting`。控制器把两条确切错误交给 rev_002；这是可前置到 agent 提交前的确定性检查，当前仍需单独一个修复 revision。
- rev_002 修好 schema 后，Judge 正确指出凭据错误消息前缀 `Could not decrypt credentials:` 既不在 P 中，也不是 historical F2P 的必要断言。rev_003 删除此前缀，但 Judge 又误称 `tests/build_verifier.cjs` 不存在；实际 revision 目录中有此文件。
- 根因是共享语义输入的 `_auditable_revision_tests` 只传 `.sh/.py/.ts/.tsx/.js/.jsx` 源内容，没有 `.cjs/.mjs`；文件发现仅 `glob('*')`，也遗漏嵌套源文件。Judge 把未收到的文件误判为实际缺失。Node、Go 等使用辅助构建/运行源文件的任务都可能复现，并非 Tutanota 特判。
- 通用修复：语义输入递归枚举完整 `tests/`，附上完整路径清单和每个文件的哈希/大小；对 CJS/MJS 及其他常见语言源码传入限长内容，明确告诉 Judge 列在清单中的文件确实存在。`tests/test_semantic_evidence.py` 6/6 通过；真实 rev_004 尚在 mini-swe 修复，待 Judge 新子进程验证。

- Tutanota rev_004 的新语义 Judge 已 `PASS`，不再误报实际存在的 `build_verifier.cjs`；Base FAIL / Gold PASS、逐 selector 审计和稳定性重放均通过。正向 QA 正在构造替代正确实现，仍未达到最终验收。

## Tutanota 完成与 final 包独立重放（2026-10-05）

- `attempt_001/rev_004` 的 artifact、语义 Judge、Base FAIL / Gold PASS、角色审计、稳定性、正向及负向 QA 全部通过，pipeline `accepted` 并打包。正向 QA 的不同正确实现由 Judge 判为 VALID，原测试与功能 verifier 均通过；这证明兼容另一实现，但没有 Element 的“原测试 FAIL / 功能 verifier PASS”区分证据。负向 QA 的相关错误实现由 Judge 判为 RELEVANT_NON_EQUIVALENT，功能 verifier 拒绝。
- 独立 `final-audit --write` 为 `PASS`，无 error/warning；原 2 条 F2P 全部对账，0 条 P2P；instruction 泄露检查通过。
- 人工核对时一度误以为 final 缺 `build_verifier.cjs`。实际 rev_004 的 `test.sh` 用 heredoc 在临时工作目录生成该脚本，`final/tests/` 与 revision 测试目录一致。直接以 **final/tests** 在官方 Docker 镜像重放再次得到 Base returncode=1、Gold returncode=0、整体 `pass`；不存在打包漏文件问题。此处区分了 rev_003 Judge 漏看独立 CJS 文件的真实框架问题和 rev_004 已内嵌 CJS 的新实现。
