# OpsFlow 平台 — Mock 数据生成指南

## 概述

提供两个管理命令批量生成平台测试数据，覆盖所有 Django ORM 模型和 Neo4j 图数据库。

---

## 1. Django ORM Mock 数据

### 命令

```bash
# 进入后端目录
cd backend

# 创建 Mock 数据（跳过已存在记录）
python manage.py add_mock_data

# 强制更新已存在的记录
python manage.py add_mock_data --force

# 先清空再重新创建
python manage.py add_mock_data --clear
```

### 覆盖的数据范围

| 模块 | 模型 | 数量 |
|------|------|------|
| **opsflow** | `OpsProject` — 项目 | 5 |
| | `TemplateCategory` — 模板分类 | 8 |
| | `FlowTemplate` — 流程模板 | 10 |
| | `TemplateNode` — 模板节点 | 40 (4/模板) |
| | `TemplateVersion` — 模板版本 | 10 (1/模板) |
| | `FlowExecution` — 执行记录 | 6 |
| | `ExecutionNode` — 执行节点 | 24 |
| | `SchedulePlan` — 调度计划 | 3 |
| | `WebhookConfig` — Webhook 配置 | 9 (3/模板) |
| | `ExecutionScheme` — 执行方案 | 4 |
| | `PluginMeta` — 插件元数据 | 6 |
| | `OpsKnowledge` — 知识库 | 6 |
| | `ApiToken` — API 令牌 | 3 |
| | `ProjectEnvironmentVariable` — 环境变量 | 15 (5/项目) |
| | `OperationRecord` — 操作记录 | 15 |
| **opsagent** | `EnvironmentContext` — 环境上下文 | 4 |
| | `Session` — 会话 | 2 |
| | `AgentMemory` — 记忆 | 3 |
| **cmdb** | `ModelDefinition` — 模型定义 | 2 |
| | `ModelField` — 模型字段 | 9 |
| **integration** | `ConnectorDefinition` — 连接器定义 | 6 |
| | `ConnectorInstance` — 连接器实例 | 6 |

### 示例

```python
from opsflow.models import FlowTemplate, OpsProject

# 列出所有 Mock 模板
for t in FlowTemplate.objects.all()[:5]:
    print(t.id, t.name, t.category.code if t.category else '-')

# 列出 Mock 项目
for p in OpsProject.objects.all():
    print(p.id, p.name)
```

---

## 2. Neo4j CMDB 拓扑数据

### 命令

```bash
cd backend

# 生成中等规模拓扑（默认）
python manage.py add_mock_neo4j

# 小规模（快速验证）
python manage.py add_mock_neo4j --scale=small

# 大规模（完整演示）
python manage.py add_mock_neo4j --scale=large

# 清空后重建
python manage.py add_mock_neo4j --clear
```

### 数据规模

| 级别 | Biz | Set | Module | Host | Process | 总计节点 |
|------|-----|-----|--------|------|---------|---------|
| small | 2 | 4 | 8 | 16 | 32 | ~62 |
| medium | 3 | 9 | 27 | 81 | 162 | ~282 |
| large | 5 | 20 | 80 | 400 | 1200 | ~1705 |

### 拓扑结构

```
Biz (业务)
 └── Set (集群)
      └── Module (模块)
           └── Host (主机)
                └── Process (进程) ── DEPENDS_ON ──> Process
```

### 关系类型

| 关系 | 来源 → 目标 | 语义 |
|------|------------|------|
| `CONTAINS` | Biz → Set / Set → Module / Module → Host | 树状包含 |
| `RUNS` | Host → Process | 归属关系 |
| `DEPENDS_ON` | Process → Process | 服务依赖 |

### 查询示例 (Cypher)

```cypher
// 查看全量拓扑
MATCH (n)-[r]->(m) RETURN n.name, type(r), m.name LIMIT 50

// 查询某业务下所有主机
MATCH (b:Biz {name: "电商平台"})-[:CONTAINS*3]->(h:Host)
RETURN h.ip, h.hostname, h.status

// 查询服务依赖链
MATCH (p:Process {name: "app-server"})-[:DEPENDS_ON*1..3]->(dep)
RETURN p.name, collect(DISTINCT dep.name) AS dependencies

// 统计各状态主机
MATCH (h:Host) RETURN h.status, count(*) AS cnt

// 查询告警中的主机及其上运行的进程
MATCH (h:Host {status: "alarm"})-[:RUNS]->(p:Process)
RETURN h.hostname, h.ip, collect(p.name) AS processes

// 查找某进程被哪些进程依赖
MATCH (p:Process {name: "mysql"})<-[:DEPENDS_ON]-(dependents)
RETURN dependents.name, collect(dependents.name) AS used_by
```

---

## 3. 数据重置

如需完全重置所有数据（Django + Neo4j）：

```bash
cd backend

# 1. 清空 Django 业务数据（保留 RBAC 菜单等系统数据）
python manage.py add_mock_data --clear

# 2. 清空 Neo4j 图数据
python manage.py add_mock_neo4j --clear

# 3. 重新生成
python manage.py add_mock_data
python manage.py add_mock_neo4j
```

---

## 4. 注意事项

- **幂等性**：两个命令均支持重复执行，已存在记录会被跳过
- **依赖顺序**：先执行 `add_mock_data` 创建 Django 数据，再执行 `add_mock_neo4j` 创建图数据
- **Neo4j 连接**：确保 `env.py` 中 Neo4j 配置正确且服务正在运行
- **测试用户**：Mock 数据使用 `superadmin`（id=1）作为创建者
