# open_api — 模块索引

> 上次自动更新: 2026-06-12

---

## `open_api/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Open API Gateway app package |
| `admin.py` |  | feat(portal,open-api): add operations portal dashboard and o |
| `apps.py` | feat(portal,open-api): add operations portal dashboard and open API gateway | `OpenApiConfig` |
| `auth.py` | OpenAPI Authentication — token-based auth for external API endpoints | `OpenApiAuthentication` — OpenAPI Token 认证 — 从 Header 或 Query 参数读取 token |
| `external_urls.py` |  | External-facing Open API URL patterns |
| `serializers.py` | Serializers for Open API Gateway | `ApiAppSerializer`<br>`ApiAppCreateUpdateSerializer`<br>`OpenApiTokenSerializer` — Token 详情 — 隐藏 secret_key，仅显示掩码<br>`OpenApiTokenCreateSerializer` — 创建 Token — 创建后返回完整的 access_key 和 secret_key<br>`OpenApiTokenRegenerateSerializer` — 重新生成凭证<br>`WebhookSubscriptionSerializer` |
| `throttling.py` | OpenAPI Rate Throttling — per-app rate limiting for external API endpoints | `OpenApiRateThrottle` — 基于 ApiApp 的频率限制<br>`throttle_failure_view()` — 限流触发的自定义响应 |
| `urls.py` |  | URL configuration for Open API Gateway |

## `open_api\models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(portal,open-api): add operations portal dashboard and o |
| `models.py` | Open API Gateway models — third-party app management, tokens, webhook subscriptions | `ApiApp` — 第三方应用<br>`OpenApiToken` — 应用访问凭证<br>`WebhookSubscription` — 事件订阅 — 第三方系统通过 Webhook 接收平台事件<br>`OpenApiLog` — API 调用日志 |

## `open_api\services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Services package for open_api |
| `webhook_service.py` | Webhook dispatch service — push events to third-party systems | `dispatch_webhook()` — 向所有订阅了该事件类型的 Webhook 推送消息 返回 [(subscription_id, success), ...] |

## `open_api\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | feat(portal,open-api): add operations portal dashboard and o |
| `external.py` | External-facing API endpoints — called by third-party systems | `health()` — 健康检查端点<br>`cmdb_sync()` — CMDB 资产同步 — 第三方推送资产到 OpsFlow CMDB<br>`create_incident()` — 第三方系统创建事件工单<br>`query_incident()` — 第三方查询工单状态<br>`trigger_execution()` — 第三方触发作业执行（支持 Plan 或快速执行）<br>`trigger_pipeline()` — 触发 OpsFlow Pipeline 执行 — 提供 template_id 或完整 pipeline_tree |
| `views.py` | Open API Gateway views — App, Token, Webhook management + external-facing endpoints | `ApiAppViewSet` — 第三方应用管理 CRUD<br>`OpenApiTokenViewSet` — 凭证管理 CRUD + 重新生成<br>`WebhookSubscriptionViewSet` — 事件订阅管理 CRUD<br>`OpenApiLogViewSet` — API 调用日志（只读） |
