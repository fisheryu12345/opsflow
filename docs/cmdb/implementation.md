# CMDB — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐☆ (4/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | Neo4j 重构核心引擎就绪，但 Mock 数据未完全替换，Agent 自动发现未集成 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| 模型定义 (ModelDefinition) | P0 | ✅ | 资源模型定义 (Meta-model) | 完整：10个字段类型，classification分组，business FK，builtin保护 |
| 模型字段 (ModelField) | P0 | ✅ | 字段定义 | 完整：9类型(string/integer/float/boolean/date/datetime/enum/json/ip) |
| 模型关联 (ModelAssociation) | P0 | ✅ | 资源间关系定义 | 1:1/1:n/n:n 映射，双向 Cypher CRUD |
| 实例 CRUD (DynamicInstance) | P0 | ✅ | 任意模型实例管理 | 统一 DynamicInstanceViewSet + NodeService(Cypher)，任意 model_code |
| 拓扑查询 (TopologyService) | P0 | ✅ | 图查询/可视化 | tree/impact/full_topology/global_search 完整 |
| 变更追踪 (ChangeTracker) | P1 | ✅ | 资源变更历史 | 字段级 diff，EventSubscription webhook 通知 |
| Excel 导入导出 | P1 | ✅ | 批量导入导出 | openpyxl 实现，完整 round-trip |
| 变量系统 (CmdbQueryVariable) | P1 | ✅ | OpsFlow 变量集成 | 3 种变量：query/topology/count |
| 云资产同步 | P1 | ✅ | 云厂商资产同步 | Aliyun ECS 全地域分页(完整)；腾讯云(骨架)；AWS(仅 provider_choices) |
| Neo4j 引擎 | P0 | ✅ | Neo4j 图数据库驱动 | neo4j_client 连接池、纯 Cypher 操作、FTS 全文搜索 |
| 模型管理与字段定义 | P0 | ✅ | MySQL 模型元数据 | ModelDefinition + ModelField + AttributeGroup + ObjectUnique |
| Alliance/MainlineTopo | P1 | 🔄 | 主线模型 | 模型定义+视图就绪，但无前端树渲染端点 |
| Agent 自动发现 | P2 | 🔄 | ProcessManager 采集上报 | agent_app 采集完成(cpu/mem/disk/process)，Neo4j 写入完成，但 Process 模型和服务未完成 |
| 进程拓扑自动发现 | P2 | 🔄 | CALLS 关系发现 | agent_app._match_calls_topology 实现，增量更新未完成 |
| DR 站点拓扑 | P1 | 🔄 | DrSite/DrGroup 拓扑 | 种子数据已建，G6 力导向图渲染未完成 |
| AI DR Pipeline | P2 | 📅 | DR 切换流程自动生成 | CreateTemplateWizard DR 选项未建设 |
| K8s 集群模型同步 | P2 | 📅 | Kubernetes CMDB | — |
| 网络设备模型 | P2 | 📅 | Router/Switch/Firewall | — |
| WebSocket 拓扑协作 | P2 | 📅 | ws/cmdb/topology/ | — |
| 实例级 RBAC | P2 | 📅 | 字段级权限控制 | — |

## TODO

### P0
- [ ] 替换 8 组 Mock 数据为真实 Neo4j 查询
- [ ] Agent 自动发现全链路打通（collect → Neo4j → CMDB API）

### P1
- [ ] MainlineTopo 前端树图渲染
- [ ] 腾讯云/Huawei 云同步实现
- [ ] DR 拓扑 G6 可视化
- [ ] CMDB 自监控策略（Neo4j 健康检查）

### P2
- [ ] AI DR Pipeline 生成
- [ ] K8s CMDB 模型
- [ ] 网络设备模型
- [ ] 实例级 RBAC
