# OpsFlow 智能运维平台 · 整体架构设计

> 基于 dvadmin 底座 + OpsFlow 工作流引擎 + OpsAgent AI 助手，对标蓝鲸体系构建完整 IT 智能运营平台

| 元数据 | 值 |
|--------|-----|
| 版本 | v1.0 |
| 日期 | 2026-06-04 |
| 状态 | 已确认 |
| 后续 | → writing-plans 阶段 |

---

## 1. 背景与目标

当前 opsflow 项目已具备：

- **RBAC/IAM 权限体系**（dvadmin 完整 RBAC + IAM 自助申请）
- **OpsFlow 工作流引擎**（bamboo-engine 驱动的 Pipeline 编排、审批流、调度计划、10+ 插件组）
- **OpsAgent AI 运维助手**（DeepSeek 驱动，SSH/本地执行，风险审计）

与完整 IT 运维平台的差距在于缺少：CMDB、ITSM 工单、监控告警、日志中心、集成中心、作业平台等核心模块。

**目标：** 对标蓝鲸体系，构建一个覆盖"发现→流程→执行→沉淀"全链路的 IT 智能运营平台。

---

## 2. 整体架构

### 2.1 分层架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                   🖥️  展示层 (Vue 3 + Element Plus)                   │
│  运维门户 │ CMDB │ ITSM │ 监控告警 │ 作业平台 │ 集成中心 │ AI助手   │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ REST + WebSocket (JWT)
┌───────────────────────────▼──────────────────────────────────────────┐
│                   🔌 API 网关/BFF 层                                  │
│  dvadmin router → 权限校验 → 项目隔离 → 请求日志 → 频率限制          │
│  Open API router → Token认证 → 签名验证 → 配额管理 → 调用计量       │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│                   🧩  业务服务层 (Django Apps)                        │
│                                                                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │ CMDB   │ │ ITSM   │ │ Monitor│ │作业平台 │ │集成中心 │ │ OpenAPI│  │
│  │ 🆕P1  │ │ 🆕P1  │ │ 🆕P1  │ │ 🆕P1  │ │ 🆕P1  │ │ 🆕P1  │  │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘  │
│      │          │          │          │          │          │        │
│  ┌───▼──────────▼──────────▼──────────▼──────────▼──────────▼────┐  │
│  │  已有底座: opsflow/opsagent/iam/dvadmin/Celery/APScheduler    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│                   🗄️  数据层                                          │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│  │ MySQL  │ │ Neo4j  │ │ Redis  │ │   ES   │ │ Object │           │
│  │事务数据 │ │CMDB拓扑│ │缓存/队 │ │日志(P2)│ │存储(P2)│           │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 外部: Prometheus TSDB │ InfluxDB │ Grafana (可视化+告警)      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

| 原则 | 说明 |
|------|------|
| **单体优先** | Phase 1 在一个 Django 项目内扩展新 app，不拆分微服务 |
| **内外隔离** | 内部 API（`/api/`）与开放 API（`/api/v2/open/`）物理隔离 |
| **所有外部调用走集成中心** | 各模块不准直接调用外部 API，强制通过集成中心 |
| **CMDB 是数据底座** | 所有模块关联 CMDB 资产，工单/告警/作业均携带资产上下文 |

---

## 3. 模块设计

### 3.1 CMDB 配置管理

| 属性 | 设计 |
|------|------|
| **App** | `backend/cmdb/` |
| **存储** | Neo4j (neomodel OGM) 存实例 + MySQL 存模型定义 |
| **核心模型** | Biz → Set → Module → Host → Process（标准拓扑链） |
| **自定义模型** | MySQL 存 schema 定义，Neo4j Tags 实例化，支持动态扩展 |
| **关系** | neomodel 的 `RelationshipTo`/`RelationshipFrom` 定义带属性的边 |
| **云同步** | 通过集成中心对接云 API 自动同步资产 |
| **前端** | 业务管理、主机管理、拓扑视图(力导向图)、模型管理 |

#### 核心节点定义

```
(Biz)──:contains──▶(Set)──:contains──▶(Module)
  ▲                                       │
  │ :belongs_to                           ▼
  │                                 (Host)──:runs──▶(Process)
  │                                       │
  └───────────────:deployed_to────────────┘
```

- Biz: biz_id, name, lifecycle, operator
- Host: host_id, ip, hostname, os_type, cpu_cores, memory_mb, disk_gb, status, agent_status, labels(JSON)
- 所有节点支持自定义字段（通过 JSON 属性扩展）

#### 双数据源策略

| 数据源 | 职责 | 技术 |
|--------|------|------|
| MySQL | 模型定义、权限、审计、用户 | Django ORM (CoreModel 基类) |
| Neo4j | CMDB 节点、拓扑关系、影响分析 | neomodel (StructuredNode) |
| 桥接 | MySQL 存 `neo4j_node_id` 引用 | Django Neo4j Router |

---

### 3.2 ITSM 服务管理

| 属性 | 设计 |
|------|------|
| **App** | `backend/itsm/` |
| **存储** | MySQL (事务数据) + Neo4j 节点 ID 引用 (CMDB 关联) |
| **四大流程** | 事件管理、服务请求、变更管理、问题管理 |

#### 工单生命周期

```
新建 → 待分派 → 处理中 → 已解决 → 已关闭
          ↑        ↑         ↓
          └── 升级 ┘   重新打开
```

- 状态转换由：用户操作 / API 触发 / SLA 超时 / 自动化规则 驱动
- 审批节点复用 OpsFlow 现有 approval 机制

#### SLA 体系

| 优先级 | 响应时间 | 解决时间 | 升级策略 |
|--------|---------|---------|---------|
| P1 危急 | ≤ 15 min | ≤ 4 h | 10 min → 主管 |
| P2 高 | ≤ 1 h | ≤ 8 h | 30 min → 主管 |
| P3 中 | ≤ 4 h | ≤ 24 h | 2 h → 升级 |
| P4 低 | ≤ 24 h | ≤ 72 h | 24 h → 提醒 |

#### CMDB 关联策略

- 工单字段 `cmdb_biz_id` / `cmdb_host_id` 存储 Neo4j 节点 ID
- 创建时快照资产信息到 `cmdb_data` JSON 字段（防止资产变更后工单信息丢失）
- 监控告警来源的工单自动携带 `alert_id` / `alert_data`

---

### 3.3 监控告警系统

| 属性 | 设计 |
|------|------|
| **App** | `backend/monitor/` |
| **采集路径 A** | Prometheus + Exporter (Pull) — 基础设施/中间件/K8s |
| **采集路径 B** | Telegraf + InfluxDB (Push) — 业务指标/网络设备/云厂商 |
| **可视化+告警** | Grafana (双数据源: Prometheus TSDB + InfluxDB) |
| **OpsFlow 集成** | Grafana Alerting API / Webhook → 告警收敛 → ITSM 工单 |

#### 告警→工单联动流程

```
Grafana Alert 触发
  ↓
Webhook → OpsFlow 告警接收端点
  ↓
告警收敛引擎: 去重 + 聚合 + 抑制 (Redis 缓存)
  ↓
关联 CMDB: 根据标签/hostname/IP 找到受影响资产
  ↓
创建事件工单 (Incident) → SLA 计时 → 通知负责人
```

---

### 3.4 集成中心 (Integration Hub)

| 属性 | 设计 |
|------|------|
| **App** | `backend/integration/` |
| **定位** | 所有外部系统调用的统一网关和连接器管理层 |

#### 核心模型

| 模型 | 说明 |
|------|------|
| `ConnectorDefinition` | 连接器定义 (code, name, category, config_schema, provider_class) |
| `ConnectorInstance` | 连接器实例 (definition, config, status, health_check) |
| `ConnectorCredential` | 凭证 (实例关联，AES-256 加密存储，过期管理) |
| `IntegrationLog` | 调用审计 (instance, action, request/response, status, duration) |

#### 首批适配器

| 类别 | 适配器 |
|------|--------|
| 公有云 | 阿里云(ECS), 腾讯云(CVM), 华为云 |
| 私有云 | VMware, OpenStack |
| 通知 | 短信网关, 邮件, 企微, 钉钉 |
| 认证 | LDAP, AD |
| AI | DeepSeek API (从 opsagent 迁移到集成中心管理凭证) |
| 已有 | Ansible Tower/AWX (从 opsflow 迁移) |

#### 设计原则

- 所有模块**不准直接调用外部 API**，强制通过集成中心
- 凭证统一加密存储（AES-256），审计所有使用记录
- 统一熔断/限流/重试策略
- 定期健康检查，状态可视化

---

### 3.5 作业平台

| 属性 | 设计 |
|------|------|
| **App** | `backend/job_platform/` |
| **技术基础** | 基于 opsagent 的 SSH/local_exec 工具扩展 |

#### 核心能力

- 批量脚本执行（在 N 台主机上执行命令/脚本）
- 文件分发（上传/下载/分发到多台主机）
- 执行账户管理（root/普通用户/特权账户）
- 高危命令拦截（关键字/正则/白名单）
- 执行记录和回放

#### 与 opsagent 的关系

| 组件 | 职责 |
|------|------|
| opsagent | AI 驱动的交互式运维（自然语言→执行→结果解释） |
| 作业平台 | 标准化的批量执行（界面化操作→执行→记录） |
| OpsFlow | 复杂流程编排（多步骤/条件/审批/联动） |

三者共享底层执行通道（SSH / Ansible / Local），面向不同场景。

---

### 3.6 运维门户

| 属性 | 设计 |
|------|------|
| **App** | `backend/portal/` (轻后端，主要聚合查询) |
| **前端** | 为主，各模块数据的聚合视图 |

#### 门户内容

- **待办聚合** — 待审批工单、待处理告警、待执行作业，跨模块统一展示
- **快捷操作** — 快速提单、快速执行、全局搜索
- **个人面板** — 我的工单、我处理的告警、我的收藏模板
- **概览看板** — 今日告警数、进行中工单、系统健康状态(CMDB)
- **通知中心** — WebSocket 实时推送，历史通知聚合

---

### 3.7 开放 API (Open API Gateway)

| 属性 | 设计 |
|------|------|
| **App** | `backend/open_api/` (独立 app，与内部 API 物理隔离) |
| **路由前缀** | `/api/v2/open/` |

#### 核心模型

| 模型 | 说明 |
|------|------|
| `ApiApp` | 第三方应用 (name, company, contact_email, status, rate_limit, allowed_apis) |
| `ApiToken` | 访问凭证 (关联 ApiApp, access_key + secret_key, expire_at, allow_ips) |
| `OpenApiLog` | 调用日志 (app, token, path, method, status, duration, ip) |
| `WebhookSubscription` | 事件订阅 (app, event_type, callback_url, secret, retry_config) |

#### 首批开放 API

| 模块 | API | 场景 |
|------|-----|------|
| CMDB | 查询资产/同步资产/拓扑查询 | 第三方同步资产 |
| ITSM | 创建工单/查询工单/更新工单 | 外部系统提单 |
| 监控告警 | 告警推送/查询/确认 | 非 Prometheus 告警接入 |
| 作业平台 | 执行作业/查询结果 | 外部触发运维操作 |
| OpsFlow | 启动流程/查询状态/审批 | 已有扩展到全平台 |
| Webhook | 事件订阅/推送 | 主动通知第三方 |

#### 设计原则

- 内外物理隔离（独立 app + 独立路由）
- 应用级权限（每个 ApiApp 独立 Token、配额、IP 白名单）
- 双向集成（既开放 API 供调用，也 Webhook 主动推送）
- 统一响应格式（复用 `DetailResponse`/`ErrorResponse` 标准）
- 提供 OpenAPI (Swagger) 文档

---

## 4. 端到端数据流

### 4.1 自动化事件响应

```
监控采集指标 → Prometheus/Telegraf
    ↓
Grafana 告警规则匹配
    ↓
Webhook → OpsFlow 告警接收
    ↓ 告警收敛 (去重/聚合/抑制)
    ↓ 关联 CMDB 资产 → 确定影响业务
    ↓
创建 ITSM 事件工单 → SLA 计时 → 通知负责人
    ↓
负责人判断是否需要变更
    ↓
提交变更申请 → CAB 审批 → OpsFlow 执行自动化修复
    ↓
更新 CMDB 状态 → 关闭工单 → 知识库沉淀
```

### 4.2 云资产同步

```
定时任务/Celery Beat 触发
    ↓
集成中心 → 云厂商 API (阿里云 ECS / 腾讯云 CVM)
    ↓
获取云上实例列表
    ↓
与 Neo4j 中已有资产比对 (diff)
    ↓
新增/更新/标记下线
    ↓
记录变更日志 → 通知 CMDB 管理员
```

---

## 5. 技术栈汇总

| 层 | 技术选型 | 备注 |
|----|---------|------|
| **前端框架** | Vue 3 + TypeScript + Vite 4 | 已有 |
| **UI 库** | Element Plus | 已有 |
| **图表** | ECharts | 已有 |
| **后端框架** | Django 4.2 + DRF 3.14 | 已有 |
| **ORM** | Django ORM (MySQL) + neomodel (Neo4j) | 双数据源 |
| **RBAC** | dvadmin.system | 已有 |
| **工作流** | bamboo-engine + OpsFlow | 已有 |
| **AI** | DeepSeek API | 已有，凭证迁移到集成中心 |
| **任务队列** | Celery + Redis | 已有 |
| **调度** | APScheduler | 已有 |
| **WebSocket** | Django Channels + Redis | 已有 |
| **MySQL** | 事务数据 (工单/审批/配置) | 已有 |
| **Neo4j** | CMDB 拓扑存储 | 🆕 |
| **Redis** | 缓存/队列/Channel Layer | 已有 |
| **Elasticsearch** | 日志存储与检索 | Phase 2 |
| **Prometheus** | 基础设施指标 TSDB | 外部 |
| **InfluxDB** | 业务指标/长期存储 | 外部 |
| **Grafana** | 可视化面板 + 告警引擎 | 外部 |

---

## 6. 分阶段演进路线

### Phase 1 (~10 周) · 核心闭环

**核心目标：** 打通"发现→流程→执行→沉淀"完整链路

| 模块 | 优先级 | 前置依赖 | 估时 |
|------|--------|---------|------|
| 集成中心 | P0 | 无（基础依赖） | 2 周 |
| CMDB | P0 | 集成中心(云同步) | 3 周 |
| ITSM | P0 | CMDB(资产关联) | 3 周 |
| 监控告警 | P0 | CMDB(资产关联), 集成中心(通知) | 3 周 |
| 作业平台 | P1 | CMDB(目标主机), 集成中心(执行通道) | 2 周 |
| 运维门户 | P1 | 所有模块(聚合数据) | 1 周 |
| Open API | P1 | 各模块完成 | 1.5 周 |

### Phase 2 (~6 周) · 可观测 + 智能化

| 模块 | 内容 |
|------|------|
| 日志中心 | Filebeat + ES 采集、全文检索、权限控制 |
| AIOps | 告警智能聚合、根因分析、异常检测 |
| 报表中心 | 运维报告自动生成和定时发送 |

### Phase 3 (~6 周) · 合规 + 治理

| 模块 | 内容 |
|------|------|
| 巡检合规 | 安全基线检查、配置漂移、漏洞管理 |
| 容量规划 | 趋势预测、资源饱和度、扩容建议 |
| 安全运营 | 审计日志分析、威胁检测 |

---

## 7. 项目目录结构

```
backend/
├── cmdb/                    # 🆕 CMDB 配置管理
│   ├── models/
│   │   ├── __init__.py
│   │   ├── node_types.py    # neomodel 节点定义
│   │   ├── relationships.py # 关系定义
│   │   └── model_schema.py  # MySQL 模型定义
│   ├── views/
│   │   ├── biz.py
│   │   ├── host.py
│   │   ├── topology.py
│   │   └── model_manage.py
│   ├── serializers/
│   ├── services/
│   │   ├── sync_service.py  # 云资产同步
│   │   └── topology_service.py
│   ├── neo4j_router.py      # 双数据源路由
│   ├── urls.py
│   └── admin.py
│
├── itsm/                    # 🆕 ITSM 服务管理
│   ├── models/
│   │   ├── incident.py
│   │   ├── change.py
│   │   ├── service_request.py
│   │   ├── problem.py
│   │   └── sla.py
│   ├── views/
│   ├── services/
│   │   ├── state_machine.py # 状态机引擎
│   │   ├── sla_timer.py     # SLA 计时
│   │   └── escalation.py    # 升级策略
│   ├── urls.py
│   └── admin.py
│
├── monitor/                 # 🆕 监控告警
│   ├── models/
│   │   ├── alert_rule.py
│   │   ├── alert_event.py
│   │   ├── notification_group.py
│   │   └── target.py
│   ├── views/
│   ├── services/
│   │   ├── alert_convergence.py  # 告警收敛
│   │   ├── grafana_client.py     # Grafana API 对接
│   │   └── incident_trigger.py   # 触发 ITSM 工单
│   ├── urls.py
│   └── admin.py
│
├── integration/             # 🆕 集成中心
│   ├── models/
│   │   ├── connector.py
│   │   ├── credential.py
│   │   └── integration_log.py
│   ├── views/
│   ├── adapters/            # 适配器实现
│   │   ├── base.py          # BaseConnector 抽象类
│   │   ├── cloud/
│   │   │   ├── aliyun.py
│   │   │   ├── tencent.py
│   │   │   └── huawei.py
│   │   ├── notification/
│   │   │   ├── sms.py
│   │   │   ├── mail.py
│   │   │   ├── wecom.py
│   │   │   └── dingtalk.py
│   │   └── auth/
│   │       ├── ldap.py
│   │       └── ad.py
│   ├── services/
│   │   ├── credential_service.py  # 凭证加密/解密
│   │   └── health_service.py
│   ├── url.py
│   └── admin.py
│
├── job_platform/            # 🆕 作业平台
│   ├── models/
│   │   ├── job.py
│   │   ├── script.py
│   │   ├── execution.py
│   │   └── approval_rule.py
│   ├── views/
│   ├── services/
│   │   ├── executor.py      # 执行引擎（复用 opsagent 通道）
│   │   ├── dengerous_cmd.py # 高危命令过滤
│   │   └── file_dist.py     # 文件分发
│   ├── urls.py
│   └── admin.py
│
├── portal/                  # 🆕 运维门户
│   ├── views/
│   │   └── dashboard.py     # 聚合查询接口
│   └── urls.py
│
├── open_api/                # 🆕 开放 API
│   ├── models/
│   │   ├── api_app.py
│   │   ├── api_token.py
│   │   └── webhook.py
│   ├── views/               # 各模块开放端点
│   │   ├── cmdb.py
│   │   ├── itsm.py
│   │   ├── monitor.py
│   │   ├── job.py
│   │   └── opsflow.py
│   ├── auth.py              # Token 认证/签名验证
│   ├── throttle.py          # 频率限制/配额
│   ├── urls.py
│   └── admin.py
│
├── opsflow/                 # 已有，无需改动
├── opsagent/                # 已有，执行通道适配给作业平台
├── dvadmin/                 # 已有，无需改动
└── iam/                     # 已有，无需改动

web/src/
├── views/apps/
│   ├── portal/              # 🆕 运维门户
│   ├── cmdb/                # 🆕 CMDB
│   ├── itsm/                # 🆕 ITSM
│   ├── monitor/             # 🆕 监控告警
│   ├── integration/         # 🆕 集成中心
│   ├── job-platform/        # 🆕 作业平台
│   └── open-api/            # 🆕 开放 API 管理后台
├── api/
│   ├── cmdb.ts
│   ├── itsm.ts
│   ├── monitor.ts
│   ├── integration.ts
│   ├── job-platform.ts
│   └── open-api.ts
└── stores/
    ├── portal.ts
    └── ...
```

---

## 8. 关键架构决策记录 (ADR)

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| CMDB 存储 | MySQL vs Neo4j | **Neo4j** | 拓扑关系查询性能、影响分析 O(1) |
| CMDB OGM | neomodel vs py2neo | **Django 双数据源** | 事务在 MySQL，图在 Neo4j，各取所长 |
| ITSM 存储 | MySQL vs 图 | **MySQL + Neo4j 引用** | 工单是事务性数据，ACID 保障更重要 |
| 监控采集 | 单一 vs 双轨 | **Prometheus + Telegraf/InfluxDB** | 拉+推覆盖所有场景 |
| 可视化告警 | 自建 vs Grafana | **Grafana** | 成熟度最高，避免重复造轮子 |
| 架构 | 单体 vs 微服务 | **单体优先** | 开发速度快，Phase 1 验证后再拆分 |
| 对外 API | 扩展现有 vs 独立 app | **独立 open_api app** | 内外物理隔离，职责清晰 |
| 集成中心 | 分散 vs 统一 | **统一集成中心** | 凭证统一管理，调用审计，熔断保护 |

---

## 9. 附录

### 9.1 参考

- 蓝鲸智云产品矩阵 (bk-sops, bk-cmdb, bk-job, bk-monitor, bk-itsm)
- dvadmin django-vue3-admin 框架
- bamboo-engine / bamboo-pipeline
- Prometheus + Grafana 生态
- neomodel: Python OGM for Neo4j

### 9.2 词汇表

| 术语 | 说明 |
|------|------|
| OGM | Object-Graph Mapping，类比 ORM 但针对图数据库 |
| CMDB | Configuration Management Database，配置管理数据库 |
| ITSM | IT Service Management，IT 服务管理 |
| SLA | Service Level Agreement，服务级别协议 |
| AIOps | AI for IT Operations，智能运维 |
| CAB | Change Advisory Board，变更咨询委员会 |
