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

---

## 为其他原子实现类型感知的标准做法

当前实现已经完全通用化。为新增原子插件实现 Input Promote + SubmitWizard 类型感知，只需三步。

### 第一步：定义 FormItem 字段类型

在插件的 `get_form_config()` 中用 `FormItem` 定义字段时，**选对 `type`、配好 `attrs`**即可。

```python
# backend/opsflow/plugins/my_plugin/my_action.py
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule

class MyActionPlugin(BasePlugin):
    name = "我的操作"
    code = "my_action"
    group = "自定义"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="基础配置",
                tag_code="basic",
                items=[
                    # -- 文本输入 --
                    FormItem(
                        tag_code="host",
                        type="input",
                        name="主机名",
                        attrs={"placeholder": "e.g. web-01"},
                        validation=[ValidationRule(type="required", error_message="请输入主机名")],
                        col=6,
                    ),
                    # -- 文本域 --
                    FormItem(
                        tag_code="description",
                        type="textarea",
                        name="描述",
                        attrs={"placeholder": "输入描述..."},
                        col=12,
                    ),
                    # -- 密码 --
                    FormItem(
                        tag_code="password",
                        type="password",
                        name="密码",
                        col=6,
                    ),
                ],
            ),
            FormGroup(
                name="资源选择",
                tag_code="resource",
                items=[
                    # -- 普通下拉菜单（选项固定） --
                    FormItem(
                        tag_code="action",
                        type="select",
                        name="操作类型",
                        attrs={
                            "options": [
                                {"label": "启动", "value": "start"},
                                {"label": "停止", "value": "stop"},
                                {"label": "重启", "value": "restart"},
                            ],
                            "placeholder": "选择操作...",
                        },
                        validation=[ValidationRule(type="required", error_message="请选择操作")],
                        col=6,
                    ),
                    # -- 异步下拉菜单（选项从 API 加载） --
                    FormItem(
                        tag_code="target_host",
                        type="async_select",
                        name="目标主机",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/my_plugin/describe-hosts/",
                            "placeholder": "选择目标主机...",
                        },
                        col=6,
                    ),
                ],
            ),
            FormGroup(
                name="资源配置",
                tag_code="config",
                items=[
                    FormItem(
                        tag_code="cpu",
                        type="int",
                        name="CPU 核数",
                        default=2,
                        attrs={"min": 1, "max": 128},
                        col=4,
                    ),
                    FormItem(
                        tag_code="memory",
                        type="float",
                        name="内存 (GB)",
                        default=4.0,
                        attrs={"min": 0.5, "max": 512},
                        col=4,
                    ),
                    FormItem(
                        tag_code="expire_at",
                        type="datetime",
                        name="过期时间",
                        col=4,
                    ),
                ],
            ),
            FormGroup(
                name="级联选择（依赖地域选可用区）",
                tag_code="cascade",
                items=[
                    FormItem(
                        tag_code="region",
                        type="async_select",
                        name="地域",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/my_plugin/describe-regions/",
                            "placeholder": "选择地域...",
                        },
                        col=6,
                    ),
                    FormItem(
                        tag_code="zone",
                        type="async_select",
                        name="可用区",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/my_plugin/describe-zones/",
                            "depends_on": "region",  # 关键：依赖 region
                            "placeholder": "先选地域...",
                        },
                        col=6,
                    ),
                    FormItem(
                        tag_code="instance_type",
                        type="async_select",
                        name="实例规格",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/my_plugin/describe-instance-types/",
                            "depends_on": "region,zone",  # 多依赖用逗号分隔
                            "placeholder": "先选地域和可用区...",
                        },
                        col=6,
                    ),
                ],
            ),
        ]
```

### 第二步：实现异步 API 端点

对于 `async_select` 类型，需要实现对应的 API 端点。

**内部 API（查自己数据库）：** 不需要 `_is_template_ref()` 保护。

```python
# backend/opsflow/views/my_plugin_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def describe_hosts(request):
    """返回主机列表供 async_select 使用"""
    hosts = MyHostModel.objects.filter(is_active=True).values('id', 'hostname', 'ip')
    result = [
        {"label": f"{h['hostname']} ({h['ip']})", "value": str(h['id'])}
        for h in hosts
    ]
    return Response({"code": 2000, "data": result})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_regions(request):
    """返回地域列表"""
    regions = RegionModel.objects.all().values('code', 'name')
    result = [{"label": r['name'], "value": r['code']} for r in regions]
    return Response({"code": 2000, "data": result})


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_zones(request):
    """级联：根据 region 查询可用区"""
    region = request.GET.get('region', '')
    if not region:
        return Response({"code": 2000, "data": []})
    zones = ZoneModel.objects.filter(region_code=region).values('code', 'name')
    result = [{"label": z['name'], "value": z['code']} for z in zones]
    return Response({"code": 2000, "data": result})
```

**外部 API（调用第三方 SDK）：** 必须加 `_is_template_ref()` 保护。

```python
# backend/opsflow/views/my_plugin_views.py
import re
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

TEMPLATE_VAR_PATTERN = re.compile(r'^\$\{[^}]+\}$')

def _is_template_ref(value: str) -> bool:
    """拦截未解析的模板变量引用 ${var_name}，避免透传给第三方 SDK"""
    return bool(value and TEMPLATE_VAR_PATTERN.match(value))


@api_view(['GET'])
@permission_classes([AllowAny])
def describe_external_resources(request):
    """调用外部 API 的端点（如阿里云、腾讯云、AWS）"""
    param = request.GET.get('param', '')
    if not param or _is_template_ref(param):  # 必须加
        return Response({"code": 2000, "data": []})

    try:
        client = get_external_client(param)
        result = client.describe_resources()
        return Response({"code": 2000, "data": result})
    except Exception as e:
        logger.exception("describe_external_resources failed")
        return Response({"code": 4000, "data": [], "msg": str(e)})
```

**级联端点：** 对所有可能传入的依赖参数都做检查。

```python
@api_view(['GET'])
@permission_classes([AllowAny])
def describe_instance_types(request):
    region = request.GET.get('region', '')
    zone = request.GET.get('zone', '')
    if not region or _is_template_ref(region) or _is_template_ref(zone):
        return Response({"code": 2000, "data": []})
    # ... 正常调用 SDK
```

### 第三步：注册路由

```python
# backend/opsflow/urls.py
from .views.my_plugin_views import describe_hosts, describe_regions, describe_zones

urlpatterns = [
    # ... 已有路由 ...
    path('plugins/my_plugin/describe-hosts/', describe_hosts, name='my-describe-hosts'),
    path('plugins/my_plugin/describe-regions/', describe_regions, name='my-describe-regions'),
    path('plugins/my_plugin/describe-zones/', describe_zones, name='my-describe-zones'),
]
```

### 总结：需要开发者做的事 vs 框架自动完成

| 阶段 | 需要开发者做的事 | 框架自动完成 |
|------|----------------|-------------|
| 定义插件 | 1. 实现 `get_form_config()` 选对 `type`<br>2. 配好 `attrs.options` / `attrs.api_endpoint` / `attrs.depends_on`<br>3. 实现 `execute()` | — |
| 异步 API | 1. 实现 view 函数返回 `{code: 2000, data: [{label, value}]}`<br>2. 如果是外部 API 调用，加 `_is_template_ref()` 保护<br>3. 注册路由 | — |
| **Promote 提权** | **什么都不用做** | PropertyPanel 字段自动显示 Promote 按钮 -> 自动读取 type/meta/options -> 调 API 存储 -> 自动填充 `${varName}` |
| **SubmitWizard 渲染** | **什么都不用做** | 自动根据 `type` 渲染对应组件：select->el-select / int->el-input-number / date->el-date-picker / input->el-input ... |
| **级联加载** | **什么都不用做** | 自动检测 `depends_on` -> 依赖值变化时自动重新加载选项 |
| **GlobalVariablePanel** | **什么都不用做** | select 显示选项编辑器；async_select 保留 apiEndpoint 信息 |
| **Aliyun SDK 保护** | `_is_template_ref()` 复制到你的 view 中（一行定义） | 拦截 `${varName}` 不传给 SDK |

### 类型—组件映射完整参考

| 插件 `type` | SubmitWizard 渲染组件 | attrs 关键字段 |
|------------|---------------------|---------------|
| `input` | `<el-input>` | `placeholder` |
| `textarea` | `<el-input type="textarea">` | `placeholder` |
| `password` | `<el-input type="password">` | `placeholder` |
| `int` | `<el-input-number :step="1">` | `min`, `max` |
| `float` | `<el-input-number :step="0.1">` | `min`, `max` |
| `select` | `<el-select>` | **`options: [{label, value}]`**, `multiple` |
| `async_select` | `<el-select filterable>` | **`api_endpoint`**, **`depends_on`**, `placeholder` |
| `datetime` | `<el-date-picker type="datetime">` | (无特殊 attrs) |
| `date` | `<el-date-picker type="date">` | (无特殊 attrs) |
| `time` | `<el-time-picker>` | (无特殊 attrs) |

---

## FormItem 类型全景分析

本节从全链路视角梳理一个 FormItem 类型从定义到最终渲染的完整生命周期。

### 一、原子如何定义 FormItem

原子插件在 `get_form_config()` 中声明其输入参数。每个参数是一个 `FormItem` 实例，`type` 字段决定了整个链路的行为。

```python
# backend/opsflow/schema/form_schema.py
class FormItem(BaseModel):
    tag_code: str                      # 字段标识，对应 execute() 的形参名
    type: str                          # 组件类型（20种）
    name: str                          # 前端显示名
    name_en: str = ""                  # 英文名（可选）
    attrs: Dict[str, Any] = {}         # 组件属性（options, api_endpoint, depends_on, min, max...）
    default: Any = None                # 默认值
    hidden: bool = False               # 是否隐藏
    scope: str = "local"               # local(节点本地) / global(可跨节点引用)
    validation: List[ValidationRule] = []
    events: List[FormEvent] = []       # 跨字段联动事件
    col: int = 12                      # 栅格宽度 1-12
```

**实际插件定义示例（完整）：**

```python
# backend/opsflow/plugins/aliyun_ecs/create_instance.py
@classmethod
def get_form_config(cls):
    return [
        FormGroup(name="基础配置", tag_code="basic", items=[
            FormItem(tag_code="instance_name", type="input", name="实例名称", col=12),
            FormItem(tag_code="region", type="async_select", name="地域", col=6,
                attrs={"api_endpoint": "/api/opsflow/plugins/aliyun/describe-regions/"}),
            FormItem(tag_code="zone_id", type="async_select", name="可用区", col=6,
                attrs={"api_endpoint": "/api/opsflow/plugins/aliyun/describe-zones/",
                       "depends_on": "region"}),
        ]),
    ]
```

### 二、后端如何处理 FormItem

#### 2.1 Plugin API 返回 form_schema

客户端请求插件详情时，后端返回完整的 form_schema 结构：

```python
# backend/opsflow/views/plugin_views.py
class PluginViewSet(ViewSet):
    @action(detail=False, methods=['get'])
    def variable_types(self, request):
        """返回所有已注册的变量类型"""
        return DetailResponse(data=VariableLibrary.get_all_variables())
        # 输出: [{"code": "input", "name": "文本输入", "type": "general", "tag": "input.input"}, ...]
```

**前端获取插件 schema：**

```typescript
// web/src/views/apps/opsflow/api/plugins.ts
export function GetPluginDetail(code: string) {
  return opsflowRequest({ url: prefix + `plugins/${code}/`, method: 'get' })
}
// 返回: { form_schema: [{tag_code, type, name, attrs, ...}], output_schema: [...] }
```

#### 2.2 提权 API（input promote）

当用户在 PropertyPanel 点击 Promote 按钮，前端调用 `HookVariable` API：

```python
# backend/opsflow/views/mixins/template_variable.py
@action(detail=True, methods=['post'], url_path='hook-variable')
def hook_variable(self, request, pk=None):
    promote_type = request.data.get('promote_type', 'output')

    if promote_type == 'input':
        # 输入提权: 直接存储值 + 类型元数据
        current[var_key] = {
            "value": request.data.get('value', ''),
            "type": var_type,                    # 从 FormItem.type 继承
            "meta": request.data.get("meta", {}), # 从 FormItem.attrs 提取
            "show_type": True,
            "description": description,
            "source_type": "manual",             # 手动管理，非动态
            "source_info": None,
            "validation": [],
        }
    else:
        # 输出提权: 运行时懒解析
        current[var_key] = {
            "value": "",
            "type": var_type,
            "meta": request.data.get("meta", {}),
            "source_type": "node_output",
            "source_info": {"node_id": node_id, "tag_code": tag_code},
        }
```

### 三、数据库如何存储

全局变量存储在 `FlowTemplate.global_vars` JSONField 中，采用结构化格式。

```python
# backend/opsflow/models/template.py
class FlowTemplate(models.Model):
    global_vars = models.JSONField(default=dict, verbose_name="全局变量")
```

**数据库中的完整存储结构：**

```json
{
  "instance_name": {
    "value": "my-server",
    "type": "input",           // ← 继承自 FormItem.type
    "meta": {},                // ← 继承自 FormItem.attrs（筛选后）
    "show_type": true,
    "description": "实例名称",
    "source_type": "manual",
    "source_info": null,
    "validation": []
  },
  "region": {
    "value": "cn-hangzhou",
    "type": "async_select",    // ← 继承自 FormItem.type
    "meta": {
      "apiEndpoint": "/api/opsflow/plugins/aliyun/describe-regions/",
      "dependsOn": ""
    },
    "source_type": "manual",
    "source_info": null
  },
  "zone_id": {
    "value": "",
    "type": "async_select",
    "meta": {
      "apiEndpoint": "/api/opsflow/plugins/aliyun/describe-zones/",
      "dependsOn": "region"
    },
    "source_type": "manual"
  }
}
```

**规范化函数确保结构完整：**

```python
# backend/opsflow/core/variable_resolver.py
def normalize_global_vars(global_vars: dict) -> dict:
    """统一输出结构化格式"""
    if not global_vars:
        return {}
    normalized = {}
    for key, val in global_vars.items():
        if isinstance(val, dict) and "value" in val:
            entry = {
                "value": val["value"],
                "type": val.get("type", "input"),
                "meta": val.get("meta", {}),       # ← 类型元数据
                "show_type": val.get("show_type", True),
                "description": val.get("description", ""),
                "source_type": val.get("source_type", "manual"),
                "source_info": val.get("source_info"),
                "validation": val.get("validation", []),
            }
        else:
            # 扁平旧格式 → 包装
            entry = {"value": val, "type": "input", "meta": {}, ...}
        normalized[key] = entry
    return normalized
```

**API 返回给前端时附加引用计数：**

```python
# backend/opsflow/views/mixins/template_variable.py — GET global-variables/
normalized = normalize_global_vars(template.global_vars)
result = {}
for key, entry in normalized.items():
    entry["reference_count"] = count_variable_references(tree, key)
    result[key] = entry
return DetailResponse(data=result)
```

### 四、前端如何提权

#### 4.1 Promote 按钮渲染

```vue
<!-- web/src/components/RenderForm/FormItem.vue -->
<div class="form-control-inner">
  <component :is="tagComponent" v-bind="tagProps" ... />
  <el-button v-if="props.context?.onPromote" text type="primary" size="small"
    class="promote-btn" @click.stop="props.context.onPromote(config, value)">
    <el-icon><Upload /></el-icon>
  </el-button>
</div>
```

#### 4.2 提权函数

```typescript
// web/src/views/apps/opsflow/components/panels/PropertyPanel.vue
async function promoteInput(config: any, currentValue: any) {
  if (!props.templateId || !form.value?.id) return
  let varKey = ''
  try {
    const { value } = await ElMessageBox.prompt('Enter a name...')
    if (!value?.trim()) return
    varKey = value.trim()

    // 从 config 提取类型和元数据
    const meta: Record<string, any> = {}
    if (config.attrs?.options) meta.options = config.attrs.options       // select 选项
    if (config.attrs?.multiple) meta.multiple = config.attrs.multiple     // 多选
    if (config.type === 'async_select' && config.attrs?.api_endpoint) {
      meta.apiEndpoint = config.attrs.api_endpoint                       // API 端点
      if (config.attrs?.depends_on) meta.dependsOn = config.attrs.depends_on  // 依赖
    }
    if (config.attrs?.min !== undefined) meta.min = config.attrs.min     // 数字最小值
    if (config.attrs?.max !== undefined) meta.max = config.attrs.max     // 数字最大值
    if (config.attrs?.step !== undefined) meta.step = config.attrs.step  // 步长

    // 调后端 API
    await HookVariable(props.templateId, {
      var_key: varKey,
      var_type: config.type || 'input',  // ← 关键：类型从 FormItem.type 继承
      meta,
      value: currentValue ?? config.default ?? '',
      description: config.name || config.tag_code || '',
      promote_type: 'input',
    })

    // 自动填充 ${varName}
    renderFormRef.value?.setField(config.tag_code, '${' + varKey + '}')
    form.value.plugin_params[config.tag_code] = '${' + varKey + '}'
    formRevision.value++
    ElMessage.success(`Global variable "${varKey}" created`)
  } catch (e: any) {
    if (e?.toString()?.includes('cancel')) return
    ElMessage.error(`Promote failed: ${e?.msg || e?.message || 'Unknown error'}`)
  }
}
```

**config 到 meta 的映射关系：**

| FormItem.attrs | meta 字段 | 说明 |
|---------------|-----------|------|
| `options` | `meta.options` | select/checkbox/radio 选项列表 |
| `multiple` | `meta.multiple` | 是否多选 |
| `api_endpoint` | `meta.apiEndpoint` | async_select API 端点 |
| `depends_on` | `meta.dependsOn` | async_select 依赖字段 |
| `min` | `meta.min` | 数字/滑块最小值 |
| `max` | `meta.max` | 数字/滑块最大值 |
| `step` | `meta.step` | 滑块步长 |
| `activeValue` / `inactiveValue` | `meta.activeValue` / `meta.inactiveValue` | switch 开关值 |

### 五、SubmitWizard 如何处理

#### 5.1 变量加载

```typescript
// web/src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue
async function loadVars() {
  const res = await GetGlobalVariables(props.templateId)
  const data = res.data || {}
  templateVars.value = {}
  overrides.value = {}
  for (const [key, val] of Object.entries(data)) {
    if (typeof val === 'object' && 'value' in val) {
      templateVars.value[key] = val
      // 初始化覆盖值
      overrides.value[key] = val.value ?? (val.type === 'int' || val.type === 'float' ? undefined : '')
      // 类型特定初始化：
      if (val?.type === 'slider')
        overrides.value[key] = typeof val.value === 'number' ? val.value : Number(val.value) || 0
      if (val?.meta?.multiple && typeof overrides.value[key] === 'string')
        overrides.value[key] = overrides.value[key].split(',').filter(Boolean)
      if ((val?.type === 'checkbox' || val?.type === 'cascader') && typeof overrides.value[key] === 'string')
        overrides.value[key] = overrides.value[key].split(',').filter(Boolean)
    } else {
      templateVars.value[key] = { value: val, type: 'input', description: '' }
      overrides.value[key] = val ?? ''
    }
  }
  // 加载 async_select 的实时选项
  await nextTick()
  loadReadyAsyncOptions()
  varsLoaded.value = true
}
```

#### 5.2 async_select 级联加载

```typescript
// 检查依赖是否已解析（不是 ${} 模板引用）
function depsResolved(key: string): boolean {
  return getDeps(key).every(dep => {
    const v = overrides.value[dep]
    return v !== undefined && v !== null && v !== '' && !/^\$\{/.test(String(v))
  })
}

// 加载所有依赖已满足的 async_select
function loadReadyAsyncOptions() {
  for (const key of Object.keys(templateVars.value)) {
    if (templateVars.value[key]?.type === 'async_select' && depsResolved(key)) {
      loadAsyncOptions(key)
    }
  }
}

// watch 检测依赖变化 → 重新加载
watch(overrides, () => {
  if (!varsLoaded.value) return
  for (const key of Object.keys(templateVars.value)) {
    if (templateVars.value[key]?.type !== 'async_select') continue
    if (!getDeps(key).length) continue
    if (depsResolved(key) && templateVars.value[key]?.meta) {
      templateVars.value[key].meta.options = []  // 清除旧选项
      loadAsyncOptions(key)                       // 重新加载
    }
  }
}, { deep: true })
```

#### 5.3 类型→组件渲染映射

Template 中的渲染逻辑（简化，展示完整条件链）：

```vue
<div v-for="key in templateVarsKeys" :key="key" class="var-item">
  <div class="var-item-head">
    <span class="var-item-key">{{ key }}</span>
    <el-tag class="var-item-tag">{{ varTypeLabel(templateVars[key]?.type) }}</el-tag>
  </div>

  <!-- select / async_select (下拉) -->
  <el-select v-if="type === 'select' || type === 'async_select'"
    v-model="overrides[key]" :multiple="meta?.multiple" filterable clearable>
    <el-option v-for="opt in (meta?.options || [])" ... />
  </el-select>

  <!-- int / float (数字) -->
  <el-input-number v-else-if="type === 'int'" v-model="overrides[key]" :step="1" ... />
  <el-input-number v-else-if="type === 'float'" v-model="overrides[key]" :step="0.1" ... />

  <!-- datetime / date / time (日期时间) -->
  <el-date-picker v-else-if="type === 'datetime'" type="datetime" ... />
  <el-date-picker v-else-if="type === 'date'" type="date" ... />
  <el-time-picker v-else-if="type === 'time'" ... />

  <!-- switch (开关) -->
  <el-switch v-else-if="type === 'switch'"
    :active-value="meta?.activeValue ?? true"
    :inactive-value="meta?.inactiveValue ?? false" />

  <!-- checkbox (多选组) -->
  <el-checkbox-group v-else-if="type === 'checkbox'" v-model="overrides[key]">
    <el-checkbox v-for="opt in (meta?.options || [])" :key="opt.value" :label="opt.value">
      {{ opt.label }}
    </el-checkbox>
  </el-checkbox-group>

  <!-- radio (单选组) -->
  <el-radio-group v-else-if="type === 'radio'" v-model="overrides[key]">
    <el-radio v-for="opt in (meta?.options || [])" :key="opt.value" :value="opt.value">
      {{ opt.label }}
    </el-radio>
  </el-radio-group>

  <!-- cascader (级联选择器) -->
  <el-cascader v-else-if="type === 'cascader'"
    v-model="overrides[key]" :options="meta?.options || []" filterable clearable />

  <!-- slider (滑块) -->
  <div v-else-if="type === 'slider'" style="display:flex;align-items:center;gap:12px;">
    <el-slider v-model="overrides[key]" :min="meta?.min ?? 0" :max="meta?.max ?? 100"
      :step="meta?.step ?? 1" show-stops style="flex:1" />
    <span>{{ overrides[key] ?? 0 }}</span>
  </div>

  <!-- host_selector / ip_selector (主机/IP 带过滤和自定义输入) -->
  <el-select v-else-if="type === 'host_selector' || type === 'ip_selector'"
    v-model="overrides[key]" :multiple="meta?.multiple"
    filterable allow-create default-first-option clearable>
    <el-option v-for="opt in (meta?.options || [])" ... />
  </el-select>

  <!-- textarea -->
  <el-input v-else-if="type === 'textarea'" type="textarea" :rows="3" ... />

  <!-- password -->
  <el-input v-else-if="type === 'password'" type="password" show-password ... />

  <!-- input (默认 fallback) -->
  <el-input v-else v-model="overrides[key]" ... />
</div>
```

#### 5.4 变量覆盖提交

```typescript
function buildVariableOverrides(): Record<string, any> {
  const vars: Record<string, any> = {}
  for (const key of templateVarsKeys.value) {
    const ov = overrides.value[key]
    const def = templateVars.value[key]?.value
    if (ov === undefined || ov === null) continue
    // 宽松比较：只提交用户真正改变的值
    // eslint-disable-next-line eqeqeq
    if (ov != def) vars[key] = ov
  }
  return vars
}
```

### 六、完整数据流图

```mermaid
flowchart TD
    A[插件 get_form_config] -->|FormItem{type, attrs}| B[Plugin API]
    B -->|form_schema JSON| C[PropertyPanel RenderForm]
    C -->|用户配置参数| D[promoteInput 提权]
    D -->|HookVariable API| E[(DB global_vars JSONField)]
    E -->|GET global-variables/| F[SubmitWizard loadVars]
    F -->|templateVars key| G{类型判断}
    G -->|select/async_select| H[<el-select>]
    G -->|int/float| I[<el-input-number>]
    G -->|datetime/date/time| J[<el-date-picker>]
    G -->|switch| K[<el-switch>]
    G -->|checkbox/radio| L[<el-checkbox-group>/<el-radio-group>]
    G -->|cascader| M[<el-cascader>]
    G -->|slider| N[<el-slider>]
    G -->|host_selector/ip_selector| O[<el-select allow-create>]
    G -->|textarea| P[<el-input textarea>]
    G -->|password| Q[<el-input password>]
    G -->|input/其他| R[<el-input>]
    H -->|meta.apiEndpoint| S[实时 API 加载选项]
    S -->|depends_on| T[watch 级联刷新]
    E -->|variable_overrides| U[execution_views.py]
    U -->|template_snapshot.global_vars| V[bamboo_builder.py]
    V -->|${varName}| W[VariableResolver 替换]
    W -->|实际值| X[插件 execute()]
```

### 七、类型支持总表

| 层级 | input | textarea | password | int | float | select | async_select | datetime | date | time | switch | checkbox | radio | cascader | slider | host_selector | ip_selector | code_editor | datatable | variable_input | meta_config | variable_mapping |
|------|:-----:|:--------:|:--------:|:---:|:-----:|:------:|:------------:|:--------:|:----:|:----:|:-----:|:--------:|:-----:|:--------:|:-----:|:-------------:|:-----------:|:-----------:|:---------:|:--------------:|:-----------:|:----------------:|
| 后端 schema | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| RenderForm (PropertyPanel) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SubmitWizard Step 3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | 🔒 | 🔒 | 🔒 |
| 提权(Promote) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | 🔒 | 🔒 | 🔒 |

> ✅ = 已实现 & 可用 & 经过验证
> ❌ = 未实现（SubmitWizard 中降级为 input/textarea 可用，但非专用渲染）
> 🔒 = 内部组件，不暴露给用户提权

---

## 2026-06-26 Update (2nd)

> 提交: 3f8184af

### 变更内容

- 新增 7 种类型在 SubmitWizard Step 3 的渲染：`switch`, `checkbox`, `radio`, `cascader`, `slider`, `host_selector`, `ip_selector`
- 修复多选下拉初始值类型（string → array），确保 `el-select[multiple]` v-model 正确
- 修复 slider 初始值类型（string → number）
- 文档追加 FormItem 类型全景分析章节

### 原因

实现完整类型覆盖，确保所有 FormItem 类型在 SubmitWizard 中都有对应的渲染组件，为 CMDB 对接做好准备。
