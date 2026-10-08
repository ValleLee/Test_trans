以“**覆盖不同功能性 verifier 形态**”为主。
是刚发布的 **SWE-Bench Pro V2**：当前公开集是 **642 条、11 个仓库**，语言分布是 **Go 256 / Python 237 / JavaScript 145 / TypeScript 4**；因此 TS 本身非常少。V2 还对大量 instruction、test set 和镜像做了重新验证，所以这次应以 V2 为准，而不是之前的 731 条 V1。:chatgpt-content-reference{index="0"}

筛选时主要看三个条件：一是行为边界比较明确，容易重写成 public API / observable output 的 functional verifier；二是尽量覆盖不同 verifier 类型，而不是 20 条都做普通 unit-test 改写；三是避免明显依赖唯一内部实现的纯重构。这个思路也和我们前面确定的转换目标一致：从 historical instance 重建 normative intent，再把行为和历史实现偶然性拆开，最后重新 author functional verifier。:chatgpt-content-reference{index="1"} DeepSWE 本身也是明确要求通过 public API 和 observable outputs 做验证，并检查 prompt-verifier bijection 与 acceptance breadth。:chatgpt-content-reference{index="2"} :chatgpt-content-reference{index="3"}

### 推荐的 20 条

| # | 语言 | Repo | Instance ID | 任务特征 / 为什么适合做功能性转换 |
|---|---|---|---|---|
| 1 | Python | qutebrowser | `instance_qutebrowser__qutebrowser-5fdc83e5da6222fe61163395baaad7ae57fa2cb4-v363c8a7e5ccdf6968fc7ab84a2053ac78036691d` | **字体字符串解析**。涉及 quoted/comma-separated font families；很适合把“必须用某个类”的实现约束改成“输入→解析结果”的行为测试。:chatgpt-content-reference{index="4"} |
| 2 | Python | OpenLibrary | `instance_internetarchive__openlibrary-0dc5b20fa186f9714f8a838178597e69f549d026-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59` | **MARC 数据解析**：导入 880 alternate-script author names。典型 parser/data-transformation，可做多输入输出 functional verifier。:chatgpt-content-reference{index="5"} |
| 3 | Python | OpenLibrary | `instance_internetarchive__openlibrary-72321288ea790a3ace9e36f1c05b68c93f7eec43-v0f5aece3601a5b4419f7ccec1dbda2071be28ee4` | **查询规范化**：`work.title` → `title`。非常适合作为“旧 test 绑定 helper → observable query output”的典型转换案例。:chatgpt-content-reference{index="6"} |
| 4 | Python | OpenLibrary | `instance_internetarchive__openlibrary-123e6e5e1c85b9c07d1e98f70bfc480bc8016890-v2733ff199fb72f0d033a30dc62cb0a4742e3a7f4` | **ISBN/ASIN value-object 行为**。可围绕解析、比较、序列化等公开语义验证，避免绑定内部类实现。 |
| 5 | Python | OpenLibrary | `instance_internetarchive__openlibrary-09865f5fb549694d969f0a8e49b9d204ef1853ca-ve8c8d62a2b60610a3c4631f5f23ed866bada9818` | **TOC 序列化/字段保留**。输出数据结构直接可观测，比较适合作为低难度 functional conversion。:chatgpt-content-reference{index="7"} |
| 6 | Python | Ansible | `instance_ansible__ansible-942424e10b2095a173dbd78e7128f52f7995849b-v30a923fb5c164d6cd18280c02422f75e611e8fb2` | **WinRM 超时与失败恢复**。stdin 写入失败后必须有限次读取并及时抛出清晰异常，适合测试超时边界和外部可观察失败行为。:chatgpt-content-reference{index="8"} |
| 7 | Go | Navidrome | `instance_navidrome__navidrome-23bebe4e06124becf1000e88472ae71a6ca7de4c` | **HTTP/API 访问控制**。适合从具体 handler/helper assertion 转为请求→状态码/response 的黑盒测试。 |
| 8 | Go | Navidrome | `instance_navidrome__navidrome-3bc9e75b2843f91f6a1e9b604e321c2bd4fd442a` | **Cache TTL / eviction**。Keys、Values、Get 在过期前后的行为都可直接验证；非常典型。:chatgpt-content-reference{index="9"} |
| 9 | Go | Flipt | `instance_flipt-io__flipt-72d06db14d58692bfb4d07b1aa745a37b35956f3` | **文件 I/O / audit sink**。目录创建、文件生成、NDJSON 内容属于 externally visible behavior，适合 filesystem verifier。 |
| 10 | Go | Flipt | `instance_flipt-io__flipt-d966559200183b713cdf3ea5007a7e0ba86a5afb` | **context cancellation / timeout**。适合验证取消后的外部行为，而非要求 context 必须经过某几个内部 helper。:chatgpt-content-reference{index="10"} |
| 11 | Go | Teleport | `instance_gravitational__teleport-24cafecd8721891092210afc55f6413ab46ca211-vee9b09fb20c43af7e520f57e9239bbcf46b7113d` | **安全 + malformed input**：SQL Server Login7 越界读取。特别适合 property/fuzz 风格 verifier：任意畸形 packet 不 panic，并正确返回 error。:chatgpt-content-reference{index="11"} |
| 12 | Go | Vuls | `instance_future-architect__vuls-878c25bf5a9c9fd88ac32eb843f5636834d5712d` | **复杂结构化数据语义**：Trivy CVE 按来源拆分 severity/CVSS。可以测试最终 domain object，而不是内部 converter 写法。:chatgpt-content-reference{index="12"} |
| 13 | JavaScript | Element Web | `instance_element-hq__element-web-776ffa47641c7ec6d142ab4a47691c30ebf83c2e` | **UI 行为**：当前 session 缺失 kebab menu。可以测试渲染结果和用户 action，是 UI functional verifier 的代表。:chatgpt-content-reference{index="13"} |
| 14 | JavaScript | Element Web | `instance_element-hq__element-web-494d9de6f0a94ffb491e74744d2735bce02dc0ab-vnan` | **UI state 更新**：Widget room buttons 显示/切换异常。适合覆盖 state→render 的可观察行为。:chatgpt-content-reference{index="14"} |
| 15 | JavaScript | ProtonMail WebClients | `instance_protonmail__webclients-6f8916fbadf1d1f4a26640f53b5cf7f55e8bedb7` | **前端数据状态**：Drive folder 对 locked/soft-deleted share 的可用性判定。适合做状态输入→导航/错误反馈的功能验证。:chatgpt-content-reference{index="15"} |
| 16 | JavaScript | NodeBB | `instance_NodeBB__NodeBB-05f2236193f407cf8e2072757fbd6bb170bc13f0-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e` | **排序/查询语义**：按 last-post 时间升序读取旧 topic。属于非常干净的 DB/API observable behavior。 |
| 17 | JavaScript | NodeBB | `instance_NodeBB__NodeBB-0c81642997ea1d827dbd02c311db9d4976112cd4-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e` | **跨实体状态一致性**：topic merge 后 queued posts 必须指向新 topic。很适合 integration functional verifier。官方 V2 数据页已显示该条为 `2.0.0`。:chatgpt-content-reference{index="16"} |
| 18 | JavaScript | NodeBB | `instance_NodeBB__NodeBB-0e07f3c9bace416cbab078a30eae972868c0a8a3-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e` | **Authorization/security**：system-reserved tags 只有 privileged user 可用。输入角色×tag→允许/拒绝，非常容易构造替代实现。官方 V2 页同样显示为 `2.0.0`。:chatgpt-content-reference{index="17"} |
| 19 | JavaScript | NodeBB | `instance_NodeBB__NodeBB-0f788b8eaa4bba3c142d171fd941d015c53b65fc-v0ec6d6c2baf3cb4797482ce4829bc25cd5716649` | **数据库 + 文件系统 side effect**：删除 topic 时清理 thumbnail。可以测试最终 DB/文件状态，而不是 mock 调用次数。 |
| 20 | TypeScript | Tutanota | `instance_tutao__tutanota-de49d486feef842101506adf040a0f00ded59519-v10a26bfb45a064b93f4fc044a0254925037b88f1` | **安全 / 凭据解密失败恢复**：keychain 数据无法解密时应识别为不可用凭据并清理/回报，而不是让底层 crypto 异常逃逸。适合安全错误处理的 functional verifier。 |

这个组合我比较喜欢的地方在于，它不是简单地“每个 repo 随机抽几条”，而是在 **20 条里故意覆盖了至少 12 种 verifier 形态**：parser/normalization、serialization、CLI、HTTP、authorization、cache/time、filesystem、context cancellation、fuzz/security、structured domain data、UI rendering/state、DB integration。这样你后面评价 VerifierTrans 时，能看出来框架到底只是“会把 pytest 改写一下”，还是已经真的具备跨语言、跨功能表面的通用转换能力。

语言比例我建议就保持 **Python 6 + Go 6 + JavaScript 7 + TypeScript 1**。原因不是 TS 不重要，而是 V2 总共才 **4 条 TS**；如果为了形式均衡硬塞 4 条 TS，会让 20 条样本被一个极小的语言子集过度影响。第一轮先用 1 条典型 TS 检验 adapter，后续再专门把 V2 的 4 条 TS 全跑一遍会更合理。:chatgpt-content-reference{index="18"}


### V2 canonicalization note

The first draft contained three IDs that are not present in the official V2 `v2/tasks/` tree or the V2 `ScaleAI/SWE-bench_Pro` `default/test` rows. They were replaced with canonical V2 tasks while preserving the intended language and verifier coverage: Ansible WinRM timeout handling, ProtonMail unavailable-share state handling, and Tutanota credential decryption error handling.
