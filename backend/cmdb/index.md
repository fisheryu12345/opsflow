# cmdb — 模块索引

> 上次自动更新: 2026-06-23 | 触发提交: d7aa8dd1

---

## 根目录

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | CMDB app package | (直接函数) |
| `admin.py` | Admin registration for CMDB MySQL models | `ClassificationAdmin` — ; `ModelFieldInline` — ; `ModelDefinitionAdmin` — ; `ModelFieldAdmin` — ; `AttributeGroupAdmin` —  |
| `apps.py` | AppConfig for cmdb app | `CmdbConfig` —  |
| `neo4j_router.py` | Django database router for Neo4j dual datasource | `CmdbNeo4jRouter` — Django 多数据库路由 |
| `urls.py` | URL configuration for CMDB app | (直接函数) |

## `management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management\__init__.py` | Management commands for cmdb app | (直接函数) |

## `management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management\commands\__init__.py` | Management commands package | (直接函数) |
| `management\commands\seed_dr_models.py` | Seed DR baseline models: Process model definition + AssociationTypes + Mock data. | `Command` —  |

## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `models\__init__.py` | Re-export all CMDB models | (直接函数) |
| `models\association.py` | Association models — 关联类型 & 模型关联，对标 bk-cmdb AssociationKind & Association | `AssociationType` — 关联类型 (AssociationKind); `ModelAssociation` — 模型关联 (Association) |
| `models\attribute_group.py` | AttributeGroup — 属性分组，对标 bk-cmdb AttributeGroup | `AttributeGroup` — 属性分组 (AttributeGroup) |
| `models\change_log.py` | CMDB change log model — 记录模型实例的变更历史 | `ChangeLog` — CMDB 变更日志 |
| `models\classification.py` | Classification model — 模型分类，对标 bk-cmdb Classification | `Classification` — 模型分类 (Classification) |
| `models\cloud_sync_log.py` | CloudSyncLog — 云资产同步日志 | `CloudSyncLog` — 云厂商资产同步执行记录 |
| `models\event_subscription.py` | CMDB event subscription model — 实例变更事件的订阅配置 | `EventSubscription` — CMDB 事件订阅 |
| `models\mainline_topo.py` | MainlineTopo — 主线拓扑定义，对标 bk-cmdb 主线概念 | `MainlineTopo` — 主线拓扑定义 (MainlineTopo) |
| `models\model_definition.py` | ModelDefinition & ModelField — 模型定义和字段，对标 bk-cmdb Object & Attribute | `ModelDefinition` — 模型定义 (Model/Object); `ModelField` — 模型字段定义 (Attribute) |
| `models\object_unique.py` | ObjectUnique — 唯一约束，对标 bk-cmdb ObjectUnique | `ObjectUnique` — 唯一约束 (ObjectUnique) |

## `serializers/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `serializers\__init__.py` | Re-export all serializers | (直接函数) |
| `serializers\instance_serializers.py` | Serializers for Neo4j dynamic instances | `DynamicInstanceSerializer` — 动态实例序列化器; `InstanceRelationSerializer` — 实例关联序列化器 |
| `serializers\schema_serializers.py` | Serializers for MySQL schema models (CoreModel subclasses) | `ClassificationSerializer` — ; `ClassificationCreateUpdateSerializer` — ; `ModelDefinitionSerializer` — ; `ModelDefinitionCreateUpdateSerializer` — ; `ModelFieldSerializer` —  |

## `services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `services\__init__.py` | Services package for CMDB app | (直接函数) |
| `services\association_service.py` |  | `AssociationService` — 实例关联管理 |
| `services\change_tracker.py` |  | `track_create()` — 记录实例创建; `track_update()` — 记录实例更新 — 逐字段对比差异; `track_delete()` — 记录实例删除 |
| `services\event_dispatcher.py` |  | `dispatch_event()` — 分发事件到所有匹配的订阅 |
| `services\import_service.py` |  | `ImportService` — 批量导入/导出服务 |
| `services\neo4j_client.py` | Neo4j database client — 统一连接管理 | `Neo4jClient` — Neo4j 驱动单例管理器 |
| `services\node_service.py` |  | `NodeService` — 统一节点 CRUD; `now_iso()` —  |
| `services\sync_service.py` |  | `BaseCloudSync` — 云厂商资产同步基类; `AliyunSync` — 阿里云 ECS 同步 — 全地域; `TencentCloudSync` — 腾讯云 CVM 同步 |
| `services\topology_service.py` |  | `TopologyService` — 拓扑查询服务 |
| `services\validation_service.py` | ValidationService — 字段类型校验 + 唯一约束检查 | `ValidationService` — 字段校验服务 |

## `variable_types/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `variable_types\__init__.py` | CMDB 变量类型包 — 导入此模块触发变量类注册到 VARIABLE_REGISTRY | (直接函数) |
| `variable_types\count.py` | CMDB 计数变量 — 统计指定模型的实例数量 | `CmdbCountVariable` — CMDB 计数变量 — 统计指定模型的实例数量 |
| `variable_types\query.py` | CMDB 实例查询变量 — 按条件查询 CMDB 模型实例 | `CmdbQueryVariable` — CMDB 实例查询变量 — 按条件查询 CMDB 模型实例 |
| `variable_types\topology.py` | CMDB 拓扑查询变量 — 获取实例的上/下游拓扑路径 | `CmdbTopologyVariable` — CMDB 拓扑查询变量 — 获取实例的上/下游拓扑路径 |

## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views\__init__.py` | CMDB views package | (直接函数) |
| `views\association.py` | Association views — 关联类型 & 模型关联 & 实例关联管理 | `AssociationTypeViewSet` — 关联类型管理 (AssociationKind); `ModelAssociationViewSet` — 模型关联管理; `InstanceAssociationViewSet` — 实例关联管理（Neo4j 关系操作） |
| `views\attribute_group.py` | AttributeGroup views — 属性分组管理 | `AttributeGroupViewSet` — 属性分组管理 |
| `views\classification.py` | Classification views — 模型分类管理 | `ClassificationViewSet` — 模型分类管理 |
| `views\cloud_sync_views.py` | Cloud Sync API — 云资产同步状态查询 & 手动触发 | `list_providers()` — 列出已注册的云厂商及其连接器状态; `sync_status()` — 获取指定云厂商的最新同步状态; `trigger_sync()` — 手动触发全量同步; `sync_history()` — 获取同步历史记录（分页） |
| `views\event_subscription.py` | EventSubscriptionViewSet — 事件订阅管理 CRUD | `EventSubscriptionViewSet` — 事件订阅管理 |
| `views\import_export.py` | ImportExportViewSet — CMDB Excel 导入导出 API | `ImportExportViewSet` — CMDB Excel 导入导出 |
| `views\instance.py` | DynamicInstanceViewSet — 动态模型实例 CRUD（纯 Cypher 驱动） | `DynamicInstanceViewSet` — 动态模型实例 CRUD |
| `views\mainline_topo.py` | MainlineTopo views — 主线拓扑定义管理 | `MainlineTopoViewSet` — 主线拓扑定义管理 |
| `views\model_manage.py` | Model definition & field management views (MySQL CRUD) | `ModelDefinitionViewSet` — 模型定义管理; `ModelFieldViewSet` — 模型字段管理 |
| `views\object_unique.py` | ObjectUnique views — 唯一约束管理 | `ObjectUniqueViewSet` — 唯一约束管理 |
| `views\topology.py` | Topology views — 拓扑查询、影响分析、全局搜索、AI 布局 | `TopologyViewSet` — 拓扑视图（只读查询） |

