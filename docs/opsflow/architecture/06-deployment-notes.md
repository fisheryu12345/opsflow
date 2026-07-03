# OPSflow 部署说明

## 后端配置

### INSTALLED_APPS（`application/settings.py`）

需添加以下组件到 `INSTALLED_APPS`：

```python
INSTALLED_APPS = [
    # ... Django 内置应用 ...
    "channels",                       # ASGI WebSocket 支持
    "django_apscheduler",             # APScheduler 管理界面
    "django_extensions",

    # OpsFlow Pipeline 引擎 (bamboo-pipeline)
    "pipeline.component_framework",   # 组件框架
    "pipeline.eri",                   # ERI 运行时接口
    "pipeline.contrib.rollback",      # 回滚支持
    "pipeline.contrib.engine_admin",  # 引擎管理界面

    "opsflow",                        # OpsFlow 主应用
    # ...
]
```

### URL 路由（`opsflow/urls.py`）

挂载在 `application/urls.py` 中：

```python
urlpatterns = [
    path('api/opsflow/', include('opsflow.urls')),
]
```

OpsFlow 注册的 API 端点：

| 端点 | 视图集 | 功能 |
|---|---|---|
| `api/opsflow/templates/` | FlowTemplateViewSet | 模板 CRUD + AI 生成/精炼/布局/分析 |
| `api/opsflow/executions/` | FlowExecutionViewSet | 执行 CRUD + 启动/暂停/取消/重试 |
| `api/opsflow/logs/` | OpsLogViewSet | 操作日志 |
| `api/opsflow/knowledge/` | OpsKnowledgeViewSet | 知识库 |
| `api/opsflow/schedule-plans/` | SchedulePlanViewSet | 调度计划 |
| `api/opsflow/plugins/` | PluginViewSet | 插件管理 |
| `api/opsflow/template-nodes/` | TemplateNodeViewSet | 模板节点查询 |
| `api/opsflow/execution-nodes/` | ExecutionNodeViewSet | 执行节点查询 |
| `api/opsflow/audit/` | OperationRecordViewSet | 审计记录 |
| `api/opsflow/projects/` | OpsProjectViewSet | 项目管理 + 成员管理 |
| `api/opsflow/template-categories/` | TemplateCategoryViewSet | 模板分类 |
| `api/opsflow/dashboard/*/` | （函数视图） | 12 个统计端点 |
| `api/opsflow/cmdb/*/` | （函数视图） | CMDB 模拟数据 |
| `api/opsflow/plugins/aliyun/*/` | （函数视图） | 8 个阿里云 ECS 资源查询端点 |
| `api/opsflow/templates/create_dr_pipeline/` | （函数视图） | DR 管线创建 |
| `api/opsflow/templates/preview_dr_topology/` | （函数视图） | DR 拓扑预览 |
| `api/opsflow/clause/privacy.html` | PrivacyView | 隐私条款页面 |
| `api/opsflow/clause/terms_service.html` | TermsServiceView | 服务条款页面 |

嵌套路由：
- `api/opsflow/templates/{id}/schemes/` — 执行方案
- `api/opsflow/projects/{id}/members/` — 项目成员

### WebSocket 路由（`application/routing.py`）

使用统一 WebSocket 端点 `MegCenter`，所有消息按 topic 路由：

```python
from django.urls import path
from application.websocketConfig import MegCenter

websocket_urlpatterns = [
    path('ws/<str:service_uid>/', MegCenter.as_asgi()),
]
```

ASGI 配置（`application/asgi.py`）：

```python
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

> **说明：** 旧版 `opsflow/consumers.py`（FlowMonitorConsumer）已移除，改用统一 `MegCenter` WebSocket 网关。前端通过 `ws/{service_uid}/` 连接，服务端通过 `channel_layer.group_send()` 推送执行状态变更。

### 关键依赖（`backend/requirements.txt`）

| 包 | 版本 | 用途 |
|---|---|---|
| `bamboo-pipeline` | 4.0.2 | 流程引擎核心（BambooDjangoRuntime） |
| `apscheduler` | 3.11.2 | Cron 调度器 |
| `django-apscheduler` | 0.7.0 | APScheduler Django 管理界面 |
| `celery` | 5.6.3 | 异步任务队列 |
| `channels` | （内置） | ASGI WebSocket 支持 |
| `channels-redis` | （内置） | Redis Channel Layer |
| `django-redis` | （内置） | Redis 缓存后端 |
| `openai` | 2.31.0 | AI 生成/精炼/分析 |
| `uvicorn` | 0.23.2 | ASGI 服务器 |
| `neo4j` | 5.x | CMDB 图数据库驱动 |
| `ldap3` | — | LDAP 身份同步 |
| `paramiko` | — | SSH 远程执行（Job Platform） |
| `django-cors-headers` | — | CORS 跨域 |
| `django-fernet-fields` | — | 凭证加密（Integration Hub） |

### Open API 独立应用（`backend/open_api/`）

外部 API 网关已从 `opsflow/core/apigw/` 迁移到独立应用 `backend/open_api/`，详见 `docs/opsflow_target.md §3.3`。

路由注册（`application/urls.py`）：

```python
path("api/open-api/", include("open_api.urls")),  # 管理后台
path("api/v2/open/", include("open_api.external_urls")),  # 第三方外部端点
```

外部端点前缀：`/api/v2/open/`

### Celery 配置（`application/settings.py`）

```python
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TASK_DEFAULT_QUEUE = 'default'

# OpsFlow 专用队列
CELERY_TASK_QUEUES = [
    Queue('default', routing_key='default'),
    Queue('er_execute', routing_key='er_execute'),    # 引擎执行 + 节点通知
    Queue('er_schedule', routing_key='er_schedule'),  # 调度计划执行
]
```

启动 Celery Worker：

```bash
celery -A application worker -l info -Q er_execute,er_schedule,default -c 4
```

**各 App 的 Celery 任务：**

| App | 任务 | 队列 | 说明 |
|-----|------|------|------|
| opsflow | `execute_pipeline_task` | er_execute | 异步管线执行 (max_retries=3) |
| opsflow | `auto_retry_node_task` | default | 节点自动重试 |
| opsflow | `execute_node_timeout_strategy` | default | 节点超时策略执行 |
| opsflow | `webhook_send` | default | Webhook 回调 + 重试 |
| opsflow | `retry_schedule_execution` | default | 调度计划重试 |
| itsm | `sla_check` | default | 每分钟 SLA 违规检查 |
| itsm | `auto_resolve_expired_tickets` | default | 自动关闭 7 天前过期工单 |
| job_platform | `ai_script_check` | default | AI 脚本安全检测 |
| job_platform | `job_start_task` | default | 作业执行入口 |
| job_platform | `step_exec_task` | default | 顺序执行步骤 |

### Redis 配置

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

Redis 用途：
- **Channel Layer（db 0）** — WebSocket 消息广播（Celery worker → Daphne/Uvicorn → 前端）
- **Celery Broker（db 0）** — 异步任务队列
- **Celery Result（db 1）** — 任务结果存储
- **Django Cache（db 0）** — 可选缓存

### ASGI 服务器启动

```bash
# Daphne（生产推荐）
daphne -b 0.0.0.0 -p 8000 application.asgi:application

# Uvicorn（开发环境）
uvicorn --host 0.0.0.0 --port 8000 application.asgi:application
```

### APScheduler 调度器独立进程

OpsFlow 和 ITSM 各有独立调度器管理命令：

```bash
# OpsFlow 调度器（定时计划、超时检查）
python manage.py start_opsflow_scheduler &

# ITSM 调度器（SLA 检查、工单自动关闭）
python manage.py start_itsm_scheduler &
```

## 前端配置

### 关键依赖（`web/package.json`）

| 包 | 版本 | 用途 |
|---|---|---|
| `@antv/x6` | 3.1.7 | 流程图画布核心 |
| `@antv/x6-plugin-clipboard` | ^2.x | 复制粘贴 |
| `@antv/x6-plugin-dnd` | ^2.x | 拖放创建节点 |
| `@antv/x6-plugin-history` | ^2.x | 撤销/重做 |
| `@antv/x6-plugin-keyboard` | ^2.x | 键盘快捷键 |
| `@antv/x6-plugin-minimap` | ^2.x | 缩略图导航 |
| `@antv/x6-plugin-selection` | ^2.x | 多选 |
| `@antv/x6-plugin-snapline` | ^2.x | 对齐线 |
| `@antv/x6-plugin-stencil` | ^2.x | 调色板 |

### 路由配置

OpsFlow 页面通过后端菜单管理系统注册（前端使用 vue-next-admin 的 isRequestRoutes 模式），因此 `web/src/router/route.ts` 中不需要显式定义 opsflow 路由。后端在菜单表 `/api/iam/menu/web_router/` 中配置以下路由：

**OpsFlow 核心页面：**

```
/opsflow                   → apps/opsflow/index.vue
/opsflow/template          → apps/opsflow-template/index.vue
/opsflow/execution         → apps/opsflow-execution/index.vue
/opsflow/approval          → apps/opsflow-approval/index.vue
/opsflow/dashboard         → apps/opsflow-dashboard/index.vue
/opsflow/log               → apps/opsflow-log/index.vue
/opsflow/knowledge         → apps/opsflow-knowledge/index.vue
/opsflow/project           → apps/opsflow-project/index.vue
/opsflow/webhook           → apps/opsflow-webhook/index.vue
/opsflow/stats             → apps/opsflow-stats/index.vue
```

**其他子产品页面：**

```
/cmdb                      → apps/cmdb/index.vue
/itsm                      → apps/itsm/index.vue
/iam                       → apps/iam/index.vue
/integration               → apps/integration/index.vue
/monitor                   → apps/monitor/index.vue
/job-platform              → apps/job-platform/index.vue
/opsagent                  → apps/opsagent/index.vue
/agent                     → apps/agent/index.vue
/portal                    → apps/portal/index.vue
/open-api                  → apps/open-api/index.vue
```

## 部署检查清单

1. 确保 MySQL 已创建数据库且 `conf/env.py` 中配置正确
2. 运行迁移：`python manage.py migrate`
3. 导入种子数据：`python manage.py seed_all`（按依赖顺序自动执行全部 App）
4. 启动 Redis 服务
5. 启动 ASGI 服务器（Daphne/Uvicorn）
6. （可选）启动 APScheduler 调度器：`start_opsflow_scheduler` / `start_itsm_scheduler`
7. 启动 Celery Worker（至少包含 er_execute 和 er_schedule 队列）
8. 确保前端 `web/src/api/opsflow/request.ts` 中的 baseURL 指向正确的后端地址
9. （可选）配置 OpenAI/DeepSeek API Key 以启用 AI 生成功能
10. （可选）安装 Neo4j 5.x 并配置 `conf/env.py` 中的 Neo4j 连接参数
