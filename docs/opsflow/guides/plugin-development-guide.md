# OpsFlow 原子（Plugin）开发指南

> 本文以 `aliyun_ecs_create_instance` 原子为例，详细说明如何开发一个标准插件。

---

## 文件结构

```
backend/opsflow/plugins/
├── base.py                    # BasePlugin 基类（继承此类）
├── registry.py                # 插件注册中心（自动发现）
├── loader.py                  # 文件扫描器（rglob）
├── aliyun_ecs/                # 插件包目录
│   ├── __init__.py            # __group_name__ 定义分组展示名
│   ├── _client.py             # 工具模块（不注册为插件）
│   └── create_instance.py     # 原子定义文件（一个文件一个原子）
```

每个原子是一个独立的 `.py` 文件，放在对应的分组目录下。插件加载器自动扫描 `plugins/` 下所有 `.py` 文件，通过 `importlib` 导入后注册 `BasePlugin` 的子类到 `PLUGIN_REGISTRY`。

---

## 原子定义模板

从 [`create_instance.py`](../../../backend/opsflow/plugins/aliyun_ecs/create_instance.py) 提取的完整结构：

```python
"""创建 ECS 实例（含可选公网 IP 分配）"""              # 模块 docstring

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class AliyunEcsCreatePlugin(BasePlugin):               # 继承 BasePlugin
    # === 1. 元数据字段 ===================================
    name = "创建实例"                                    # 中文名称（必填）
    name_en = "Create Instance"                         # 英文名称（必填）
    code = "aliyun_ecs_create"                          # 插件唯一标识（必填）
    group = "Aliyun ECS"                                # 分组（必填）
    version = "v1.0"                                    # 版本号
    description = "创建一台阿里云 ECS 实例"                  # 中文描述
    description_en = "Create an Alibaba Cloud ECS..."    # 英文描述
    risk_level = "high"                                  # 风险等级
    icon = "Plus"                                        # 图标
    color = "#E6A23C"                                    # 主题色
    show_execution_controls = True                       # 是否显示执行控制
    show_loop_config = True                              # 是否显示循环配置

    # === 2. 表单配置 ====================================
    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="基础配置",
                name_en="Basic Config",
                tag_code="basic",
                items=[
                    FormItem(
                        tag_code="instance_name",
                        type="input",
                        name="实例名称",
                        name_en="Instance Name",
                        attrs={"placeholder": "my-ecs-instance"},
                        validation=[ValidationRule(type="required")],
                        col=12,
                    ),
                    FormItem(
                        tag_code="region",
                        type="async_select",
                        name="地域",
                        name_en="Region",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-regions/",
                            "placeholder": "选择地域...",
                            "placeholder_en": "Select region...",
                        },
                        validation=[ValidationRule(type="required")],
                        col=6,
                    ),
                ],
            ),
        ]

    # === 3. 执行逻辑 ====================================
    def execute(self, instance_name="", region="", **kwargs):
        # kwargs 包含 get_form_config() 中定义的所有参数
        # ... 业务逻辑 ...
        return {"success": True, "data": {"instance_id": "i-xxx"}}

    # === 4. 输出定义（可选）=============================
    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_id", "type": "string",
             "description": "新建的 ECS 实例 ID",
             "description_en": "Created ECS instance ID"},
        ]
```

---

## 字段详解

### 1. 元数据字段（类属性）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `code` | `str` | ✅ | **插件唯一标识**。全局唯一，如 `"aliyun_ecs_create"`。存于 `_atom_type` 中，运行时通过 `get_plugin(code)` 查找 |
| `name` | `str` | ✅ | **中文显示名称**。如 `"创建实例"`，前端插件选择器、节点标签默认值 |
| `name_en` | `str` | ✅ | **英文显示名称**。如 `"Create Instance"`，英文模式时替换 `name` |
| `group` | `str` | ✅ | **分组**。如 `"Aliyun ECS"`，决定插件在 stencil 侧边栏和选择器中的分类 |
| `version` | `str` | | **版本号**。默认 `"v1.0"`，支持多版本共存 |
| `description` | `str` | | **中文描述**。插件选择器中显示 |
| `description_en` | `str` | | **英文描述**。英文模式时替换 `description` |
| `risk_level` | `str` | | **风险等级**。`low` / `medium` / `high`，影响节点视觉标识 |
| `icon` | `str` | | **图标**。Element Plus 图标名（如 `"Plus"`、`"VideoPause"`） |
| `color` | `str` | | **主题色**。hex 颜色值（如 `"#E6A23C"`） |
| `show_execution_controls` | `bool` | | 是否显示 Execution Control 区域。控制流原子（pause/approval）设为 `False` |
| `show_loop_config` | `bool` | | 是否显示 Loop Config 区域。控制流原子设为 `False` |

### 2. 表单配置 `get_form_config()`

定义原子在 PropertyPanel 中展示的参数表单。有两种元素：

#### FormItem（单个字段）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `tag_code` | `str` | ✅ | 字段标识，**必须匹配 execute() 的形参名** |
| `type` | `str` | ✅ | 组件类型，见下方"表单组件类型" |
| `name` | `str` | ✅ | 中文标签 |
| `name_en` | `str` | | 英文标签（空则 fallback 到 `name`） |
| `attrs` | `dict` | | 组件属性：`placeholder`/`placeholder_en`/`options`/`min`/`max`/`multiple`/`api_endpoint`/`depends_on`/`searchable` 等 |
| `default` | `Any` | | 默认值 |
| `hidden` | `bool` | | 是否隐藏字段 |
| `scope` | `str` | | `"local"`（默认，节点本地变量）或 `"global"`（全局变量） |
| `validation` | `list[ValidationRule]` | | 校验规则，见下方 |
| `col` | `int` | | 栅格宽度 1-12（12 占满一行，6 占半行） |
| `events` | `list[FormEvent]` | | 联动事件 |

#### FormGroup（字段分组）

| 字段 | 说明 |
|------|------|
| `name` / `name_en` | 组标题（支持中英切换） |
| `tag_code` | 分组标识 |
| `items` | 子字段列表，可递归嵌套 `FormItem` 或 `FormGroup` |

#### 表单组件类型

| type | 说明 | 关键 attrs |
|------|------|-----------|
| `"input"` | 单行文本 | `placeholder`, `placeholder_en` |
| `"textarea"` | 多行文本 | `rows` |
| `"int"` | 整数 | `min`, `max` |
| `"select"` | 下拉选择 | `options: [{label, value}]` |
| `"switch"` | 开关 | — |
| `"checkbox"` | 复选框 | `options: [{label, value}]` |
| `"radio"` | 单选 | `options: [{label, value}]` |
| `"async_select"` | **异步搜索下拉** | `api_endpoint`, `depends_on`, `multiple`, `searchable` |
| `"cascader"` | 级联选择 | `api_endpoint`, `props` |
| `"slider"` | 滑块 | `min`, `max`, `label-0`, `label-n` |
| `"code_editor"` | 代码编辑器 | `language`, `height` |
| `"host_selector"` | CMDB 主机选择 | `api_endpoint` |
| `"ip_selector"` | IP 选择器 | — |
| `"datatable"` | 数据表格 | `columns` |
| `"datetime"` | 日期时间 | — |

#### async_select 详解

异步搜索下拉是最常用的一类复杂组件，用于级联选择：

```python
FormItem(
    tag_code="region",
    type="async_select",
    name="地域",
    name_en="Region",
    attrs={
        "api_endpoint": "/api/opsflow/plugins/aliyun/describe-regions/",
        "depends_on": "zone_id",          # 依赖另一个字段的值
        "multiple": True,                  # 支持多选
        "searchable": True,                # 支持搜索过滤
        "placeholder": "选择地域...",
        "placeholder_en": "Select region...",
    },
    validation=[ValidationRule(type="required")],
    col=6,
)
```

API 预期返回格式：
```json
{"data": [{"value": "cn-hangzhou", "label": "华东1（杭州）"}]}
```

`depends_on` 字段变更时自动重新加载选项列表。

### 3. 执行逻辑 `execute()`

```python
def execute(self, instance_name="", region="", zone_id="", image_id="",
            instance_type="", security_group_id="", vswitch_id="",
            internet_max_bandwidth_out=0, system_disk_size=0,
            system_disk_category="", **kwargs) -> dict:
```

**规则：**

1. **形参名必须匹配 FormItem 的 `tag_code`** — 前端表单收集的数据通过参数名传递
2. **返回固定格式的 dict：**

```python
{
    "success": True,                          # bool，是否成功
    "data": {                                 # dict，输出数据
        "instance_id": "i-xxx",
        "status": "Running",
        "stdout": "...",                      # 自动作为标准输出显示
        "stderr": "...",                      # 失败时自动作为错误输出
    },
    "error": "错误信息",                       # 失败时的错误消息
}
```

3. **`success=True`** 时引擎立即执行下一个节点；**`success=False`** 时节点标记为 FAILED
4. **不支持 `**kwargs` 吞掉未定义的参数** — 所有入参都应显式声明

### 4. 输出定义 `get_output_schema()`

定义本原子的输出字段，供下游节点的条件表达式引用（格式 `\${node_id.field_name}`）：

```python
@classmethod
def get_output_schema(cls):
    return [
        {"name": "instance_id", "type": "string",
         "description": "新建的 ECS 实例 ID",
         "description_en": "Created ECS instance ID"},
        {"name": "public_ip", "type": "string",
         "description": "公网 IP（如有分配）",
         "description_en": "Public IP (if assigned)"},
    ]
```

| 字段 | 说明 |
|------|------|
| `name` | 输出字段名，需匹配 execute() 返回的 `data` 中的 key |
| `type` | 类型：`string` / `number` / `boolean` |
| `description` | 中文描述 |
| `description_en` | 英文描述（可选） |

### 5. 变量类型 `get_var_types()`

控制参数是否进行 `${key}` 变量替换：

```python
@classmethod
def get_var_types(cls):
    return {
        "threshold": "plain",     # 不做替换
        "command": "splice",      # 模板替换（默认行为）
        "hosts": "split",         # 替换后按逗号分割为列表
        "callback": "lazy",       # 延迟解析
    }
```

默认所有参数为 `"splice"` 模式，即支持 `${node_id.field}` 引用。

---

## 执行流程

```
用户选择插件 → PropertyPanel 加载 get_form_config() → 填写参数 → 保存
→ pipeline_tree: {atom_type: "aliyun_ecs_create", params: {instance_name: "..."}}
→ build_bamboo_pipeline() → _create_element()
    → get_plugin(atom_type) 找到 AliyunEcsCreatePlugin
    → 创建 ServiceActivity(component_code="opsflow_plugin")
    → inputs['_atom_type'] = "aliyun_ecs_create"
    → inputs['instance_name'] = Var(SPLICE, "...")
→ 执行时 PluginService.execute()
    → get_plugin("aliyun_ecs_create") → AliyunEcsCreatePlugin
    → instance.execute(**resolved_params)
    → 返回 {"success": True, "data": {...}}
    → _promote_results() 写入 execution.context._node_outputs
    → 节点完成，引擎继续
```

---

## 注册与同步

插件加载器在 `apps.py:ready()` 中自动执行：

1. `discover_plugins()` → `PluginLoader.scan()` 遍历 `plugins/` 目录
2. 每个 `.py` 文件通过 `importlib.import_module()` 导入
3. `dir()` 扫描模块，找到所有 `BasePlugin` 子类
4. 注册到 `PLUGIN_REGISTRY[code][version]` + `PLUGIN_GROUP_MAP[group]`
5. `sync_plugin_meta_to_db()` 同步到 `PluginMeta` 表（供 API 查询）

**无需手动注册**，新文件放到 `plugins/<group>/` 目录下即可自动发现。

---

## 通用工具与控制流原子

部分特殊原子无需实际执行逻辑：

```python
# 手动暂停 — execute 立即返回，PluginService 处理 pause
class ManualPausePlugin(BasePlugin):
    code = "manual_pause"
    group = "Common Tools"
    icon = "VideoPause"
    color = "#909399"
    show_execution_controls = False
    show_loop_config = False

    def execute(self, **kwargs):
        return {"success": True, "data": {"paused": True}}

    @classmethod
    def get_form_config(cls):
        return []  # 无参数
```

**关键区别：**
- 控制流原子（pause / approval）设置 `show_execution_controls=False, show_loop_config=False`
- `get_form_config()` 返回 `[]` 表示无参数
- `group = "Process Control"` 归入流程控制分组
