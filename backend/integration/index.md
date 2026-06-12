# integration — 模块索引

> 上次自动更新: 2026-06-12

---

## `integration/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | 123 |
| `admin.py` | Admin registration for integration models | `ConnectorDefinitionAdmin`<br>`ConnectorInstanceAdmin`<br>`ConnectorCredentialAdmin`<br>`IntegrationLogAdmin` |
| `apps.py` | AppConfig for integration app | `IntegrationConfig` |
| `serializers.py` | Serializers for integration app | `ConnectorDefinitionSerializer` — 连接器定义 — 列表/详情<br>`ConnectorDefinitionCreateUpdateSerializer` — 连接器定义 — 创建/修改<br>`ConnectorInstanceSerializer` — 连接器实例 — 列表/详情<br>`ConnectorInstanceCreateUpdateSerializer` — 连接器实例 — 创建/修改<br>`ConnectorCredentialSerializer` — 连接器凭证 — 列表/详情（解密展示）<br>`ConnectorCredentialCreateUpdateSerializer` — 连接器凭证 — 创建/修改（自动加密） |
| `urls.py` |  | URL configuration for integration app |

## `integration\adapters/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Adapter package for integration app |
| `base.py` | Base connector adapter for Integration Hub | `HealthResult` — 健康检查结果<br>`BaseConnector` — 连接器基类 所有适配器必须实现: - health_check(): 返回 HealthResult - get_client(): 返回外部 SDK 客户端实例 |

## `integration\adapters\ai/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | 123 |
| `anthropic.py` | Anthropic Claude AI connector adapter | `AnthropicConnector` — Anthropic Claude API 连接器适配器 |
| `openai.py` | OpenAI-compatible AI connector adapter | `OpenAIConnector` — OpenAI 兼容 API 连接器适配器 |

## `integration\adapters\auth/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Auth adapter package |

## `integration\adapters\cloud/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Cloud adapter package |
| `aliyun.py` | Aliyun Cloud connector adapter | `AliyunConnector` — 阿里云 ECS 适配器 配置项: - region: 地域 (default: cn-hangzhou) - endpoint: API 端点 |

## `integration\adapters\notification/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Notification adapter package |
| `dingtalk.py` | DingTalk Bot notification adapter | `DingtalkBotConnector` — 钉钉群机器人适配器 支持 text / markdown / link 消息类型 |
| `email_adapter.py` | Email (SMTP) notification adapter | `EmailSmtpConnector` — SMTP 邮件适配器 |
| `sms.py` | SMS notification adapter | `AliyunSmsConnector` — 阿里云短信适配器 配置项: - sign_name: 短信签名 - template_code: 短信模板编码 |
| `wecom.py` | WeCom Bot notification adapter | `WeComBotConnector` — 企业微信群机器人适配器 支持 text 和 markdown 消息类型 |

## `integration\management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands for integration app |

## `integration\management\commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Management commands package |

## `integration\models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Re-export all models for integration app |
| `connector.py` | Model definitions for Integration Hub | `ConnectorDefinition` — 连接器定义 描述一种连接器类型（如 阿里云ECS、企业微信、短信网关）， 包含其配置 JSON Schema 和实现类路径。<br>`ConnectorInstance` — 连接器实例 连接器定义的一个具体实例，包含实际配置（不含敏感凭证）。 例如 "生产环境阿里云"、"测试环境企业微信"。 |
| `credential.py` | Credential model for Integration Hub | `ConnectorCredential` — 连接器凭证 与连接器实例关联的敏感凭据，AES-256 加密存储。 支持多种凭证类型：access_key / password / token / certificate。 |
| `integration_log.py` | Integration call audit log model | `IntegrationLog` — 集成调用审计日志 记录每一次通过集成中心发起的外部系统调用。 |

## `integration\services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Services package for integration app |
| `credential_service.py` | Credential encryption/decryption service for Integration Hub | `encrypt_credential()` — 加密凭证明文 → 返回加密后的字符串<br>`decrypt_credential()` — 解密凭证密文 → 返回明文 |
| `health_service.py` | Health check service for Integration Hub | `HealthCheckScheduler` — 健康检查调度器 — 定时批量检查所有活跃实例<br>`run_health_check()` — 对单个连接器实例执行健康检查 返回 (is_healthy: bool, message: str) |

## `integration\views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Views package for integration app |
| `connector.py` | ViewSet for ConnectorDefinition and ConnectorInstance | `ConnectorDefinitionViewSet` — 连接器定义管理<br>`ConnectorInstanceViewSet` — 连接器实例管理 |
| `credential.py` | ViewSet for ConnectorCredential | `ConnectorCredentialViewSet` — 连接器凭证管理 |
| `integration_log.py` | ViewSet for IntegrationLog | `IntegrationLogViewSet` — 集成调用日志（只读） |
