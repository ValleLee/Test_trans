# 中间产物与实际运行边界的语义核查

时间：2026-10-06 06:49:30 UTC

## 现象与关键 evidence

Ansible 解释器任务旧 verifier 对返回 shebang 的检查之外，还断言内部 module_style。第一次新修订草稿移除 module_style，但又要求生成的 b_module_data 首行精确等于声明解释器，认为返回 shebang 正确、脚本首行不同就必然违反 P。

只读检查 Base 镜像的 lib/ansible/plugins/action/__init__.py：_execute_module 从 _configure_module 取得 shebang 与 module_data，之后将 shebang 传入 connection shell 的 build_module_command。lib/ansible/plugins/shell/__init__.py 的 build_module_command 将 shebang 去掉 #! 后直接放进执行命令。故生成脚本首行并非该执行链中唯一决定解释器的值；一个使用正确显式启动命令、但中间脚本首行不同的实现可以满足 P。原本建议“必须再断言 b_module_data 首行”已在 docs/261006_stage2_python10_audit.md 更正。

## Failure classification、根因与范围

这是可跨任务出现的框架级语义审查缺口：Converter 和 Judge 容易把返回字段、生成文件的文本布局、最终执行动作当作同一个契约。它可能造成对正确替代实现的误拒，也可能只检查一个实际未被消费的元数据值而漏检错误。具体 Ansible 断言仍是实例级 verifier 问题，须由 Converter REPAIR 处理。

## 通用修复与修改文件

已补充 prompts/converter.md、prompts/converter_focused.md、prompts/judges/semantic.md：要求追踪下游消费者实际使用的值，构造改变中间表示但保留 P 产品效果的反例；仅在 P 或已记录的公共运行契约要求时，才断言两个表示必须完全一致。未加入任务 ID、仓库名、特定文件路径或符号硬编码。

## 验证方法、结果与残余风险

只读源代码核查证实首行精确相等缺少当前执行链依据；三份提示词已本地修改。真实 Converter/Judge 效果要由新的 Ansible revision 与完整 Stage 2 gate 验证。当前 endpoint 自动审批要求用户消息明确具体目的地与发送材料范围；在获得该授权前不重试模型调用。提示词改动不等于已修好旧 verifier，也不能单独证明新任务通过独立审计。
