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
| `api/opsflow/apigw/v1/*/` | （函数视图） | 外部 API 网关 |
| `api/opsflow/cmdb/*/` | （函数视图） | CMDB 模拟数据 |

嵌套路由：
- `api/opsflow/templates/{id}/schemes/` — 执行方案
- `api/opsflow/projects/{id}/members/` — 项目成员

### WebSocket 路由（`application/routing.py`）

```python
from django.urls import path, re_path
from opsflow.consumers import FlowMonitorConsumer

websocket_urlpatterns = [
    re_path(r'^ws/opsflow/execution/(?P<execution_id>\d+)/$',
            FlowMonitorConsumer.as_asgi()),
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

### 关键依赖（`backend/requirements.txt`）

| 包 | 版本 | 用途 |
|---|---|---|
| `bamboo-pipeline` | 3.29.9 | 流程引擎核心（BambooDjangoRuntime） |
| `apscheduler` | 3.11.2 | Cron 调度器 |
| `django-apscheduler` | 0.7.0 | APScheduler Django 管理界面 |
| `celery` | 5.6.3 | 异步任务队列 |
| `channels` | （内置） | ASGI WebSocket 支持 |
| `channels-redis` | （内置） | Redis Channel Layer |
| `django-redis` | （内置） | Redis 缓存后端 |
| `openai` | 2.31.0 | AI 生成/精炼/分析 |
| `uvicorn` | 0.23.2 | ASGI 服务器 |

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

OpsFlow 页面通过后端菜单管理系统注册（前端使用 vue-next-admin 的 isRequestRoutes 模式），因此 `web/src/router/route.ts` 中不需要显式定义 opsflow 路由。后端在菜单表 `/api/system/menu/` 中配置以下路由：

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

## 部署检查清单

1. 确保 MySQL 已创建数据库且 `conf/env.py` 中配置正确
2. 运行迁移：`python manage.py migrate opsflow`
3. 注册插件：`python manage.py shell -c "from opsflow.plugins.registry import discover_plugins; discover_plugins()"`（或重启后自动执行）
4. 启动 Redis 服务
5. 启动 ASGI 服务器（Daphne/Uvicorn）
6. 启动 Celery Worker（至少包含 er_execute 和 er_schedule 队列）
7. 确保前端 `web/src/api/opsflow/request.ts` 中的 baseURL 指向正确的后端地址
8. （可选）配置 OpenAI API Key 以启用 AI 生成功能
