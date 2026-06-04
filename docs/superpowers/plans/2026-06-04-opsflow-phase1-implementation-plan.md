# OpsFlow 智能运维平台 · Phase 1 实施计划

> 基于架构设计文档生成：`docs/superpowers/specs/2026-06-04-opsflow-platform-architecture-design.md`

---

## 1. 总览

**Phase 1 目标**：打通"发现→流程→执行→沉淀"完整链路

| 度量 | 值 |
|------|-----|
| 新建 Django App | 7 个 (cmdb / itsm / monitor / integration / job_platform / portal / open_api) |
| 新增后端文件 | ~100+ (模型/视图/序列化器/服务/适配器) |
| 新增前端页面 | ~30+ |
| 预计工期 | ~10 周 |
| 统一代码规范 | CoreModel + CustomModelViewSet + CustomModelSerializer |

---

## 2. 开发顺序（依赖驱动）

```
                    ┌──────────────────┐
                    │  集成中心 (P0)    │ ← Phase 1 启动点，无外部依赖
                    │  integration     │     其他模块通过集成中心调用外部系统
                    └────────┬─────────┘
                             │ 提供云同步/通知通道
                             ▼
              ┌──────────────────────────────┐
              │     CMDB (P0)                │ ← 数据底座，依赖集成中心云同步
              │     业务/集群/模块/主机/进程  │     所有模块依赖 CMDB 资产数据
              └────────┬──────────┬──────────┘
                       │          │
          ┌────────────┘          └────────────┐
          ▼                                    ▼
  ┌─────────────────┐                ┌─────────────────┐
  │  ITSM (P0)      │                │  Monitor (P0)   │
  │  事件/变更/     │                │  告警收敛/      │
  │  SLA/工单       │                │  Grafana联动    │
  │  依赖CMDB资产   │                │  依赖CMDB+集成  │
  └────────┬────────┘                └────────┬────────┘
           │                                   │
           │              ┌────────────────────┘
           │              │
  ┌────────▼──────────────▼──────────────────────┐
  │  作业平台 (P1)                                │
  │  批量执行/文件分发/高危拦截                    │
  │  依赖 CMDB 目标主机 + 集成中心执行通道         │
  └──────────────────────┬───────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
  ┌─────────────────┐         ┌─────────────────┐
  │  运维门户 (P1)   │         │  Open API (P1)  │
  │  聚合各模块数据   │         │  外部系统集成接口 │
  │  其余模块完成后   │         │  各模块完成后封装 │
  └─────────────────┘         └─────────────────┘
```

### 开发批次划分

| 批次 | App | 前置 | 工期 | 可并行 |
|------|-----|------|------|--------|
| **Batch 1** | 集成中心 | 无 | 2 周 | - |
| **Batch 2** | CMDB | 集成中心 | 3 周 | Batch1 结束后启动 |
| **Batch 3** | ITSM + Monitor | CMDB | 3 周 | 可并行开发 |
| **Batch 4** | 作业平台 | CMDB + 集成中心 | 2 周 | Batch3 同期可启动 |
| **Batch 5** | 运维门户 + Open API | 所有模块 | 1.5 周 | 可并行 |

---

## 3. 详细任务拆解

### Batch 1：集成中心 (integration) — 2 周

**后端（第 1 周）：**

| 任务 | 文件 | 说明 |
|------|------|------|
| App 骨架 | `__init__.py`, `apps.py`, `admin.py` | 基础配置 |
| 连接器定义模型 | `models/connector.py` | `ConnectorDefinition` + `ConnectorInstance`（CoreModel） |
| 凭证模型 | `models/credential.py` | `ConnectorCredential`（AES-256 加密字段） |
| 调用审计模型 | `models/integration_log.py` | `IntegrationLog`（CoreModel） |
| 模型 __init__ | `models/__init__.py` | 重新导出 |
| 连接器 ViewSet | `views/connector.py` | CRUD + 启停+健康检查动作 |
| 凭证 ViewSet | `views/credential.py` | CRUD + 加密存储/解密展示 |
| 日志 ViewSet | `views/integration_log.py` | 只读列表/详情 |
| 序列化器 | `serializers.py` | 各模型对应的 3-4 个序列化器 |
| 路由 | `urls.py` | SimpleRouter 注册 |
| 适配器基类 | `adapters/base.py` | `BaseConnector` 抽象类 + health_check / get_client |
| 凭证服务 | `services/credential_service.py` | AES 加密/解密工具 |
| 健康检查服务 | `services/health_service.py` | 定时健康检查调度 |

**后端（第 2 周）：适配器实现**

| 任务 | 文件 | 说明 |
|------|------|------|
| 阿里云适配器 | `adapters/cloud/aliyun.py` | ECS SDK 封装 |
| 腾讯云适配器 | `adapters/cloud/tencent.py` | CVM SDK 封装 |
| 短信适配器 | `adapters/notification/sms.py` | 阿里云短信网关 |
| 邮件适配器 | `adapters/notification/mail.py` | SMTP 封装 |
| 企微适配器 | `adapters/notification/wecom.py` | Webhook Bot |
| LDAP 适配器 | `adapters/auth/ldap.py` | 认证源 |

**前端（并行）：**

| 任务 | 文件 | 说明 |
|------|------|------|
| 连接器市场页面 | `views/integration/` | 浏览/安装连接器 |
| 实例管理页面 | `views/integration/` | 配置/启停/健康状态 |
| 凭证管理页面 | `views/integration/` | 加密存储/过期提醒 |
| 调用监控页面 | `views/integration/` | 实时调用量+成功率 |
| API 封装 | `api/integration.ts` | Axios CRUD 封装 |

---

### Batch 2：CMDB — 3 周

**第 1 周：数据模型**

| 任务 | 文件 | 说明 |
|------|------|------|
| App 骨架 | `apps.py`, `admin.py` | AppConfig |
| 模型 schema（MySQL） | `models/model_schema.py` | 模型定义、字段定义（CoreModel） |
| Neo4j 节点定义 | `models/node_types.py` | Biz/Set/Module/Host/Process（StructuredNode） |
| 模型 __init__ | `models/__init__.py` | 导出 |
| 双数据源路由 | `neo4j_router.py` | Django database router |
| 序列化器 | `serializers.py` | MySQL 模型 + Neo4j 节点序列化器 |

**第 2 周：核心 API**

| 任务 | 文件 | 说明 |
|------|------|------|
| 业务 ViewSet | `views/biz.py` | 业务 CRUD + 拓扑展开动作 |
| 主机 ViewSet | `views/host.py` | 主机 CRUD + 批量导入动作 |
| 拓扑 ViewSet | `views/topology.py` | 拓扑查询 + 影响分析 |
| 模型管理 ViewSet | `views/model_manage.py` | 自定义模型/字段 CRUD |
| 路由 | `urls.py` | 注册 4 个 ViewSet + path 额外动作 |

**第 3 周：服务层 + 前端**

| 任务 | 文件 | 说明 |
|------|------|------|
| 云资产同步服务 | `services/sync_service.py` | 通过集成中心同步云资产 |
| 拓扑服务 | `services/topology_service.py` | 图遍历查询封装 |
| 业务管理页面 | `views/cmdb/biz/` | 业务树，CRUD |
| 主机管理页面 | `views/cmdb/host/` | 主机列表，批量操作 |
| 拓扑视图 | `views/cmdb/topology/` | D3.js/vis.js 力导向图 |
| 模型管理页面 | `views/cmdb/model/` | 自定义模型配置 |
| API 封装 | `api/cmdb.ts` | 与后端对应 |

---

### Batch 3：ITSM — 3 周

**第 1 周：模型 + 状态机**

| 任务 | 文件 | 说明 |
|------|------|------|
| App 骨架 | `apps.py`, `admin.py` | |
| 事件工单模型 | `models/incident.py` | Incident（CoreModel），含 CMDB 关联字段 |
| 变更模型 | `models/change.py` | Change（CoreModel），含 CAB 审批关联 |
| 服务请求模型 | `models/service_request.py` | ServiceRequest |
| 问题模型 | `models/problem.py` | Problem |
| SLA 模型 | `models/sla.py` | SlaPolicy, SlaViolation |
| 状态机引擎 | `services/state_machine.py` | 状态转换 + 动作触发 |
| SLA 计时器 | `services/sla_timer.py` | Celery Beat 定时检查 SLA |
| 升级策略 | `services/escalation.py` | 超时自动升级 |

**第 2 周：API**

| 任务 | 文件 | 说明 |
|------|------|------|
| 事件工单 ViewSet | `views/incident.py` | CRUD + 分派/升级/关闭动作 |
| 变更 ViewSet | `views/change.py` | CRUD + CAB 审批动作 |
| 服务请求 ViewSet | `views/service_request.py` | |
| 问题 ViewSet | `views/problem.py` | |
| SLA ViewSet | `views/sla.py` | |
| 序列化器 | `serializers.py` | 各模型序列化器 |
| 路由 | `urls.py` | 注册 ViewSet |

**第 3 周：前端**

| 任务 | 说明 |
|------|------|
| 工单工作台页面 | 待处理/我提报/我处理/E 多维度筛选 |
| 工单详情页 | 时间线/操作记录/关联资产/关联告警 |
| SLA 看板 | 实时 SLA 状态/违例概览/趋势 |
| 服务目录页面 | 服务分类/表单模板 |
| 变更日历 | 甘特图/维护窗口/冲突检测 |
| API 封装 | `api/itsm.ts` |

### Batch 3 并行：Monitor — 3 周

**第 1 周：模型 + API**

| 任务 | 文件 | 说明 |
|------|------|------|
| App 骨架 | `apps.py`, `admin.py` | |
| 告警规则模型 | `models/alert_rule.py` | AlertRule（CoreModel） |
| 告警事件模型 | `models/alert_event.py` | AlertEvent（CoreModel），关联 CMDB |
| 通知策略模型 | `models/notification.py` | NotificationGroup, NotificationPolicy |
| 监控目标模型 | `models/target.py` | MonitorTarget，关联 CMDB Host |
| 告警事件 ViewSet | `views/alert_event.py` | 列表/详情/确认/关闭 |
| 告警规则 ViewSet | `views/alert_rule.py` | CRUD |
| 监控目标 ViewSet | `views/target.py` | CRUD + 健康检查动作 |
| 序列化器 | `serializers.py` | |
| 路由 | `urls.py` | |

**第 2 周：告警引擎**

| 任务 | 文件 | 说明 |
|------|------|------|
| 告警收敛引擎 | `services/alert_convergence.py` | 去重/聚合/抑制逻辑 |
| Grafana 客户端 | `services/grafana_client.py` | Grafana Alerting API / Webhook 接收 |
| 工单联动服务 | `services/incident_trigger.py` | 告警→ITSM 事件工单创建 |
| Webhook 接收端点 | 复用 OpsFlow webhook 机制 | Grafana 告警推送入口 |

**第 3 周：前端**

| 任务 | 说明 |
|------|------|
| 告警事件中心页面 | 告警列表/收敛历史/详情/关联工单 |
| 监控目标管理页面 | Exporter 注册/健康状态 |
| 通知策略管理页面 | 通知组/值班表/模板 |
| 资产监控面板 | CMDB 资产关联 Grafana 面板嵌入 |
| API 封装 | `api/monitor.ts` |

---

### Batch 4：作业平台 (job_platform) — 2 周

| 任务 | 文件 | 说明 |
|------|------|------|
| App 骨架 | `apps.py`, `admin.py` | |
| 作业定义模型 | `models/job.py` | JobDefinition（CoreModel） |
| 脚本模型 | `models/script.py` | Script（CoreModel） |
| 执行记录模型 | `models/execution.py` | JobExecution（CoreModel） |
| 高危规则模型 | `models/approval_rule.py` | DangerousCmdRule |
| 作业 ViewSet | `views/job.py` | CRUD + 执行动作 |
| 脚本 ViewSet | `views/script.py` | CRUD + 上传/下载 |
| 执行记录 ViewSet | `views/execution.py` | 只读 |
| 执行引擎 | `services/executor.py` | 复用 opsagent SSH/local_exec |
| 高危命令过滤 | `services/dangerous_cmd.py` | 关键字/正则/白名单 |
| 文件分发 | `services/file_dist.py` | SCP/RSYNC 封装 |
| 序列化器 | `serializers.py` | |
| 路由 | `urls.py` | |
| 前端页面 | 作业执行/文件分发/执行记录/脚本管理 | |
| API 封装 | `api/job-platform.ts` | |

---

### Batch 5：运维门户 + Open API — 1.5 周

**运维门户（轻后端 0.5 周 + 前端 1 周）：**

| 任务 | 文件 | 说明 |
|------|------|------|
| 聚合视图 | `views/dashboard.py` | 查询各模块待办/告警/工单概览 |
| 聚合服务 | `services/aggregator.py` | 跨模块数据聚合（调用各模块 service） |
| 路由 | `urls.py` | 少量聚合端点 |
| 门户首页 | 前端 | 待办聚合/快捷操作/通知中心/概览卡片 |
| 个人工作台 | 前端 | 我的工单/我的告警/收藏模板 |
| 全局搜索 | 前端 | 搜索 CMDB 资产/工单/流程/知识库 |
| Store | `stores/portal.ts` | |

**Open API（独立 app）：**

| 任务 | 文件 | 说明 |
|------|------|------|
| ApiApp 模型 | `models/api_app.py` | 第三方应用（CoreModel） |
| ApiToken 模型 | `models/api_token.py` | 访问凭证 |
| Webhook 模型 | `models/webhook.py` | 事件订阅 |
| Token 认证 | `auth.py` | Access Key + Secret Key + HMAC 签名 |
| 频率限制 | `throttle.py` | 应用级配额控制 |
| CMDB 开放端点 | `views/cmdb.py` | 资产查询/同步 |
| ITSM 开放端点 | `views/itsm.py` | 工单创建/查询 |
| Monitor 开放端点 | `views/monitor.py` | 告警推送/查询 |
| 作业开放端点 | `views/job.py` | 作业执行/结果查询 |
| OpsFlow 开放端点 | `views/opsflow.py` | 流程启动/状态查询 |
| Webhook 推送服务 | `services/webhook_service.py` | 事件→回调第三方 |
| 前端管理页面 | Open API 管理后台 | 应用管理/Token 管理/调用日志/Webhook 订阅 |
| API 封装 | `api/open-api.ts` | |

---

## 4. 已有 App 的适配任务

### opsflow — 新增 / 改动

| 任务 | 说明 | 工期 |
|------|------|------|
| 审批流 ITSM 联动 | 现有 approval ViewSet 增加 ITSM 工单 ID 关联 | 1 天 |
| Grafana Webhook 接收端点 | 新增 opsflow webhook 类型 | 1 天 |
| ansible_trigger CMDB 引用 | 执行目标从固定 hosts 改为 CMDB Host 查询 | 2 天 |

### opsagent — 新增 / 改动

| 任务 | 说明 | 工期 |
|------|------|------|
| 执行通道抽象 | 将 SSH/local_exec 抽取为可复用通道，供作业平台调用 | 2 天 |
| DeepSeek 凭证迁移 | 从 opsagent env 配置迁移到集成中心 Credential | 1 天 |

### dvadmin / iam

无需改动。

---

## 5. 统一代码结构清单（每 App 检查项）

所有新建 App 完成后需检查：

- [ ] `models/` 目录拆分，模型继承 CoreModel（或 CMDB 的 StructuredNode）
- [ ] `views/` 目录每实体一个文件，继承 CustomModelViewSet
- [ ] `serializers.py` 统一文件，继承 CustomModelSerializer
- [ ] 响应使用 `DetailResponse` / `SuccessResponse` / `ErrorResponse`
- [ ] 表前缀 `ops_<app>_<name>`
- [ ] URL 路径 kebab-case
- [ ] `models/__init__.py` 重新导出所有模型
- [ ] `urls.py` 使用 SimpleRouter
- [ ] 业务逻辑在 `services/`，不在 ViewSet 中

---

## 6. 工时汇总

| 批次 | 模块 | 后端 | 前端 | 总计 |
|------|------|------|------|------|
| Batch 1 | 集成中心 | 1.5 周 | 0.5 周 | 2 周 |
| Batch 2 | CMDB | 2 周 | 1 周 | 3 周 |
| Batch 3a | ITSM | 1.5 周 | 1.5 周 | 3 周 |
| Batch 3b | Monitor | 1.5 周 | 1.5 周 | 3 周 |
| Batch 4 | 作业平台 | 1 周 | 1 周 | 2 周 |
| Batch 5 | 运维门户 | 0.5 周 | 1 周 | 1.5 周 |
| Batch 5 | Open API | 1 周 | 0.5 周 | 1.5 周 |
| 交叉 | 已有 app 适配 | 1 周 | 0 | 1 周 |
| | **总计** | **~8 周** | **~5 周** | **~10 周**（含并行） |
