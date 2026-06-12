# CMDB 变量类型重构 — 从 opsflow 迁移并拆分文件

> 提交: 66fa9493（第一版）+ dde68d11（第二版） | 日期: 2026-06-12
> 涉及 App: cmdb
> 类型: 重构

---

## 动机

根据 `docs/opsflow_target.md` 架构文档，CMDB 变量类型（CmdbQueryVariable、CmdbTopologyVariable、CmdbCountVariable）在能力域上归属于 CMDB 子产品。原来放在 `opsflow/core/variables/cmdb_variables.py` 中存在领域错位。同时文件名 `cmdb_variables.py` 在 `cmdb/` app 内重复了 `cmdb` 前缀，阅读冗余。

本次重构将 CMDB 变量类型拆分为功能单一的文件，以 `variable_types/` 命名一目了然地表达"变量类型定义"的语义。

## 变更要点

### 变更前

```
# 路径 1: 领域错位 — CMDB 的变量放在 opsflow 中
backend/opsflow/core/variables/
  cmdb_variables.py    ← 3 个类挤在一个文件

# 路径 2: 文件重复前缀
backend/cmdb/variables/
  cmdb_variables.py    ← cmdb 目录下又 cmdb_ 前缀
```

### 变更后

```
backend/cmdb/variable_types/              ← 语义清晰："变量类型"定义
  __init__.py                              ← 导入 query, topology, count
  query.py                                 ← CmdbQueryVariable — 实例查询
  topology.py                              ← CmdbTopologyVariable — 拓扑路径
  count.py                                 ← CmdbCountVariable — 实例计数
```

### 代码结构

**`variable_types/__init__.py`** — 包入口，导入各模块触发 `RegisterVariableMeta` 元类自动注册：

```python
"""CMDB 变量类型包 — 导入此模块触发变量类注册到 VARIABLE_REGISTRY"""
from . import query      # noqa: F401 — CmdbQueryVariable
from . import topology   # noqa: F401 — CmdbTopologyVariable
from . import count      # noqa: F401 — CmdbCountVariable
```

**`variable_types/query.py`** — CMDB 实例查询变量：

```python
class CmdbQueryVariable(LazyVariable):
    """CMDB 实例查询变量 — 按条件查询 CMDB 模型实例"""
    code = "cmdb_query"
    name = "CMDB 查询"
    type = "dynamic"
    tag = "cmdb.cmdb_query"
    description = "按条件查询 CMDB 模型实例，返回实例列表"

    def get_value(self):
        from cmdb.services.node_service import NodeService
        # ... 运行时查询 Neo4j，返回 {items, total, model_code}
```

**`variable_types/topology.py`** — CMDB 拓扑查询变量：

```python
class CmdbTopologyVariable(LazyVariable):
    """CMDB 拓扑查询变量 — 获取实例的上/下游拓扑路径"""
    code = "cmdb_topology"
    # ...
    def get_value(self):
        from cmdb.services.topology_service import TopologyService
        # ... 运行时查询拓扑，返回实例的影响范围
```

**`variable_types/count.py`** — CMDB 实例计数变量：

```python
class CmdbCountVariable(LazyVariable):
    """CMDB 计数变量 — 统计指定模型的实例数量"""
    code = "cmdb_count"
    # ...
    def get_value(self):
        from cmdb.services.node_service import NodeService
        # ... 运行时计数，返回 {count, model_code}
```

### 注册链

```
discover_variables()
  → from opsflow.core import variable_types
    → opsflow/core/variable_types/__init__.py
      → from cmdb.variable_types import *
        → from . import query, topology, count
          → RegisterVariableMeta 元类 → VARIABLE_REGISTRY["cmdb_query"] = CmdbQueryVariable
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 目录名 | `variable_types` 而非 `variables` | 明确是"变量类型定义"，不是变量值或环境变量 |
| 拆分粒度 | 每个类一个独立文件 | `query.py` / `topology.py` / `count.py` — 文件名即职责说明 |
| 包导入方式 | `__init__.py` 显式导入每个模块 | 确保 metaclass 被触发注册 |
| 域间调用 | `opsflow` 通过 `from cmdb.variable_types import *` 桥接 | 不改变 `discover_variables()` 的注册入口约定 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/cmdb/variable_types/__init__.py` | 包入口，触发所有变量类注册 |
| `backend/cmdb/variable_types/query.py` | CmdbQueryVariable — 24 行核心逻辑，支持 model_code + filters + limit |
| `backend/cmdb/variable_types/topology.py` | CmdbTopologyVariable — 23 行核心逻辑，支持 instance_id + direction + max_depth |
| `backend/cmdb/variable_types/count.py` | CmdbCountVariable — 15 行核心逻辑，支持按 model_code 计数 |
| `backend/opsflow/core/variable_types/__init__.py` | 桥接导入 `from cmdb.variable_types import *` |

## 使用方式

变量类的使用方式完全不变。下游代码通过 `VariableLibrary` 按 `code` 引用：

```python
# 前端/服务层 — 获取变量结果（不变）
from opsflow.core.variable_registry import VariableLibrary
result = VariableLibrary.resolve("cmdb_query", config_value, context)

# 直接查询注册情况
from opsflow.core.variable_registry import VARIABLE_REGISTRY
cls = VARIABLE_REGISTRY.get("cmdb_topology")
```

### 关联文档

- 相关架构文档: [opsflow 变量类型目录重构](../opsflow/architecture/2026-06-12-variable-types-refactor.md)

---

## 2026-06-12 Update

> 提交: 66fa9493

### 变更内容

将 CMDB 变量注册从 opsflow 的桥接导入 (`from cmdb.variable_types import *`) 解耦为 cmdb 自主注册 (`cmdb/apps.py:ready()` 中 `from cmdb import variable_types`)，消除 opsflow → cmdb 的 import 硬依赖。

### 原因

之前的桥接导入方式要求 opsflow 在 import 层面硬依赖 cmdb。如果其他子 app（itsm、monitor 等）也想注册变量类型，还得改 opsflow 的代码。改为各 app 自主注册后，新增子 app 只需在自己的 `apps.py:ready()` 中加载变量包即可。

### 变量注册全生命周期

变量注册不是孤立事件，而是一条贯穿启动→配置→执行的完整链路。下面是全貌：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. 启动注册 (Startup Registration)                                      │
│                                                                         │
│  Django 启动                                                            │
│    ├─ opsflow/apps.py:ready()                                           │
│    │   └─ discover_variables()                                          │
│    │       └─ from opsflow.core import variable_types                   │
│    │           └─ opsflow/core/variable_types/__init__.py               │
│    │               └─ from . import common                              │
│    │                   └─ RegisterVariableMeta 元类触发                  │
│    │                       → VARIABLE_REGISTRY["input"] = InputVariable │
│    │                       → VARIABLE_REGISTRY["select"] = SelectVariable│
│    │                       → VARIABLE_REGISTRY["current_time"] = ...    │
│    │                       (共计 ~15 种通用变量类型)                     │
│    │                                                                     │
│    └─ cmdb/apps.py:ready()                                              │
│        ├─ Neo4j 驱动初始化                                              │
│        └─ from cmdb import variable_types                               │
│            └─ cmdb/variable_types/__init__.py                           │
│                ├─ from . import query                                   │
│                │   └─ RegisterVariableMeta                              │
│                │       → VARIABLE_REGISTRY["cmdb_query"]=CmdbQueryVariable│
│                ├─ from . import topology                                │
│                │   └─ RegisterVariableMeta                              │
│                │       → VARIABLE_REGISTRY["cmdb_topology"]=...         │
│                └─ from . import count                                   │
│                    └─ RegisterVariableMeta                              │
│                        → VARIABLE_REGISTRY["cmdb_count"]=...            │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. 前端展示 (API — 给用户选)                                            │
│                                                                         │
│  用户打开画布 → 添加全局变量 → 下拉选择变量类型                           │
│                                                                         │
│  GET /api/opsflow/plugins/variable_types/                               │
│  (opsflow/views/plugin_views.py:140-154)                                │
│                                                                         │
│  def variable_types(self, request):                                     │
│      types = VariableLibrary.get_all_variables()                        │
│      # → 遍历 VARIABLE_REGISTRY，返回 {code, name, type, tag}           │
│      #    ↑ 如果 cmdb 变量没注册，列表里就不会有"CMDB 查询"选项         │
│                                                                         │
│  返回结果（前端渲染为下拉框）：                                           │
│    [{code:"input",         name:"文本输入",     type:"general"},        │
│     {code:"select",        name:"下拉框",       type:"meta"},           │
│     {code:"current_time",  name:"当前时间",     type:"dynamic"},        │
│     {code:"cmdb_query",    name:"CMDB 查询",    type:"dynamic"},        │
│     {code:"cmdb_topology", name:"CMDB 拓扑路径", type:"dynamic"},        │
│     {code:"cmdb_count",    name:"CMDB 实例计数", type:"dynamic"}]        │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. 模板配置 (用户在画布上声明)                                           │
│                                                                         │
│  用户选择 "CMDB 查询" 后，填写配置:                                      │
│    code: "cmdb_query"                                                   │
│    value: '{"model_code":"Host","filters":{"status":"normal"},"limit":20}'│
│    → 保存到 FlowTemplate.global_vars:                                    │
│      {"host_list": {"code": "cmdb_query", "value": "{...}"}}            │
│                                                                          │
│  在后续节点中使用 ${host_list.items} 引用                                  │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. 运行时解析 (Execution Time — 真正干活)                               │
│                                                                         │
│  流程执行时，variable_resolver.py 扫描 global_vars:                      │
│                                                                         │
│  resolve_variables():                                                   │
│    for key, var_def in global_vars.items():                             │
│        code = var_def["code"]     # "cmdb_query"                       │
│        value = var_def["value"]   # {"model_code":"Host", ...}          │
│                                                                         │
│        # ↓ VARIABLE_REGISTRY 查找                                       │
│        result = VariableLibrary.resolve(code, value, context)           │
│                                                                         │
│        # resolve() 内部:                                                │
│        #   1. klass = VARIABLE_REGISTRY.get("cmdb_query")               │
│        #      → 找到 CmdbQueryVariable 类                                │
│        #   2. var = klass(value=json_str, context=ctx)                  │
│        #   3. result = var.get_value()   ← 关键步骤                     │
│        #      → 内部:                                                   │
│        #        from cmdb.services.node_service import NodeService      │
│        #        svc = NodeService("Host")                               │
│        #        result = svc.list({"status":"normal"}, page=1, page_size=20)│
│        #        return {"items": [...], "total": 42, "model_code":"Host"}│
│                                                                          │
│        # ↓ 替换模板变量                                                 │
│        template_tree = replace_vars(template_tree, {key: result})       │
│        # ${host_list} → {"items": [...], "total": 42, ...}              │
│        # ${host_list.items} → [...]                                      │
│                                                                         │
│  PluginService 再解析节点参数中的 ${host_list.items}:                    │
│    params = resolve_variables(node.params, global_vars_resolved)        │
│    # target_hosts: "${host_list.items}" → ["192.168.1.1", "..."]        │
│    plugin_instance.execute(**params)                                    │
└─────────────────────────────────────────────────────────────────────────┘

### 关键代码

**注册触发点 — cmdb/apps.py:ready() (行 26-30)：**

```python
def ready(self):
    # 1) Neo4j 驱动初始化
    from .services.neo4j_client import graph_driver
    graph_driver.initialize()

    # 2) 注册 CMDB 变量类型到 VariableLibrary  ← 新加入
    from cmdb import variable_types  # noqa: F401
```

**元类自动注册 — opsflow/core/variable_registry.py:20-29：**

```python
class RegisterVariableMeta(type):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        if not name.startswith('_') and hasattr(cls, 'code') and cls.code:
            if cls.code in VARIABLE_REGISTRY:
                logger.warning("变量 code 重复: %s", cls.code)
            VARIABLE_REGISTRY[cls.code] = cls  # ← 关键：写入全局注册表
        return cls
```

**前端 API — opsflow/views/plugin_views.py:140-154：**

```python
@action(detail=False, methods=['get'])
def variable_types(self, request):
    types = VariableLibrary.get_all_variables()  # ← 从 VARIABLE_REGISTRY 读取
    data = [
        {"code": code, "name": info.get("name", code),
         "type": info.get("type", "general"), "tag": info.get("tag", "")}
        for code, info in types.items()
    ]
    return DetailResponse(data=data)
```

**运行时解析 — opsflow/core/variable_registry.py:85-99：**

```python
@classmethod
def resolve(cls, code, value, context=None):
    var = cls.get_var(code, value=value, context=context)
    if var:
        return var.get_value()   # ← 执行 CmdbQueryVariable.get_value()
    return value                 # ← 未注册时原样返回（降级）
```

### 数据流

```
Django 启动
  → apps.py:ready() 触发模块导入
    → RegisterVariableMeta 元类写入 VARIABLE_REGISTRY
      → (至此启动完成，注册表就绪)

用户编排流程
  → GET /variable_types/ API 从 VARIABLE_REGISTRY 读取列表
    → 前端下拉框展示所有可选变量类型
      → 用户选择类型、填写配置、保存到模板

流程执行
  → VariableLibrary.resolve(code, value)
    → VARIABLE_REGISTRY[code] 查找类
      → 实例化 + get_value()
        → NodeService / TopologyService 查 Neo4j
          → 返回结构化数据替换模板中的 ${key}
            → PluginService 用解析后的参数执行原子
```
