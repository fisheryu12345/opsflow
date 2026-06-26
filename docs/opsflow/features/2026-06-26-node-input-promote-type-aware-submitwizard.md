# 节点输入参数提权与 SubmitWizard 类型感知渲染

> 提交: b67fff40 | 日期: 2026-06-26
> 涉及 App: opsflow
> 类型: 功能新增

---

## 背景

在 opsflow 流程编辑器中，原子节点的 **input 参数**（RenderForm 渲染的表单项）之前无法一键提升为全局变量。用户只能在 PropertyPanel 中配置参数后，再去 GlobalVariablePanel 手动创建变量，操作路径断裂。

同时，SubmitWizard 的 Step 3 (Parameters) 中将所有全局变量统一渲染为 `<el-input>`，丢失了变量原有的 UI 类型——下拉框被渲染为文本框、日期选择器被渲染为普通输入框，用户体验差。

## 实现方案

### 核心架构 / 设计

整个功能分为三个子系统：

1. **Input Promote 系统** — PropertyPanel 中 RenderForm 表单项旁的一键提权按钮
2. **类型元数据系统** — `meta` 字段扩展，存储 select 选项、async_select API 端点等类型相关信息
3. **SubmitWizard 类型感知渲染** + async_select 级联加载

```
PropertyPanel (RenderForm)
  ├─ 字段右侧 Promote 按钮 (Upload 图标)
  │   → ElMessageBox.prompt 输入变量名
  │   → HookVariable API (promote_type=input)
  │   → 自动填充 ${varName} 到字段值
  │   → 全局变量可见于 GlobalVariablePanel
  │
  v
SubmitWizard Step 3 (Parameters)
  ├─ type=input     → <el-input>
  ├─ type=textarea  → <el-input textarea>
  ├─ type=password  → <el-input password show-password>
  ├─ type=int       → <el-input-number step=1>
  ├─ type=float     → <el-input-number step=0.1>
  ├─ type=select    → <el-select options=meta.options>
  ├─ type=async_select → <el-select filterable>
  │   └─ 无依赖 → 立即调用 API 加载选项
  │   └─ 有依赖 → watch 检测依赖变化后级联加载
  ├─ type=datetime  → <el-date-picker type=datetime>
  ├─ type=date      → <el-date-picker type=date>
  └─ type=time      → <el-time-picker>
```

### 关键代码

#### 1. 后端 — `normalize_global_vars()` 添加 `meta` 字段

`backend/opsflow/core/variable_resolver.py:42-65` — 规范化函数在结构化条目中增加 `meta` 字段：

```python
entry = {
    "value": val["value"],
    "type": val.get("type", "input"),
    "meta": val.get("meta", {}),    # ← 新增: 类型相关元数据
    "show_type": True,
    "description": "",
    "source_type": "manual",
    "source_info": None,
    "validation": [],
}
```

旧的扁平格式默认 `meta: {}`，完全向后兼容。

#### 2. 后端 — `hook_variable()` 增加 `promote_type` 支持

`backend/opsflow/views/mixins/template_variable.py:147-183` — 端点扩展：

```python
promote_type = request.data.get('promote_type', 'output')

if promote_type == 'input':
    # 输入提权: 直接存储值, source_type=manual
    current[var_key] = {
        "value": request.data.get('value', ''),
        "type": var_type,
        "meta": request.data.get("meta", {}),
        "source_type": "manual",
        "source_info": None,
    }
else:
    # 输出提权: 运行时懒解析, source_type=node_output
    current[var_key] = {
        "value": "",
        "type": var_type,
        "meta": request.data.get("meta", {}),
        "source_type": "node_output",
        "source_info": {"node_id": node_id, "tag_code": tag_code},
    }
```

`promote_type="input"` 时不需要 `node_id`，直接存储值；`promote_type="output"`（默认）保持原有懒解析行为。

#### 3. 后端 — `_is_template_ref()` 防 SDK 校验穿透

`backend/opsflow/views/aliyun_views.py:18-25` — 新增模板变量引用检测函数：

```python
TEMPLATE_VAR_PATTERN = re.compile(r'^\$\{[^}]+\}$')

def _is_template_ref(value: str) -> bool:
    return bool(value and TEMPLATE_VAR_PATTERN.match(value))
```

所有 6 个 `describe_*` 端点都添加了前置检查，在参数透传给 Aliyun SDK 前拦截 `${var_name}` 模式的值。

#### 4. 前端 — FormItem Promote 按钮

`web/src/components/RenderForm/FormItem.vue:17-19` — 在输入框右侧添加 Promote 图标按钮：

```vue
<el-button v-if="props.context?.onPromote" text type="primary" size="small"
  class="promote-btn" @click.stop="props.context.onPromote(config, value)">
  <el-icon><Upload /></el-icon>
</el-button>
```

仅当 `context.onPromote` 存在时显示，不影响非 opsflow 场景。

#### 5. 前端 — PropertyPanel `promoteInput()` 提权函数

`web/src/views/apps/opsflow/components/panels/PropertyPanel.vue:565-617` 核心提权逻辑：

```typescript
async function promoteInput(config: any, currentValue: any) {
  // 1. 弹窗询问变量名
  const { value } = await ElMessageBox.prompt('Enter a name...', 'Promote Input...')
  const varKey = value.trim()

  // 2. 构建 meta
  const meta: Record<string, any> = {}
  if (config.attrs?.options) meta.options = config.attrs.options
  if (config.type === 'async_select' && config.attrs?.api_endpoint) {
    meta.apiEndpoint = config.attrs.api_endpoint
    if (config.attrs?.depends_on) meta.dependsOn = config.attrs.depends_on
  }

  // 3. 调 API
  await HookVariable(props.templateId, { var_key: varKey, var_type: config.type, meta, promote_type: 'input' })

  // 4. 自动填充 ${varName}
  renderFormRef.value?.setField(config.tag_code, '${' + varKey + '}')
  form.value.plugin_params[config.tag_code] = '${' + varKey + '}'
}
```

#### 6. 前端 — SubmitWizard async_select 级联加载

`web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue:683-737` — 级联加载逻辑：

```typescript
// 只加载依赖已满足的变量
function loadReadyAsyncOptions() {
  for (const key of Object.keys(templateVars.value)) {
    if (vars[key]?.type === 'async_select' && depsResolved(key)) {
      loadAsyncOptions(key)  // 无依赖的如 region 立即加载
    }
  }
}

// watch 检测依赖值变化后重新加载
watch(overrides, () => {
  if (!varsLoaded.value) return
  for (const key of Object.keys(templateVars.value)) {
    if (tv[key]?.type !== 'async_select') continue
    if (depsResolved(key)) {
      tv[key].meta.options = []  // 清除旧选项
      loadAsyncOptions(key)       // 重新加载
    }
  }
}, { deep: true })
```

完整级联流程：
```
region (无依赖) → 立即加载选项 ✅
用户选 region → overrides.region 变化 → watch 触发
  → zone_id 依赖已满足 → 请求 describe-zones/?region=X ✅
  → image_id 依赖已满足 → 请求 describe-images/?region=X ✅
用户选 zone_id → overrides.zone_id 变化 → watch 触发
  → instance_type 依赖已满足 → 请求 describe-instance-types/?region=X&zone_id=Y ✅
```

#### 7. 前端 — 2 列 flex 响应式布局

```scss
.var-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.var-item {
  width: calc(50% - 6px);   // 两列
  padding: 12px 14px;
  box-sizing: border-box;
}
```

### 数据流

```
[全局变量存储]
FlowTemplate.global_vars (JSONField)
  └─ key: { value, type, meta: { options/apiEndpoint/dependsOn }, show_type, description, source_type }

[提权链路]
PropertyPanel → HookVariable API (promote_type=input) → DB 存储 → GetGlobalVariables API
                                                                     ↓
                                                          SubmitWizard Step 3
                                                            ├─ select → meta.options
                                                            ├─ async_select → API 级联加载 → meta.options
                                                            └─ input/int/date/time → 对应组件

[执行链路]
SubmitWizard → variable_overrides → execution_views.py merge → bamboo_builder.py
  → VariableResolver.resolve_variables() → 替换 ${varName} → 插件 execute()
```

### 设计决策

1. **提权时自动填充 `${varName}`** — 所有类型都自动填充（包括 async_select），因为 Aliyun 端有 `_is_template_ref()` 保护，不会将 `${varName}` 透传给 SDK
2. **`meta` 作为存储层的一部分** — 而非运行时计算。select 选项、async_select API 端点信息持久化到 JSONField，不依赖实时 API
3. **async_select 在 SubmitWizard 中实时加载** — 而不是在提权时冻结选项。因为正式运行时数据可能已经变化（如云资源列表更新）
4. **`watch(overrides, { deep: true })` 而非 computed** — 因为需要异步触发 API 请求，computed 不支持异步
5. **`varsLoaded` 守卫** — 防止 watch 在 `loadVars()` 初始化阶段触发级联加载，避免重复请求

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/core/variable_resolver.py:42-65` | `normalize_global_vars()` 添加 `meta` 字段 |
| `backend/opsflow/serializers.py:41` | `get_global_variable_list()` 返回 `meta` |
| `backend/opsflow/views/aliyun_views.py:18-25` | `_is_template_ref()` 拦截模板引用 |
| `backend/opsflow/views/mixins/template_variable.py:147-183` | `hook_variable()` 支持 `promote_type` |
| `web/src/components/RenderForm/FormItem.vue:17-19` | Promote 按钮渲染 |
| `web/src/views/apps/opsflow/components/panels/PropertyPanel.vue:565-617` | `promoteInput()` 提权函数 |
| `web/src/views/apps/opsflow/api/templates.ts:110-119` | `HookVariable` 接口扩展 |
| `web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue:683-737` | async_select 级联加载 |
| `web/src/views/apps/opsflow/components/panels/GlobalVariablePanel.vue` | select 选项编辑器 + `show_type` 保留 |

## 使用方式

### 节点输入参数提权

1. 在流程编辑器中选中一个 atom 节点（如阿里云 ECS 创建实例）
2. 在 PropertyPanel（右侧属性面板）的 Input Parameters 中
3. 点击任意字段输入框右侧的 Promote 图标（Upload 图标）
4. 在弹出的对话框中输入全局变量名（默认使用字段 tag_code）
5. 点击 Promote 确认
6. 字段值自动变为 `${变量名}`，全局变量出现在 GlobalVariablePanel 中

### SubmitWizard 中变量覆盖

1. 点击提交执行 → 打开 SubmitWizard
2. 进入 Step 3 (Parameters & Variables)
3. 所有全局变量按原始 UI 类型渲染：
   - 下拉框/异步下拉 → `<el-select>` 带选项列表
   - 数字 → `<el-input-number>`
   - 日期/时间 → `<el-date-picker>` / `<el-time-picker>`
   - 文本 → `<el-input>`
4. 异步下拉框支持级联：选地域 → 自动加载可用区/镜像选项

### 全局变量管理

1. 打开右侧 GlobalVariablePanel（Variables 侧边栏）
2. 支持 select 类型的选项编辑器（添加/删除/编辑 label+value）
3. 非 select 类型保留原始 value 输入
