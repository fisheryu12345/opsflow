# 节点输出变量可见性 & CRUD 修复

> 提交: 7b2481de | 日期: 2026-06-14
> 类型: 修复合集

---

## 问题清单

### Bug 1: variable_browser API 字段 key 映射错误

节点插件的 `get_output_schema()` 使用 `name` 字段，但 API 只读 `tag_code` 和 `key`，导致所有输出字段被过滤。

**根因**：`backend/opsflow/views/mixins/template_variable.py:106`
```python
# 修复前
field_key = field.get('tag_code', field.get('key', ''))
# 修复后
field_key = field.get('tag_code', field.get('key', field.get('name', '')))
```

### Bug 2: cleanup_unused_vars 在 PATCH/POST 后自动删除变量

PATCH handler 调用 `cleanup_unused_vars()` 删除引用数为 0 的所有变量，导致新创建的变量和未引用的已有变量都被清理。

**根因**：`template_variable.py` PATCH handler 中 `cleanup_unused_vars` 无条件执行
**修复**：POST 和 PATCH handler 均不再调用 `cleanup_unused_vars`，保持为纯增量/替换操作

### Bug 3: onDelete 前端发送空对象

`onDelete` 遍历 globalVars 生成 `{ key: {} }` 空值后发送 POST，导致所有变量被覆盖为空。

**根因**：`VariableBrowser.vue` 未获取完整结构化数据
**修复**：改为 `GetGlobalVariables` API 获取完整 dict → 删除目标 key → 发送剩余数据

### Bug 4: 测试原子输出字段在前端不可见

`test_print_time` 插件的 `_outputSchema` 未同步到 graph node data，导致 `extractNodeOutputFields()` 只能返回兜底字段。

**根因**：PropertyPanel 的 `emitUpdate()` 未包含 `_outputSchema`
**修复**：PropertyPanel 中 `onPluginChange()` 和 `onFormChange()` 均写入 `form.value._outputSchema`

### Bug 5: GraphNodes 未透传到 VariableBrowser

`graphNodes` 经过 RenderForm → FormGroup → FormItem → TagInput/TagTextarea/TagVariableInput 链路时断裂。

**根因**：`FormGroup.vue` 未接收 `context` prop，`TagInput.vue` 未接收 `graphNodes` prop
**修复**：补全整个链路中缺失的 prop 传递

### Bug 6: contextWithVars computed 未重算

`form.value._outputSchema` 是新增属性，Vue 3 reactive 不会触发 computed 重算。

**修复**：引入 `formRevision` 修订计数器，每次属性变更时递增

## 涉及文件

| 文件 | 修复 |
|------|------|
| `template_variable.py` | 字段 key 映射、移除 cleanup |
| `PropertyPanel.vue` | `_outputSchema` 同步、formRevision |
| `VariableBrowser.vue` | onDelete 逻辑、引用保护 |
| `FormGroup.vue` | 新增 context prop |
| `RenderForm.vue` | 向 FormGroup 传递 context |
| `TagInput.vue`, `TagTextarea.vue` | 接收 graphNodes prop |
| `elements.py` | NodeOutput 注册 |
| `variable_resolver.py` | 被提升变量运行时解析 |

## 验证方法

1. 创建 A 节点(test_print_time)→ 选插件 → B 节点 Browse → 应看到 A 的输出字段
2. 添加全局变量 → 不消失(cleanup bug) ✅
3. 删除单个全局变量 → 不影响其他变量 ✅
4. 被引用的变量删除 → 提示阻止 ✅
5. 引用计数实时更新(从前端画布扫描) ✅
