# OpsFlow CMDB 深度重构 — 实施计划

> **基于:** docs/superpowers/specs/2026-06-05-opsflow-cmdb-design.md
> **Phase:** 1/3 (后端核心 · MySQL Schema + Neo4j)
> **预计工期:** 3-5 天

---

## 任务列表

### Phase 1.1 — MySQL Schema 模型（1 天）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 1.1.1 | 清理旧模型文件 | `backend/cmdb/models/node_types.py` 删除 | neomodel StructuredNode，已废弃 |
| | | `backend/cmdb/models/model_schema.py` 删除 | 重构为新文件 |
| | | `backend/cmdb/migrations/0001_initial.py` 删除 | 重建 migration |
| 1.1.2 | 创建 Classification 模型 | `backend/cmdb/models/classification.py` | cls_id, name, icon, sort_order |
| 1.1.3 | 创建 ModelDefinition + ModelField | `backend/cmdb/models/model_definition.py` | 合并自旧的 model_schema，增加 classification FK、source、is_paused |
| 1.1.4 | 创建 AttributeGroup | `backend/cmdb/models/attribute_group.py` | |
| 1.1.5 | 创建 AssociationType | `backend/cmdb/models/association.py` | asst_id, name, direction, ... |
| 1.1.6 | 创建 ModelAssociation | `backend/cmdb/models/association.py` | 同一文件 |
| 1.1.7 | 创建 ObjectUnique | `backend/cmdb/models/object_unique.py` | keys = JSONField |
| 1.1.8 | 创建 MainlineTopo | `backend/cmdb/models/mainline_topo.py` | 主线层级链定义 |
| 1.1.9 | 创建 `__init__.py` 统一导出 | `backend/cmdb/models/__init__.py` | |
| 1.1.10 | 生成 migration | `python manage.py makemigrations cmdb` | 注意先清除旧 migration 文件 |

### Phase 1.2 — Neo4j 基础设施（0.5 天）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 1.2.1 | 创建统一 Neo4j 客户端 | `backend/cmdb/services/neo4j_client.py` | 驱动连接池管理 + 会话上下文管理器 |
| 1.2.2 | 检查/更新 neo4j_router | `backend/cmdb/neo4j_router.py` | 现有文件，确认兼容 |
| 1.2.3 | 验证 Neo4j 连接 | `python manage.py check` | 确保应用启动正常 |

### Phase 1.3 — Service 层（1.5 天）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 1.3.1 | ValidationService | `backend/cmdb/services/validation_service.py` | 字段类型校验、必填检查、enum 校验、唯一约束查 Neo4j |
| 1.3.2 | NodeService — CRUD | `backend/cmdb/services/node_service.py` | create/list/retrieve/update/delete，纯 Cypher |
| 1.3.3 | AssociationService | `backend/cmdb/services/association_service.py` | create_relation/delete_relation/list_relations/get_neighbors |
| 1.3.4 | TopologyService | `backend/cmdb/services/topology_service.py` | get_tree/get_impact/global_search/full_topology |
| 1.3.5 | ImportService | `backend/cmdb/services/import_service.py` | 批量 UNWIND + MERGE |

### Phase 1.4 — View + Serializer + URL（1 天）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 1.4.1 | Schema 序列化器 | `backend/cmdb/serializers/schema_serializers.py` | MySQL 模型的 DRF Serializer |
| 1.4.2 | 实例序列化器 | `backend/cmdb/serializers/instance_serializers.py` | Neo4j 节点的动态序列化 |
| 1.4.3 | ClassificationViewSet | `backend/cmdb/views/classification.py` | |
| 1.4.4 | ModelManageViewSet | `backend/cmdb/views/model_manage.py` | ModelDefinition + ModelField |
| 1.4.5 | 关联 ViewSet | `backend/cmdb/views/association.py` | AssociationType + ModelAssociation + InstanceAssociation |
| 1.4.6 | DynamicInstanceViewSet | `backend/cmdb/views/instance.py` | URL: /instances/{model_code}/ |
| 1.4.7 | TopologyViewSet | `backend/cmdb/views/topology.py` | tree/impact/search/graph |
| 1.4.8 | 注册 URL | `backend/cmdb/urls.py` | 所有路由 |
| 1.4.9 | 注册 app + 确认 settings | `backend/cmdb/apps.py` + `settings.py` | |

### Phase 1.5 — 种子数据 + 清理（0.5 天）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| 1.5.1 | seed 命令 | `backend/cmdb/management/commands/seed_cmdb_models.py` | 5 个内置模型 + 字段 + 关联 + 分类 |
| 1.5.2 | admin.py | `backend/cmdb/admin.py` | Django Admin 注册 |
| 1.5.3 | 删除废弃文件 | `views/base.py`, `views/biz.py`, `views/host.py`, `serializers.py`, `services/topology_service.py`, `services/sync_service.py` | |

---

## 关键实现细节

### neo4j_client.py

```python
from neo4j import GraphDatabase
from django.conf import settings

class Neo4jClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = GraphDatabase.driver(
                f"{settings.NEO4J_PROTOCOL}://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        return cls._instance
    
    @property
    def driver(self):
        return self._driver
    
    def session(self):
        return self._driver.session()

graph_driver = Neo4jClient()
```

### NodeService Cypher 模板

```python
CREATE:    f"CREATE (n:{label} $props) RETURN n"
LIST:      f"MATCH (n:{label}) WHERE ... RETURN n SKIP $skip LIMIT $limit"
RETRIEVE:  f"MATCH (n:{label} {{instance_id: $id}}) RETURN n"
UPDATE:    f"MATCH (n:{label} {{instance_id: $id}}) SET n += $props RETURN n"
DELETE:    f"MATCH (n:{label} {{instance_id: $id}}) DETACH DELETE n"
COUNT:     f"MATCH (n:{label}) WHERE ... RETURN count(n)"
```

### 唯一约束校验

```python
# Neo4j 中查询是否已有值
cypher = f"""
    MATCH (n:{model_code} {{{field_name}: $value}})
    RETURN count(n) as cnt
"""
with graph_driver.session() as s:
    result = s.run(cypher, value=value).single()
    if result['cnt'] > 0:
        raise ValidationError(f'{field_name} 值已存在')
```

---

## 验证清单

1. `python manage.py migrate cmdb` ✅
2. `python manage.py seed_cmdb_models` → 检查 MySQL 表数据 ✅
3. 访问 `/api/cmdb/model-definitions/` 返回 5 个内置模型 ✅
4. `POST /api/cmdb/instances/Biz/` 创建业务实例，检查 Neo4j ✅
5. `GET /api/cmdb/topology/graph/` 返回力导向图数据 ✅
6. `GET /api/cmdb/topology/search/?q=xxx` 返回搜索结果 ✅
7. 级联删除测试：创建 Biz→Set→Module→Host，删除 Biz，检查 Neo4j ✅
