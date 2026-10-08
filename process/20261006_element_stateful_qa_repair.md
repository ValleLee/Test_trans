# Element 功能 verifier：状态模拟与修订耗时

记录时间：2026-10-06。只处理五条试验任务中的 Element；未扩展到其他数据。

## 现象与跨任务根因

旧 `attempt_006` 自动接受，但独立审计发现两个测试在整页统计 `aria-haspopup` 按钮并要求恰好一个。题面只要求当前会话区域有可用菜单；其他区域增加菜单是等价正确实现，旧 verifier 会误拒。`attempt_007` 由框架 mini-swe/DeepSeek 修订，未手工改写测试。

修订轨迹揭示两类通用风险：

1. 为避免全局 DOM 计数，候选曾改用 `data-testid` 和区域内精确计数。该测试专用定位与唯一性仍不由题面支持，独立语义 Judge 拒绝。
2. 为检验“退出其他会话”，候选先断言某个 SDK 删除方法的精确参数，误拒等价公开删除方式；随后又把 `getDevices` 的操作后响应预设为只剩当前设备，使得只刷新界面的错误解也可通过。Judge 和独立反例分别发现这些问题。
3. 后续有状态模拟虽修复预设结果，但只支持一个删除入口，或把所有 `delete*` 方法都当作会话退出。前者误拒等价实现，后者放过无关删除调用。共享 Converter 提示已增补通用规则：公开读取必须返回实时模拟状态；只有有语义的公开变更操作才能改变该状态；不得预设操作后结果；需要同时核对外部状态与可见 UI，并容纳 Base 中等价公开操作。

这些风险适用于任何涉及外部状态变化的任务，修复没有使用 instance ID、repo 名、commit 或当前测试名作共享框架特判。

## 当前进度

`attempt_007` 的 `rev_001` 至 `rev_006` 都未取得独立认证。`rev_006` 的 LLM Judge 曾给 PASS，但独立审计构造“无关 delete 方法触发模拟器删除其他设备”的假阳性，停止了已知无效的 Docker 回放。框架 `next_revision/seed_revision/write_feedback` 已生成 `rev_007`，要求模拟真实设备删除效果并检查公开查询及 UI；mini-swe/DeepSeek 正在修订。

本轮开始前另外四条任务已取得独立 PASS。Element 未计入完成数；只有经语义、Base/Gold/P2P、稳定性、正负 QA、final audit 和独立审计后才可计入。

## 耗时分析

Harbor 到 Harbor 的文件改造很少，耗时集中在语义质量认证。该轮首版 Converter 约 7 分钟，后续 mini-swe 修订各使用几十至百余条消息；语义子进程有的持续约 10 分钟，内部可能含协议重试，不能据子进程总时长推断单次 API 请求时长。每个被拒绝的 revision 都要重新提交和审核；Docker Base/Gold/P2P、稳定性与正负 QA 在语义门槛之后继续增加墙钟时间。已观察到 endpoint 连接建立且模型返回过有效 verdict，没有证据将全部耗时归为网络连接故障。

## 后续修订：模拟器不能替实现掩盖错误

`rev_005` 有状态模拟只支持一种公开删除入口，Judge 拒绝。`rev_006` 用 `delete*` 名称前缀泛化入口，Judge 给 PASS，但独立反例显示无关删除也会清空其他会话；在已知错误下提前停止了 Docker 回放。`rev_007` 改为仅支持 Base 中两种实际设备删除操作，按传入设备 ID 修改集合，并检查 UI 及公开 `getDevices`。独立审计又发现模拟器无条件保留当前设备：若错误解同时删除当前和其他设备，模拟器仍会让其通过。该轮语义请求已停止，结构化反馈送入 `rev_008` 的 mini-swe 修订。

共享 Converter 提示又补充了通用规则：测试替身必须忠实反映候选解请求的错误变更，不得暗中保护本应由解题实现保持的不变量；自审应构造错误目标的反例。`rev_008` 的完整门槛仍待执行，Element 尚未认证。

## `rev_008` 完整结果

`rev_008` 经独立语义 Judge、Base/Gold/P2P Docker 回放、行为角色审计和稳定性复跑通过。正向 QA 的不同实现通过功能 verifier、未通过原 verifier，fresh Judge 判为 `VALID`。负向 QA 只移除“无当前设备时禁用菜单”的条件，功能 verifier 拒绝，fresh Judge 判为 `RELEVANT_NON_EQUIVALENT`。控制器已接受并打包完整 Harbor final；独立审计核对 instruction、10 条 F2P 映射和可观察测试边界，结论为 PASS。最终认证以 `review/final_audit.json` 为准。

## 五条试验任务的最新 attempt 审计

截至 2026-10-06，Element `attempt_007`、qutebrowser `attempt_023`、Tutanota `attempt_005`、两条 OpenLibrary `attempt_001` 的最终 Harbor 包、正负 QA、独立审计、final-audit 均为 PASS，审阅指标 `certified_final=true`。两条 OpenLibrary 的独立审计原见 `process/20261004_171526_remaining_images_conversion.md`，现已写入各自 `review/independent_audit.json`；它们的语义证据早于当前 verifier fingerprint 合同，因此 final-audit 仍给出 `legacy_unversioned` 警告。该警告不被解释为新一轮模型复审。
