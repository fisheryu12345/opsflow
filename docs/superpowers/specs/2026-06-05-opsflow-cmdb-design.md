# OpsFlow CMDB 深度重构设计 — 参考 bk-cmdb 实现

> **日期:** 2026-06-05
> **状态:** v1 设计稿
> **对标:** 蓝鲸 bk-cmdb (Go + MongoDB) → OpsFlow CMDB (Django + Neo4j)

---

## 1. 背景与目标

### 1.1 为什么需要重构

现有 CMDB 使用 neomodel 定义了 5 种固定节点类型（Biz → Set → Module → Host → Process），硬编码在 Python `StructuredNode` 子类中。这意味着：

- 新增模型类型需要写 Python 代码 + 部署
- 字段变更需要修改 `StructuredNode` 定义
- 无法实现用户自定义模型（如"路由器"、"防火墙"、"数据库实例"）
- 无法实现动态关联类型

bk-cmdb 的核心思想是**模型驱动**：模型定义存储在元数据层，实例数据按模型定义动态生成，所有操作通过 API 完成，无需代码部署。

### 1.2 核心差异：MongoDB → Neo4j

| bk-cmdb (MongoDB) | OpsFlow CMDB (Neo4j) | 优势 |
|---|---|---|
| 实例存为 `map[string]interface{}` | 节点 Label = 模型 code | Label 原生支持按类型过滤 |
| 关联通过 `InstAsst` 集合存储 + lookup | 原生 Relationship + 类型属性 | 图遍历 O(1)，免 Join |
| 拓扑需递归查询 | `MATCH path = ()-[:CONTAINS*]->()` 原生 | 一行 Cypher 搞定全路径 |
| 影响分析需查多个集合 | 上下游遍历，O(depth) | 深度可控，毫秒级 |

---

## 2. 总体架构

### 2.1 四层架构

```
┌───────────────────────────────────────────────────────┐
│                    API Layer (DRF)                     │
│   Schema API (MySQL CRUD)  │ Instance API (Neo4j)     │
│   Topology API (Traversal) │ Sync API                 │
├───────────────────────────────────────────────────────┤
│                   Service Layer                        │
│   NodeService  │  AssociationService  │  TopoService   │
│   Validation   │  ImportService       │  CloudSync     │
├──────────────────┬────────────────────────────────────┤
│     MySQL        │            Neo4j                   │
│  (Schema 层)     │       (实例 + 关系层)               │
│                  │                                    │
│ Classification   │  Label: ModelDefinition.code        │
│ ModelDefinition  │  (:Biz, :Set, :Host, :Router, ...) │
│ ModelField       │  Property: ModelField.name → value │
│ AssociationType  │  RelType: AssociationType.asst_id  │
│ ModelAssociation │  (:CONTAINS, :RUNS, :DEPENDS_ON)   │
│ ObjectUnique     │  Unique constraint on property comb │
│ AttributeGroup   │  Index on searchable fields        │
│ MainlineTopo     │  Full-text index for global search │
└──────────────────┴────────────────────────────────────┘
```

### 2.2 技术选型

- **纯 Cypher 驱动** — 放弃 neomodel，所有节点/关系统一通过 `neo4j` Python Driver 直接执行 Cypher
- **MySQL + Neo4j 双数据源** — MySQL 存 Schema（模型定义），Neo4j 存实例数据
- **Django DATABASE_ROUTER** — 已有 `CmdbNeo4jRouter` 路由策略保留
- **完全重写** — 不保留任何现有 CMDB 代码（明确废弃的文件见第 6 节）

---

## 3. Schema 层（MySQL）

### 3.1 Classification（模型分类）

对标 bk-cmdb 的 `Classification`。用于对模型进行分组归类。

```python
class Classification(CoreModel):
    cls_id = CharField(max_length=128, unique=True)    # bk_classification_id
    name = CharField(max_length=255)                    # bk_classification_name
    icon = CharField(max_length=128, null=True)
    sort_order = IntegerField(default=0)
```

预置分类：`bk_host_manage`（主机管理）、`bk_biz_topo`（业务拓扑）、`bk_organization`（组织架构）、`bk_network`（网络）、`bk_uncategorized`（未分类）

### 3.2 ModelDefinition（模型定义）

对标 bk-cmdb 的 `Object`。每个 ModelDefinition 对应 Neo4j 中的一个 Label。

```python
class ModelDefinition(CoreModel):
    code = CharField(max_length=128, unique=True)       # bk_obj_id → Neo4j Label
    name = CharField(max_length=255)                    # bk_obj_name
    classification = FK(Classification, null=True)
    icon = CharField(max_length=128, null=True)
    description = TextField(null=True)
    is_builtin = BooleanField(default=False)            # 内置模型不可删除
    is_paused = BooleanField(default=False)             # 暂停使用
    source = CharField(choices=[('builtin','内置'), ('custom','自定义')])
```

内置模型（code/name）：`Biz/业务`、`Set/集群`、`Module/模块`、`Host/主机`、`Process/进程`

### 3.3 ModelField（模型字段）

对标 bk-cmdb 的 `Attribute`。定义模型实例的属性。

```python
class ModelField(CoreModel):
    model_definition = FK(ModelDefinition, related_name='fields')
    name = CharField(max_length=128)                    # bk_property_id
    label = CharField(max_length=255)                   # bk_property_name
    field_type = CharField(choices=FIELD_TYPE_CHOICES)  # string/int/float/enum/...
    required = BooleanField(default=False)
    is_unique = BooleanField(default=False)
    is_system = BooleanField(default=False)
    is_readonly = BooleanField(default=False)
    default_value = JSONField(null=True)
    options = JSONField(null=True)                      # enum 选项列表
    placeholder = CharField(max_length=512, null=True)
    sort_order = IntegerField(default=0)
    group = FK(AttributeGroup, null=True)               # 所属属性分组
    unit = CharField(max_length=64, null=True)          # 单位
    help_text = TextField(null=True)

    class Meta:
        unique_together = [['model_definition', 'name']]
```

字段类型支持：`string`、`integer`、`float`、`boolean`、`date`、`datetime`、`enum`、`json`、`ip`

### 3.4 AttributeGroup（属性分组）

对标 bk-cmdb `AttributeGroup`。前端展示时将字段分组展示。

```python
class AttributeGroup(CoreModel):
    model_definition = FK(ModelDefinition, related_name='attr_groups')
    group_id = CharField(max_length=128)                # 内部标识
    name = CharField(max_length=255)                    # 显示名
    sort_order = IntegerField(default=0)

    class Meta:
        unique_together = [['model_definition', 'group_id']]
```

### 3.5 AssociationType（关联类型）

对标 bk-cmdb `AssociationKind`。每个关联类型对应 Neo4j 的一种 Relationship Type。

```python
class AssociationType(CoreModel):
    asst_id = CharField(max_length=128, unique=True)    # bk_asst_id → RelType
    name = CharField(max_length=255)                    # bk_asst_name
    src_to_dest_note = CharField(max_length=255, null=True)
    dest_to_src_note = CharField(max_length=255, null=True)
    direction = CharField(choices=[
        ('none', '无方向'), ('src_to_dest', '源→目标'),
        ('dest_to_src', '目标→源'), ('bidirectional', '双向'),
    ])
```

预置关联类型：

| asst_id | name | 语义 |
|---|---|---|
| `BELONGS_TO` | 属于 | 实例归属关系 |
| `CONTAINS` | 包含 | 上层包含下层 |
| `RUNS` | 运行 | 主机运行进程 |
| `DEPENDS_ON` | 依赖 | 服务依赖关系 |
| `CONNECTS_TO` | 连接 | 网络连接关系 |

### 3.6 ModelAssociation（模型关联）

对标 bk-cmdb `Association`。定义哪些模型之间可以建立哪种关联。

```python
class ModelAssociation(CoreModel):
    source_model = FK(ModelDefinition, related_name='src_assocs')
    target_model = FK(ModelDefinition, related_name='tgt_assocs')
    association_type = FK(AssociationType)
    mapping = CharField(choices=[('1:1','一对一'),('1:n','一对多'),('n:n','多对多')])
    on_delete = CharField(choices=[('none','无操作'),('delete_target','删除目标')])
    alias_name = CharField(max_length=255, null=True)
    is_pre = BooleanField(default=False)

    class Meta:
        unique_together = [['source_model', 'target_model', 'association_type']]
```

预置模型关联：

| source | target | type | mapping |
|---|---|---|---|
| Biz | Set | CONTAINS | 1:n |
| Set | Module | CONTAINS | 1:n |
| Module | Host | CONTAINS | 1:n |
| Host | Process | RUNS | 1:n |
| Process | Process | DEPENDS_ON | n:n |

### 3.7 ObjectUnique（唯一约束）

对标 bk-cmdb `ObjectUnique`。一个或多个字段组合值的唯一性约束。

```python
class ObjectUnique(CoreModel):
    model_definition = FK(ModelDefinition)
    keys = JSONField()                 # ["field1", "field2"]
    is_pre = BooleanField(default=False)

    class Meta:
        unique_together = [['model_definition', 'keys']]
```

### 3.8 MainlineTopo（主线拓扑）

对标 bk-cmdb 的主线概念。定义业务拓扑的层级链：Biz → Set → Module → Host。

```python
class MainlineTopo(CoreModel):
    model_definition = FK(ModelDefinition, unique=True)
    parent_model = FK(ModelDefinition, null=True, related_name='children')
    sort_order = IntegerField(default=0)
```

---

## 4. 实例层（Neo4j）— 纯 Cypher

### 4.1 节点契约

所有 CMDB 节点（无论内置/自定义）遵循统一结构：

```cypher
CREATE (n:ModelLabel {
  instance_id:   "uuid-v4",                // 全局唯一 ID（必填）
  __model_code:  "Biz",                    // 指向 ModelDefinition.code
  __created_at:  "2026-06-05T10:00:00Z",   // 创建时间
  __updated_at:  "2026-06-05T10:00:00Z",   // 更新时间

  // ↓ 以下为动态属性，由 ModelField 定义决定
  name:          "电商业务",
  lifecycle:     "生产",
  operator:      "张三",
  description:   "核心电商平台"
})
```

- `instance_id` 作为统一主键，所有模型类型通用
- `__model_code` 用于反向查找该节点属于哪个 ModelDefinition
- 系统字段（以 `__` 开头）不可通过 API 直接修改

### 4.2 关系契约

```cypher
(a:Biz {instance_id: $src})
-[r:CONTAINS {                             // 关系类型 = AssociationType.asst_id
  rel_id:        "uuid-v4",                // 关系唯一 ID
  __asst_type:   "CONTAINS",              // 指向 AssociationType.asst_id
  __created_at:  "2026-06-05T10:00:00Z",
  src_model:     "Biz",                   // 源节点 model_code
  dst_model:     "Set"                    // 目标节点 model_code
}]->(b:Set {instance_id: $dst})
```

- 关系类型（`:CONTAINS`、`:RUNS` 等）直接从 `AssociationType.asst_id` 动态生成
- `__asst_type` 用于反向查找该关系属于哪个 AssociationType
- 级联删除逻辑：删除节点时，根据 `ModelAssociation.on_delete` 决定是否级联删除关联节点

### 4.3 NodeService（统一节点 CRUD）

```python
class NodeService:
    """所有 CMDB 节点的统一 CRUD"""

    def __init__(self, model_code: str):
        # model_code → ModelDefinition.code → Neo4j Label
        self.model_code = model_code
        self.model_def = ModelDefinition.objects.get(code=model_code)

    def create(self, data: dict) -> dict:
        """创建节点 —— 校验字段类型 → 校验唯一约束 → 构造 Cypher CREATE"""
        validated = ValidationService(self.model_def).validate(data)
        validated['instance_id'] = str(uuid4())
        validated['__model_code'] = self.model_code
        validated['__created_at'] = now_iso()
        validated['__updated_at'] = now_iso()
        cypher = f"CREATE (n:{self.model_code} $props) RETURN n"
        with graph_driver.session() as s:
            result = s.run(cypher, props=validated)
            return self._node_to_dict(result.single()[0])

    def list(self, filters: dict, page=1, page_size=20,
             order_by=None) -> dict:
        """列表查询 —— 支持字段过滤、分页、排序"""
        conditions = self._build_conditions(filters)
        cypher = f"""
            MATCH (n:{self.model_code})
            WHERE {' AND '.join(conditions) if conditions else '1=1'}
            RETURN n
            SKIP $skip LIMIT $limit
        """
        ...

    def retrieve(self, instance_id: str) -> dict:
        cypher = f"MATCH (n:{self.model_code} {{instance_id: $id}}) RETURN n"

    def update(self, instance_id: str, data: dict) -> dict:
        """更新 —— 校验 → 动态 SET"""
        ...

    def delete(self, instance_id: str):
        """删除节点 + 级联处理关联关系"""
        ...
```

### 4.4 AssociationService（关联管理）

```python
class AssociationService:
    """实例关联管理"""

    def create_relation(self, src_id: str, dst_id: str, asst_type: str):
        """创建实例间关联"""
        cypher = """
            MATCH (src {instance_id: $src_id})
            MATCH (dst {instance_id: $dst_id})
            CREATE (src)-[r:{asst_type} {
                rel_id: $rel_id, __asst_type: $asst_type,
                __created_at: $now,
                src_model: src.__model_code,
                dst_model: dst.__model_code
            }]->(dst)
            RETURN r
        """

    def delete_relation(self, rel_id: str):
        """按 rel_id 删除关系"""
        cypher = "MATCH ()-[r {rel_id: $rel_id}]->() DELETE r"

    def list_relations(self, instance_id: str = None,
                       asst_type: str = None,
                       src_model: str = None, dst_model: str = None,
                       page=1, page_size=20) -> dict:
        """按条件查询实例关联"""
        ...

    def get_neighbors(self, instance_id: str,
                      direction='both', max_depth=1,
                      asst_types: list[str] = None) -> dict:
        """获取邻接节点（图遍历）"""
        dir_symbol = {'out': '->', 'in': '<-', 'both': '-'}[direction]
        type_filter = f"|{':'.join(asst_types)}" if asst_types else ''
        cypher = f"""
            MATCH path = (n {{instance_id: $id}})
                         -[{dir_symbol}[r{type_filter}]*1..{max_depth}]-()
            RETURN ...
        """
```

### 4.5 TopologyService（拓扑查询）

```python
class TopologyService:
    """拓扑、影响分析、全局搜索"""

    def get_tree(self, root_id: str, max_depth=5) -> dict:
        """以 root_id 为根展开子树"""
        cypher = """
            MATCH path = (root {instance_id: $root_id})
                         -[:CONTAINS*0..$depth]->(descendant)
            RETURN ...
        """

    def get_impact(self, instance_id: str, direction='downstream',
                   max_depth=5) -> dict:
        """影响分析 —— 某节点故障时受影响的上/下游"""
        dir_sym = '->' if direction == 'downstream' else '<-'
        cypher = f"""
            MATCH path = (src {{instance_id: $id}})
                         -[{dir_sym}*1..{max_depth}]->(affected)
            RETURN affected, length(path) as depth
            ORDER BY depth
        """

    def global_search(self, query: str, model_codes: list = None,
                      limit=50) -> list:
        """全局搜索 —— 利用 CONTAINS 模糊匹配所有字符串属性"""
        # 方案 A：遍历每个字段做 CONTAINS
        # 方案 B：Neo4j 全文索引
        ...

    def full_topology(self) -> dict:
        """全局力导向图数据 —— 所有节点+关系"""
        cypher = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]->(m)
            RETURN n, r, m
        """
        return {'nodes': [...], 'edges': [...]}
```

### 4.6 ValidationService（字段校验）

```python
class ValidationService:
    """字段类型校验 + 唯一约束检查"""

    def __init__(self, model_def: ModelDefinition):
        self.model_def = model_def
        self.fields = {
            f.name: f for f in model_def.fields.all()
        }
        self.uniques = ObjectUnique.objects.filter(
            model_definition=model_def
        )

    def validate(self, data: dict) -> dict:
        """校验输入数据：
        1. 必填字段检查
        2. 字段类型转换（如 "123" → 123 via int）
        3. enum 选项校验
        4. 唯一约束检查（查询 Neo4j 已有值）
        """
        validated = {}
        for name, field in self.fields.items():
            value = data.get(name, field.default_value)
            if value is None and field.required:
                raise ValidationError(f'{field.label} 为必填')
            validated[name] = self._cast(value, field.field_type)
            if field.is_unique:
                self._check_unique(name, value)
        return validated
```

### 4.7 ImportService（批量导入）

```python
class ImportService:
    """CSV/JSON 批量导入"""

    def import_instances(self, model_code: str,
                         records: list[dict],
                         strategy='create_or_update') -> dict:
        """批量写入 —— UNWIND + MERGE 单事务"""
        cypher = f"""
            UNWIND $records AS rec
            MERGE (n:{model_code} {{instance_id: rec.instance_id}})
            SET n += rec
            RETURN count(n) as total
        """

    def import_relations(self, relations: list[dict]) -> dict:
        """批量导入关联"""
        cypher = """
            UNWIND $rels AS r
            MATCH (src {instance_id: r.src_id})
            MATCH (dst {instance_id: r.dst_id})
            CALL apoc.merge.relationship(src, r.type, {}, {}, dst)
            YIELD rel
            RETURN count(rel) as total
        """
```

---

## 5. API 层

### 5.1 路由表

所有路由前缀 `/api/cmdb/`。

| Method | URL | ViewSet | 说明 |
|---|---|---|---|
| CRUD | `/classifications/` | ClassificationViewSet | 分类管理 |
| CRUD | `/model-definitions/` | ModelDefinitionViewSet | 模型定义 |
| CRUD | `/model-definitions/{pk}/fields/` | ModelFieldViewSet | 模型字段（Nested） |
| CRUD | `/attribute-groups/` | AttributeGroupViewSet | 属性分组 |
| CRUD | `/association-types/` | AssociationTypeViewSet | 关联类型 |
| CRUD | `/model-associations/` | ModelAssociationViewSet | 模型关联定义 |
| CRUD | `/object-uniques/` | ObjectUniqueViewSet | 唯一约束 |
| CRUD | `/mainline-topos/` | MainlineTopoViewSet | 主线拓扑 |
| POST/GET/PUT/DEL | `/instances/{model_code}/` | DynamicInstanceViewSet | 动态实例 CRUD |
| POST | `/instance-associations/` | InstanceAssociationViewSet | 创建实例关联 |
| GET | `/instance-associations/` | .. | 查询实例关联 |
| GET | `/topology/tree/` | TopologyViewSet | 业务拓扑树 |
| GET | `/topology/impact/` | .. | 影响分析 |
| GET | `/topology/search/` | .. | 全局搜索 |
| GET | `/topology/graph/` | .. | 全局力导向图 |

### 5.2 响应格式

统一使用 `DetailResponse` / `ErrorResponse` / `SuccessResponse`：

```json
// 成功（无分页）
{ "code": 2000, "data": {...}, "msg": "success" }

// 成功（有分页）
{ "code": 2000, "data": [...], "total": 42, "page": 1, "limit": 20, "msg": "success" }

// 业务错误
{ "code": 4000, "data": null, "msg": "实例 xxx 不存在" }
```

---

## 6. 文件变更清单

### 6.1 新增文件

```
backend/cmdb/
├── models/
│   ├── __init__.py              # 导出所有模型
│   ├── classification.py
│   ├── model_definition.py      # ModelDefinition + ModelField
│   ├── attribute_group.py
│   ├── association.py           # AssociationType + ModelAssociation
│   ├── object_unique.py
│   └── mainline_topo.py
├── services/
│   ├── __init__.py
│   ├── node_service.py
│   ├── association_service.py
│   ├── topology_service.py
│   ├── validation_service.py
│   ├── import_service.py
│   ├── sync_service.py          # 云同步框架
│   └── neo4j_client.py          # 统一 Neo4j 驱动连接管理
├── views/
│   ├── __init__.py
│   ├── classification.py
│   ├── model_manage.py
│   ├── association.py
│   ├── instance.py              # DynamicInstanceViewSet
│   └── topology.py
├── serializers/
│   ├── __init__.py
│   ├── schema_serializers.py    # MySQL 模型序列化器
│   └── instance_serializers.py  # Neo4j 实例序列化器
├── management/
│   └── commands/
│       └── seed_cmdb_models.py  # 种子数据管理命令
├── urls.py
├── apps.py
├── admin.py
└── __init__.py
```

### 6.2 删除文件

```
backend/cmdb/models/node_types.py         # neomodel StructuredNode
backend/cmdb/models/model_schema.py       # 旧的 ModelDefinition/Field
backend/cmdb/views/base.py                # Neo4jViewSet
backend/cmdb/views/biz.py                 # 固定 Biz/Set/Module ViewSet
backend/cmdb/views/host.py                # 固定 Host ViewSet
backend/cmdb/serializers.py               # 旧序列化器
backend/cmdb/services/topology_service.py # 旧拓扑服务
backend/cmdb/services/sync_service.py     # 旧同步服务
```

### 6.3 迁移文件

```
backend/cmdb/migrations/         # 保留已有 migration，新增 0002_...
```

---

## 7. 预置种子数据

`seed_cmdb_models` 管理命令自动创建：

### 7.1 分类

| cls_id | name |
|---|---|
| bk_biz_topo | 业务拓扑 |
| bk_host_manage | 主机管理 |
| bk_organization | 组织架构 |
| bk_network | 网络设备 |
| bk_uncategorized | 未分类 |

### 7.2 内置模型（5个）

| code | name | classification | 主字段 |
|---|---|---|---|
| Biz | 业务 | bk_biz_topo | name, lifecycle, operator, description |
| Set | 集群 | bk_biz_topo | name, env_type(生产/测试/开发), description |
| Module | 模块 | bk_biz_topo | name, service_type(web/db/cache/mq/lb/other) |
| Host | 主机 | bk_host_manage | ip, hostname, os_type, cpu_cores, memory_mb, disk_gb, status, agent_status, cloud_instance_id, private_ip, public_ip, region |
| Process | 进程 | bk_host_manage | name, port, protocol, status, version |

### 7.3 预置关联

同上「预置模型关联」表格。

---

## 8. OpsFlow Pipeline 集成

### 8.1 资源选择器 Plugin

在工作流节点中，用户可以从 CMDB 选择目标主机：

```python
# backend/opsflow/plugins/cmdb/resource_selector.py

class CmdbResourceSelector(BasePlugin):
    """CMDB 资源选择器"""
    code = 'cmdb_resource_selector'
    name = 'CMDB 资源选择器'

    def get_form_config(self):
        return [
            FormItem(type='resource_selector', tag_code='targets',
                     attrs={'model_code': 'Host',
                            'filters': ['biz', 'module', 'labels']})
        ]

    def execute(self, **kwargs):
        targets = kwargs['targets']
        # targets 是前端的资源选择器配置
        # 通过 CMDB API 解析为具体主机列表
        return TopologyService().resolve_targets(targets)
```

### 8.2 CMDB 查询变量

```python
# backend/opsflow/core/variables/cmdb_variables.py

class CmdbQueryVariable(BaseVariable):
    code = 'cmdb_query'
    name = 'CMDB 查询'
    def get_value(self, context):
        return NodeService(context['model_code']).query(context['filters'])
```

### 8.3 CMDB 变更事件

```
CMDB 数据变更 (create/update/delete)
    → 发送 Webhook 或消息队列
    → 触发 OpsFlow Pipeline 执行
    → 场景：新主机上线 → 自动触发初始化流程
```

---

## 9. 前端架构

### 9.1 页面结构

| 标签页 | 功能 | 核心组件 |
|---|---|---|
| 模型管理 | 分类/模型/字段/关联的配置 | ModelDefTable, FieldEditor, AssocGraph |
| 实例管理 | 动态 CRUD + 批量导入 | DynamicTable, ImportDialog |
| 拓扑视图 | 力导向图 + 影响分析 + 搜索 | TopoCanvas, ImpactPanel, SearchBar |
| 数据同步 | 云资产同步 + 导入导出 | SyncPanel |

### 9.2 动态表格组件

```vue
<!-- DynamicInstanceTable.vue -->
<!-- 根据 ModelDefinition + ModelField 自动渲染 CRUD 表格 -->

<template>
  <el-table>
    <el-table-column v-for="field in fields" :key="field.name">
      <!-- 根据 field.field_type 选择控件 -->
      <template v-if="field.field_type === 'string'">
        <el-input v-model="row[field.name]" />
      </template>
      <template v-else-if="field.field_type === 'integer'">
        <el-input-number v-model="row[field.name]" />
      </template>
      <template v-else-if="field.field_type === 'enum'">
        <el-select v-model="row[field.name]">
          <el-option v-for="opt in field.options" :key="opt"
                     :label="opt" :value="opt" />
        </el-select>
      </template>
      <!-- ... -->
    </el-table-column>
  </el-table>
</template>
```

### 9.3 拓扑画布

基于 G6 或 cytoscape.js：
- 力导向布局展示全局拓扑
- 节点颜色 = `status` 字段（正常/告警/维护/下线）
- 右击菜单：查看详情/影响分析/编辑
- 滚轮缩放 + 拖拽平移
- 搜索高亮

### 9.4 Pinia Store

```typescript
// stores/cmdb.ts
state: {
  classifications, modelDefinitions, modelFields,
  associationTypes, modelAssociations,
  currentModel: ModelDefinition | null,
  topology: { nodes: TopoNode[], edges: TopoEdge[] },
  impactResult: ImpactResult | null,
  searchResults: SearchResult[],
}
```

### 9.5 API 层

```typescript
// api/cmdb/index.ts
const API_BASE = '/api/cmdb'

// Schema API
export const classifications = createCrudApi(`${API_BASE}/classifications`)
export const modelDefinitions = createCrudApi(`${API_BASE}/model-definitions`)

// 动态实例 API
export function getInstances(modelCode: string, params?: any) {
  return request.get(`${API_BASE}/instances/${modelCode}/`, { params })
}
export function createInstance(modelCode: string, data: any) {
  return request.post(`${API_BASE}/instances/${modelCode}/`, data)
}
export function updateInstance(modelCode: string, id: string, data: any) { ... }
export function deleteInstance(modelCode: string, id: string) { ... }

// 拓扑 API
export function getTopology() { return request.get(`${API_BASE}/topology/graph/`) }
export function getImpact(nodeId: string) { ... }
export function searchNodes(q: string) { ... }
```

---

## 10. 实现计划

### Phase 1（后端核心 — MySQL Schema + Neo4j 基础）

1. 创建 8 个 MySQL model 定义 + migration
2. 实现 `neo4j_client.py`（连接管理 + 会话上下文）
3. 实现 `ValidationService`
4. 实现 `NodeService` CRUD
5. 实现 `AssociationService`
6. 实现 `TopologyService`
7. 实现序列化器
8. 实现所有 ViewSet + URL 路由
9. 删除废弃文件
10. 实现 `seed_cmdb_models` 管理命令
11. 删除旧 migration 并重建初始 migration

### Phase 2（前端）

1. API 层 TypeScript 封装
2. 模型管理页面（分类/模型/字段/关联配置）
3. 实例管理页面（动态表格组件）
4. 拓扑视图页面（G6 画布 + 影响分析 + 搜索）
5. 数据同步页面（导入/导出）
6. Pinia store

### Phase 3（Pipeline 集成 + 同步）

1. 资源选择器 Plugin
2. CMDB 查询变量
3. 变更事件 Webhook
4. 云同步框架实现

---

## 11. 验证方式

1. `python manage.py migrate cmdb` — migration 成功
2. `python manage.py seed_cmdb_models` — 5 个内置模型 + 字段入库
3. API 测试流程：
   - 创建 Classification → 创建 ModelDefinition → 创建 ModelField
   - 创建实例（带校验）→ 创建关联 → 查询拓扑
   - 影响分析 → 全局搜索 → 批量导入
4. 前端验证：
   - 模型管理页配置自定义模型（如"Router"）
   - 实例管理页 CRUD
   - 拓扑图展示 + 影响分析
5. 级联删除测试：
   - 创建 Biz → Set → Module → Host 链
   - 删除 Biz → 级联删除下游
   - 验证 Neo4j 中是否干净

---

## 12. 与 bk-cmdb 的关键差异总结

| 方面 | bk-cmdb (MongoDB) | OpsFlow CMDB (Neo4j) |
|---|---|---|
| 实例存储 | `map[string]interface{}` + collection | Cypher Label + Property |
| 关联存储 | `InstAsst` 集合 + lookup | Native Relationship |
| 拓扑查询 | 递归查询集合 | `MATCH path = ()-[:TYPE*]->()` |
| 唯一约束 | MongoDB unique index | Neo4j composite constraint |
| 全文搜索 | MongoDB text index | Neo4j fulltext index |
| ORM | MongoDB Go Driver | Pure Cypher（无 ORM） |
| 模型定义动态性 | 数据驱动 | Label + Cypher 动态驱动 |
