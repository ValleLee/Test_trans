# 两条试验任务的问题分类与框架修复记录

## 1. 数据语义组成问题

### 无可区分功能增量

qutebrowser 的 historical F2P 绑定 Gold 新增 helper，但大部分产品行为在 Base 已存在。去掉 helper 绑定后没有 Base FAIL / Gold PASS 的功能差异。此类任务应终止为 `non_discriminative_task`，不能为了发布而制造新接口要求。

### 功能增量与既有回归混合

OpenLibrary 的 6 条 historical F2P 包含 2 条真实功能增量和 4 条 Base 已有行为。旧设计把所有转换结果都写入 `fail_to_pass`，混淆了历史来源和最终执行角色。

修复：完整保留 historical F2P accounting；按每条 Base replay 结果派生最终角色，增量进入 F2P，既有回归进入 P2P。

## 2. 观察边界选择问题

- qutebrowser helper 的空输入/控制字符输入域宽于真实产品入口，不能把 helper 独有输入伪装成产品契约。
- OpenLibrary 初始 revision 把 4 条回归映射到 Gold-only `read_author_person`/`DataField`；Semantic Judge 拒绝。
- 后续改用 `read_edition` 产品边界，但第一次使用不兼容的 `MarcXml` 夹具，Docker 证明 Base/Gold 都失败；修正为受支持的记录输入后通过。

修复原则：边界必须在 Base/Gold 都存在并可执行；输入域必须属于产品入口；运行证据优先于 prose 自审。

## 3. 结构化输出与 schema 问题

Converter 曾输出字符串形式的 `"true"`/`"false"`。这不是语义歧义，但会被严格 schema 拒绝。

修复：只对 `base_repo_observable`、`gold_only_binding` 的明确布尔字面量进行规范化；描述性或不确定文本仍拒绝。

## 4. Judge 证据与协议问题

- 动态测试体位于 `run_script.sh`，精简证据包只发送 `test.sh` 和语言源码，Judge 无法审阅。
- `config.json` 被截断，尾部 converted regression selectors 消失。
- 顶层 `p2p_accounting` 未发送。
- hard replay 在 Semantic gate 后运行，Judge 曾把 `not_run` 当缺失证据。

修复：Judge 证据包括所有 shell 源码、parser、完整 config 和 p2p accounting；提示明确 pre-replay 顺序。Judge transport/protocol failure 与语义 FAIL 分流。

## 5. 结果文件协议问题

角色审计器最初只读取 `output.json`，OpenLibrary verifier 使用 `parsed_results.json`，导致已经存在的 Base/Gold selector 结果被判为 MISSING。

修复：以 `tests[{name,status}]` schema 为契约，兼容两种文件名；不同语言的 PASS/FAIL 状态统一成 PASSED/FAILED。

## 6. 通用性说明

以上修复均不包含 instance ID、仓库名、commit、测试名或任务特有路径特判。规则分别作用于：

- 任意语言/runner 的 selector 角色；
- 任意 Harbor verifier 的结果 JSON；
- 任意 LLM Converter 的严格布尔输出；
- 任意动态 shell 测试生成器；
- 任意混合 functional delta 与 Base regression 的任务。

## 7. 验证

- 框架单元测试：9 passed。
- qutebrowser：`non_discriminative_task`，无 final。
- OpenLibrary rev_007：全门禁 PASS，final audit PASS。
