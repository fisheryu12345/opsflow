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

## 5. 统一 App 代码结构规范

所有新建 Django App 必须遵循同一套代码结构和基类约定，确保模块间的可维护性和一致性。

### 5.1 目录规范

每个标准 CRUD 类 App 使用以下目录结构：

```
app_name/                          # Django App
├── __init__.py
├── apps.py                        # AppConfig, 配置 verbose_name
├── admin.py                       # Django Admin 注册
├── urls.py                        # 路由 (SimpleRouter + path())
├── serializers.py                 # 序列化器 (统一文件, 简洁时)
│   ├── xxx_serializer()           #   或拆分为 serializers/ 目录
│   └── ...
├── filters.py                     # filter_fields / search_fields (可选)
├── models/
│   ├── __init__.py                # 重新导出所有模型
│   ├── entity_a.py                # 按领域拆分的模型文件
│   └── entity_b.py
├── views/
│   ├── __init__.py
│   ├── entity_a.py                # 每个模型/领域一个 ViewSet 文件
│   └── entity_b.py
├── services/                      # 业务逻辑层 (保持 views 轻薄)
│   ├── __init__.py
│   ├── some_service.py
│   └── ...
├── management/commands/           # 管理命令
├── migrations/
└── tests/
```

> **说明：** `models/` 目录拆分仅在 `models.py` 超过 200 行时使用。对仅有 1-2 个简单模型的 App，可保留单一 `models.py` 文件。

### 5.2 基类约定

| 组件 | 基类 | 来源 | 说明 |
|------|------|------|------|
| **Model** | `CoreModel` | `dvadmin.utils.models` | 自动获得 id / creator / modifier / create_datetime / update_datetime / description / deleted |
| **ViewSet** | `CustomModelViewSet` | `dvadmin.utils.viewset` | 自动注入统一响应格式、按动作切换序列化器、批量删除、导入/导出 |
| **Serializer** | `CustomModelSerializer` | `dvadmin.utils.serializers` | 自动填充 creator / modifier / dept_belong_id，格式化时间字段 |
| **Response** | `DetailResponse` / `SuccessResponse` / `ErrorResponse` | `dvadmin.utils.json_response` | 统一 `{"code": 2000, "data": ..., "msg": "..."}` 格式 |

**例外情况：**
- CMDB App 的 Neo4j 节点模型使用 `neomodel.StructuredNode`，不适用 `CoreModel`；但 CMDB 的模型定义（MySQL 侧）仍使用 `CoreModel`
- 复杂视图（如 ITSM 状态机驱动、监控告警收敛）可通过 `mixins` 组合扩展 `CustomModelViewSet`
- 只读视图（如日志、审计）可使用 `ReadOnlyModelViewSet` 或 `ListModelMixin + RetrieveModelMixin`

### 5.3 代码模板

#### models/entity.py

```python
# -*- coding: utf-8 -*-
"""Model definition for EntityX

实体名称 — 简要说明
"""

import logging

from django.db import models
from dvadmin.utils.models import CoreModel

logger = logging.getLogger(__name__)

class EntityX(CoreModel):
    """实体X — 核心业务对象"""
    name = models.CharField(max_length=128, verbose_name="名称")
    code = models.CharField(max_length=64, unique=True, null=True, blank=True, verbose_name="编码")
    status = models.CharField(max_length=32, default="active", verbose_name="状态")
    # ... 更多字段
    extra_config = models.JSONField(default=dict, verbose_name="扩展配置")

    class Meta:
        db_table = "ops_entity_x"
        verbose_name = "实体X"
        verbose_name_plural = verbose_name
        ordering = ["-create_datetime"]

    def __str__(self):
        return self.name
```

**命名规范：**
- 表名前缀：`ops_<app_short>_<name>`（如 `ops_cmdb_biz`、`ops_itsm_incident`）
- 模型名：驼峰，单数（`Incident`、`ServiceRequest`）
- 字段：蛇形，全小写

#### views/entity.py

```python
# -*- coding: utf-8 -*-
"""ViewSet for EntityX

实体名称 CRUD 接口
"""

from rest_framework import filters

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse

from ..models import EntityX
from ..serializers import (
    EntityXSerializer,
    EntityXCreateUpdateSerializer,
)

FSM = 'entity_x_viewset'


class EntityXViewSet(CustomModelViewSet):
    """
    实体X管理

    list: 查询列表
    create: 创建
    update: 修改
    retrieve: 详情
    destroy: 删除
    """
    model = EntityX
    queryset = EntityX.objects.all()
    serializer_class = EntityXSerializer
    create_serializer_class = EntityXCreateUpdateSerializer
    update_serializer_class = EntityXCreateUpdateSerializer
    filter_fields = ["status", "name"]
    search_fields = ["name", "code"]
    ordering = ["-create_datetime"]
```

#### serializers.py

```python
# -*- coding: utf-8 -*-
"""Serializers for EntityX
"""

from dvadmin.utils.serializers import CustomModelSerializer
from .models import EntityX


class EntityXSerializer(CustomModelSerializer):
    """列表/详情"""
    class Meta:
        model = EntityX
        fields = "__all__"


class EntityXCreateUpdateSerializer(CustomModelSerializer):
    """创建/修改"""
    class Meta:
        model = EntityX
        fields = "__all__"
        read_only_fields = ["code"]
```

#### urls.py

```python
# -*- coding: utf-8 -*-
"""URL configuration for app_name
"""

from django.urls import path, include
from rest_framework import routers

from .views.entity import EntityXViewSet

router = routers.SimpleRouter()
router.register(r'entity-x', EntityXViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

**路由命名规则：** URL 路径使用 `kebab-case`（连字符），对应 Model 名转换：`Incident` → `incidents`、`ServiceRequest` → `service-requests`。

### 5.4 分层职责

```
ViewSet (视图层)          → 请求/响应处理，权限校验，参数验证
  ↓
Serializer (序列化层)    → 数据校验、字段映射、嵌套展示
  ↓
Model (模型层)           → 数据定义、ORM 查询、字段约束
  ↓
Service (服务层, 可选)    → 复杂业务逻辑、跨模型操作、外部调用
```

- **ViewSet** 保持薄层：只做请求解析和响应返回
- **Service** 承载核心业务逻辑（状态机、收敛算法、SLA 计时等）
- **Model** 只做数据定义和基础查询，不做业务判断

### 5.5 已有 App 的对齐策略

| App | 当前模式 | 对齐计划 |
|-----|---------|---------|
| **cmdb** 🆕 | 新建 | 全面遵循本规范 |
| **itsm** 🆕 | 新建 | 全面遵循本规范 |
| **monitor** 🆕 | 新建 | 全面遵循本规范 |
| **integration** 🆕 | 新建 | 全面遵循本规范 |
| **job_platform** 🆕 | 新建 | 全面遵循本规范 |
| **portal** 🆕 | 新建 | 轻后端，简化结构 |
| **open_api** 🆕 | 新建 | 遵循本规范 |
| opsflow (已有) | 使用 `models.Model` + 标准 `ModelSerializer` | 不必重构，新功能保持现状 |
| opsagent (已有) | 使用 `models.Model` + 标准 `ModelSerializer` | 不必重构，新功能保持现状 |

## 7. 技术栈汇总

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

## 8. 分阶段演进路线

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

## 9. 项目目录结构

```
backend/
├── cmdb/                    # 🆕 CMDB 配置管理
│   ├── __init__.py
│   ├── apps.py              # AppConfig
│   ├── admin.py
│   ├── urls.py              # SimpleRouter + path()
│   ├── serializers.py       # CustomModelSerializer 子类
│   ├── models/
│   │   ├── __init__.py      # 重新导出所有模型
│   │   ├── model_schema.py  # MySQL 模型定义 (CoreModel)
│   │   └── node_types.py    # Neo4j 节点定义 (neomodel)
│   ├── views/
│   │   ├── __init__.py
│   │   ├── biz.py           # ViewSet per entity
│   │   ├── host.py
│   │   ├── topology.py
│   │   └── model_manage.py
│   ├── services/
│   │   ├── sync_service.py  # 云资产同步 (通过集成中心)
│   │   └── topology_service.py
│   └── neo4j_router.py      # 双数据源路由
│
├── itsm/                    # 🆕 ITSM 服务管理
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── urls.py
│   ├── serializers.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── incident.py      # 事件工单 (CoreModel)
│   │   ├── change.py        # 变更 (CoreModel)
│   │   ├── service_request.py
│   │   ├── problem.py
│   │   └── sla.py           # SLA 定义
│   ├── views/
│   │   ├── __init__.py
│   │   ├── incident.py
│   │   ├── change.py
│   │   └── ...
│   └── services/
│       ├── state_machine.py # 状态机引擎
│       ├── sla_timer.py     # SLA 计时器
│       └── escalation.py    # 升级策略
│
├── monitor/                 # 🆕 监控告警
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── urls.py
│   ├── serializers.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── alert_rule.py
│   │   ├── alert_event.py
│   │   ├── notification.py  # 通知组/策略
│   │   └── target.py        # 监控目标
│   ├── views/
│   │   ├── alert_event.py
│   │   ├── alert_rule.py
│   │   └── target.py
│   └── services/
│       ├── alert_convergence.py  # 告警收敛引擎
│       ├── grafana_client.py     # Grafana API 客户端
│       └── incident_trigger.py   # 联动 ITSM 工单
│
├── integration/             # 🆕 集成中心
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── urls.py
│   ├── serializers.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── connector.py     # ConnectorDefinition + Instance
│   │   ├── credential.py    # ConnectorCredential (AES 加密)
│   │   └── integration_log.py
│   ├── views/
│   │   ├── connector.py
│   │   ├── credential.py
│   │   └── integration_log.py
│   ├── adapters/            # 连接器适配器实现
│   │   ├── base.py          # BaseConnector 抽象类
│   │   ├── cloud/           # 云厂商
│   │   │   ├── aliyun.py
│   │   │   ├── tencent.py
│   │   │   └── huawei.py
│   │   ├── notification/    # 通知通道
│   │   │   ├── sms.py
│   │   │   ├── mail.py
│   │   │   ├── wecom.py
│   │   │   └── dingtalk.py
│   │   └── auth/            # 认证源
│   │       ├── ldap.py
│   │       └── ad.py
│   └── services/
│       ├── credential_service.py  # 凭证加密/解密
│       └── health_service.py      # 健康检查
│
├── job_platform/            # 🆕 作业平台
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── urls.py
│   ├── serializers.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── job.py           # 作业定义
│   │   ├── script.py        # 脚本管理
│   │   ├── execution.py     # 执行记录
│   │   └── approval_rule.py # 高危命令规则
│   ├── views/
│   │   ├── job.py
│   │   ├── script.py
│   │   └── execution.py
│   └── services/
│       ├── executor.py      # 执行引擎 (复用 opsagent)
│       ├── dangerous_cmd.py # 高危命令过滤
│       └── file_dist.py     # 文件分发
│
├── portal/                  # 🆕 运维门户 (轻后端)
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py
│   ├── views/
│   │   └── dashboard.py     # 聚合查询接口
│   └── services/
│       └── aggregator.py    # 跨模块数据聚合
│
├── open_api/                # 🆕 开放 API (独立 app)
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── urls.py
│   ├── serializers.py
│   ├── auth.py              # Token 认证/签名验证
│   ├── throttle.py          # 频率限制/配额
│   ├── models/
│   │   ├── __init__.py
│   │   ├── api_app.py       # 第三方应用
│   │   ├── api_token.py     # 访问凭证
│   │   └── webhook.py       # 事件订阅
│   ├── views/
│   │   ├── api_app.py
│   │   ├── api_token.py
│   │   ├── cmdb.py          # CMDB 开放端点
│   │   ├── itsm.py          # ITSM 开放端点
│   │   ├── monitor.py       # 监控开放端点
│   │   ├── job.py           # 作业开放端点
│   │   └── opsflow.py       # OpsFlow 开放端点
│   └── services/
│       └── webhook_service.py
│
├── opsflow/                 # 已有，保持现状
├── opsagent/                # 已有，执行通道适配给作业平台
├── dvadmin/                 # 已有，保持现状
└── iam/                     # 已有，保持现状

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

## 10. 关键架构决策记录 (ADR)

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

## 11. 附录

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
