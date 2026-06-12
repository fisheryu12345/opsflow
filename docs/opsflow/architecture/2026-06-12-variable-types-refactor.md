# Variable Types 目录重构 — variables → variable_types

> 提交: 66fa9493（第一版）+ dde68d11（第二版） | 日期: 2026-06-12
> 涉及 App: opsflow
> 类型: 重构

---

## 动机

原来 `opsflow/core/variables/` 目录名 `variables` 过于泛化，初看不知道是"什么变量"——是普通变量、环境变量、变量值的类型定义？`cmdb_variables.py` 在 `cmdb/` app 内部又重复了 `cmdb` 前缀，阅读时冗余且不易理解。

根据架构文档 `docs/opsflow_target.md` 的领域划分，CMDB 变量类型应归属于 CMDB 子产品。上一轮已将 `cmdb_variables.py` 迁移到 `backend/cmdb/variables/`，但目录名 `variables/` 的问题仍然存在。

本次重构在领域归属迁移的基础上，进一步优化了命名结构。

## 变更要点

### 变更前

```
backend/opsflow/core/variables/                     ← "variables" 含义模糊
  __init__.py                                        ← 导入 common + cmdb_variables
  common.py                                          ← 通用变量类型
  cmdb_variables.py                                  ← CMDB 变量类型（领域错位）

backend/cmdb/variables/                              ← 同样的问题
  __init__.py
  cmdb_variables.py                                  ← 文件名重复 "cmdb"
```

### 变更后

```
backend/opsflow/core/variable_types/                 ← "variable_types" 一眼看出是"变量类型定义"
  __init__.py                                         ← 导入 common + 桥接 cmdb.variable_types
  common.py                                           ← 通用变量类型（不变）

backend/cmdb/variable_types/                         ← 与 opsflow 侧命名一致
  __init__.py                                         ← 导入 query, topology, count
  query.py                                            ← CmdbQueryVariable — 实例查询
  topology.py                                         ← CmdbTopologyVariable — 拓扑路径
  count.py                                            ← CmdbCountVariable — 实例计数
```

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `opsflow/core/variables/__init__.py` | `from . import cmdb_variables` | `from cmdb.variable_types import *` |
| `opsflow/core/variables/common.py` | 在 old `variables/` 下 | 移到 `opsflow/core/variable_types/common.py` |
| `opsflow/core/variables/cmdb_variables.py` | 单文件 3 个类 | 删除（已拆分到 cmdb） |
| `cmdb/variables/__init__.py` | 单行导入 | 改为 `cmdb/variable_types/__init__.py` |
| `cmdb/variables/cmdb_variables.py` | 单文件 3 个类 | 拆分为 `query.py`, `topology.py`, `count.py` |
| `opsflow/plugins/registry.py:discover_variables()` | `from opsflow.core import variables` | `from opsflow.core import variable_types` |
| `opsflow/tests/test_variable_registry.py` | `from opsflow.core import variables` | `from opsflow.core import variable_types` |

### 关键代码对比

```python
# 重构前 — 变量注册入口
# opsflow/plugins/registry.py
def discover_variables():
    from opsflow.core import variables  # noqa

# 重构后 — 改用新包名
def discover_variables():
    from opsflow.core import variable_types  # noqa
```

```python
# 重构前 — CMDB 变量类型在一个文件
# opsflow/core/variables/cmdb_variables.py → 3 个类硬塞一起
class CmdbQueryVariable(LazyVariable): ...
class CmdbTopologyVariable(LazyVariable): ...
class CmdbCountVariable(LazyVariable): ...

# 重构后 — 拆分到 cmdb app，每类一个文件
# cmdb/variable_types/query.py
class CmdbQueryVariable(LazyVariable):
    """CMDB 实例查询变量 — 按条件查询 CMDB 模型实例"""
    code = "cmdb_query"
    ...

# cmdb/variable_types/topology.py
class CmdbTopologyVariable(LazyVariable):
    """CMDB 拓扑查询变量 — 获取实例的上/下游拓扑路径"""
    code = "cmdb_topology"
    ...

# cmdb/variable_types/count.py
class CmdbCountVariable(LazyVariable):
    """CMDB 计数变量 — 统计指定模型的实例数量"""
    code = "cmdb_count"
    ...
```

### 注册链（不变）

```
Django 启动 → opsflow/apps.py:ready()
  → discover_variables()
    → from opsflow.core import variable_types
      → opsflow/core/variable_types/__init__.py
        → from cmdb.variable_types import *     ← 桥接导入（领域归属 cmdb）
          → from . import query, topology, count
            → RegisterVariableMeta 元类自动注册到 VARIABLE_REGISTRY
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 目录名 | `variable_types` 而非 `variables` | `variable_types` 一眼能看出是"变量类型定义"，不是环境变量或普通变量 |
| 拆分方式 | 按功能拆为 3 个文件 | `query.py` / `topology.py` / `count.py` — 文件名即文档，快速定位 |
| 桥接导入 | `opsflow/__init__.py` 中 `from cmdb.variable_types import *` | 保持注册链不变，不破坏 `discover_variables()` 的调用约定 |
| 无兼容层 | 更新了所有 2 处引用（registry.py + test） | 内部引用可控，不需要废弃周期 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/opsflow/core/variable_types/__init__.py` | 新包入口，桥接导入 CMDB 变量 |
| `backend/opsflow/core/variable_types/common.py` | 不变，从旧路径平移 |
| `backend/cmdb/variable_types/__init__.py` | CMDB 侧变量类型包入口 |
| `backend/cmdb/variable_types/query.py` | CmdbQueryVariable — 实例查询变量 |
| `backend/cmdb/variable_types/topology.py` | CmdbTopologyVariable — 拓扑路径变量 |
| `backend/cmdb/variable_types/count.py` | CmdbCountVariable — 实例计数变量 |
| `backend/opsflow/plugins/registry.py:96-101` | `discover_variables()` — import 路径更新 |
| `backend/opsflow/tests/test_variable_registry.py:6` | 测试引用路径更新 |

## 使用方式

**开发者** — 变量类的注册和使用方式完全不变。只需知道新路径：

```python
# 直接使用 VariableLibrary 按 code 查找（推荐方式，不变）
from opsflow.core.variable_registry import VariableLibrary
cls = VariableLibrary.get_var_class("cmdb_query")

# 若需导入 CMDB 变量类（极少需要）
from cmdb.variable_types.query import CmdbQueryVariable
```

### 关联文档

- 相关 CMDB 架构: [cmdb 变量类型重构](architecture/2026-06-12-variable-types-refactor.md)

---

## 2026-06-12 Update — 变量注册解耦

> 提交: 66fa9493

### 变更内容

- 从 `opsflow/core/variable_types/__init__.py` 移除桥接导入 `from cmdb.variable_types import *`
- 改为 `cmdb/apps.py:ready()` 中自主注册 `from cmdb import variable_types`
- 消除 opsflow → cmdb 的 import 硬依赖

### 原因

之前的桥接导入方式要求 opsflow 在 import 层面硬依赖 cmdb。如果其他子 app（itsm、monitor 等）也想注册变量类型，还得改 opsflow 的代码。改为各 app 自主注册后，新增子 app 只需在自己的 `apps.py:ready()` 中加载变量包即可。

### 注册链对比

```
# 变更前 — opsflow 桥接导入
opsflow/apps.py:ready()
  → discover_variables()
    → from opsflow.core import variable_types
      → __init__.py → from cmdb.variable_types import *  ← opsflow 硬依赖 cmdb

# 变更后 — 各 app 自主注册
opsflow/apps.py:ready()
  → discover_variables()
    → from opsflow.core import variable_types
      → __init__.py → from . import common  (只加载 opsflow 自身)

cmdb/apps.py:ready()
  → from cmdb import variable_types          ← cmdb 自己注册自己
    → __init__.py → from . import query, topology, count
      → RegisterVariableMeta → VARIABLE_REGISTRY
```

具体的端到端注册链路见 [cmdb 文档中的全生命周期](architecture/cmdb/2026-06-12-variable-types-refactor.md)。
