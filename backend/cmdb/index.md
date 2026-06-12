# cmdb — 模块索引

> 上次自动更新: 2026-06-12

---

## `cmdb/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | CMDB app package |
| `admin.py` | Admin registration for CMDB MySQL models | `ClassificationAdmin`<br>`ModelFieldInline`<br>`ModelDefinitionAdmin`<br>`ModelFieldAdmin`<br>`AttributeGroupAdmin`<br>`AssociationTypeAdmin` |
| `apps.py` | AppConfig for cmdb app | `CmdbConfig` |
| `neo4j_router.py` | Django database router for Neo4j dual datasource | `CmdbNeo4jRouter` — Django 多数据库路由 cmdb 中的 Neo4j 节点模型（以 'Neo4j' 结尾的模型名）路由到 neo4j 数据库。 其他模型使用默认 MySQL 数据库。 |
| `urls.py` |  | URL configuration for CMDB app |

## `cmdb\management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands for cmdb app |

## `cmdb\management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands package |

## `cmdb\models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Re-export all CMDB models |
| `association.py` | Association models — 关联类型 & 模型关联，对标 bk-cmdb AssociationKind & Association | `AssociationType` — 关联类型 (AssociationKind) 对标 bk-cmdb AssociationKind。每个 asst_id 对应 Neo4j 一种 Relationship Type。<br>`ModelAssociation` — 模型关联 (Association) 对标 bk-cmdb Association。定义哪些模型之间可以建立哪种关联。 |
| `attribute_group.py` | AttributeGroup — 属性分组，对标 bk-cmdb AttributeGroup | `AttributeGroup` — 属性分组 (AttributeGroup) 对标 bk-cmdb AttributeGroup，用于字段的分组展示。 |
| `change_log.py` | CMDB change log model — 记录模型实例的变更历史 | `ChangeLog` — CMDB 变更日志 |
| `classification.py` | Classification model — 模型分类，对标 bk-cmdb Classification | `Classification` — 模型分类 (Classification) 对标 bk-cmdb Classification，用于对模型进行分组归类。 |
| `event_subscription.py` | CMDB event subscription model — 实例变更事件的订阅配置 | `EventSubscription` — CMDB 事件订阅 |
| `mainline_topo.py` | MainlineTopo — 主线拓扑定义，对标 bk-cmdb 主线概念 | `MainlineTopo` — 主线拓扑定义 (MainlineTopo) 对标 bk-cmdb 主线概念。定义模型的拓扑层级关系。 如 Biz → Set → Module → Host，每层通过 parent_model 关联。 |
| `model_definition.py` | ModelDefinition & ModelField — 模型定义和字段，对标 bk-cmdb Object & Attribute | `ModelDefinition` — 模型定义 (Model/Object) 对标 bk-cmdb Object。code 作为 Neo4j Label 标识。 内置模型 (is_builtin=True) 不可删除。<br>`ModelField` — 模型字段定义 (Attribute) 对标 bk-cmdb Attribute。定义模型实例的一个属性。 |
| `object_unique.py` | ObjectUnique — 唯一约束，对标 bk-cmdb ObjectUnique | `ObjectUnique` — 唯一约束 (ObjectUnique) 对标 bk-cmdb ObjectUnique。 keys 字段存储字段名列表，表示这些字段的组合值在实例中唯一。 |

## `cmdb\serializers/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Re-export all serializers |
| `instance_serializers.py` | Serializers for Neo4j dynamic instances | `DynamicInstanceSerializer` — 动态实例序列化器<br>`InstanceRelationSerializer` — 实例关联序列化器 |
| `schema_serializers.py` | Serializers for MySQL schema models (CoreModel subclasses) | `ClassificationSerializer`<br>`ClassificationCreateUpdateSerializer`<br>`ModelDefinitionSerializer`<br>`ModelDefinitionCreateUpdateSerializer`<br>`ModelFieldSerializer`<br>`ModelFieldCreateUpdateSerializer` |

## `cmdb\services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Services package for CMDB app |
| `association_service.py` | feat(job-platform): complete backend + frontend implementation | `AssociationService` — 实例关联管理 |
| `change_tracker.py` | 123 | `track_create()` — 记录实例创建<br>`track_update()` — 记录实例更新 — 逐字段对比差异<br>`track_delete()` — 记录实例删除 |
| `event_dispatcher.py` | 123 | `dispatch_event()` — 分发事件到所有匹配的订阅 |
| `import_service.py` | 123 | `ImportService` — 批量导入/导出服务 |
| `neo4j_client.py` | Neo4j database client — 统一连接管理 | `Neo4jClient` — Neo4j 驱动单例管理器 |
| `node_service.py` | 123 | `NodeService` — 统一节点 CRUD<br>`now_iso()` |
| `sync_service.py` | 123 | `BaseCloudSync` — 云厂商资产同步基类<br>`AliyunSync` — 阿里云 ECS 同步<br>`TencentCloudSync` — 腾讯云 CVM 同步 |
| `topology_service.py` | feat(job-platform): complete backend + frontend implementation | `TopologyService` — 拓扑查询服务 |
| `validation_service.py` | ValidationService — 字段类型校验 + 唯一约束检查 | `ValidationService` — 字段校验服务 |

## `cmdb\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | CMDB views package |
| `association.py` | Association views — 关联类型 & 模型关联 & 实例关联管理 | `AssociationTypeViewSet` — 关联类型管理 (AssociationKind)<br>`ModelAssociationViewSet` — 模型关联管理<br>`InstanceAssociationViewSet` — 实例关联管理（Neo4j 关系操作） |
| `attribute_group.py` | AttributeGroup views — 属性分组管理 | `AttributeGroupViewSet` — 属性分组管理 |
| `classification.py` | Classification views — 模型分类管理 | `ClassificationViewSet` — 模型分类管理 |
| `event_subscription.py` | EventSubscriptionViewSet — 事件订阅管理 CRUD | `EventSubscriptionViewSet` — 事件订阅管理 |
| `import_export.py` | ImportExportViewSet — CMDB Excel 导入导出 API | `ImportExportViewSet` — CMDB Excel 导入导出 |
| `instance.py` | DynamicInstanceViewSet — 动态模型实例 CRUD（纯 Cypher 驱动） | `DynamicInstanceViewSet` — 动态模型实例 CRUD |
| `mainline_topo.py` | MainlineTopo views — 主线拓扑定义管理 | `MainlineTopoViewSet` — 主线拓扑定义管理 |
| `model_manage.py` | Model definition & field management views (MySQL CRUD) | `ModelDefinitionViewSet` — 模型定义管理<br>`ModelFieldViewSet` — 模型字段管理 |
| `object_unique.py` | ObjectUnique views — 唯一约束管理 | `ObjectUniqueViewSet` — 唯一约束管理 |
| `topology.py` | Topology views — 拓扑查询、影响分析、全局搜索 | `TopologyViewSet` — 拓扑视图（只读查询） |
