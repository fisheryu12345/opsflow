# Integration — 模块索引

> 上次自动更新: 2026-06-30 | 触发提交: 4f73a692

---

## `/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` | - | - |
| `admin.py` | Admin registration for integration models | `ConnectorDefinitionAdmin`, `ConnectorInstanceAdmin`, `ConnectorCredentialAdmin`, `IntegrationLogAdmin` |
| `apps.py` | AppConfig for integration app | `IntegrationConfig` |
| `serializers.py` | Serializers for integration app | `连接器定义`, `连接器定义`, `连接器实例`, `连接器实例` |
| `urls.py` | URL configuration for integration app | - |

## `adapters/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/__init__.py` | Adapter package for integration app | - |
| `adapters/base.py` | Base connector adapter for Integration Hub | `健康检查结果`, `连接器基类` |

## `adapters/ai/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/ai/__init__.py` | - | - |
| `adapters/ai/anthropic.py` | Anthropic Claude AI connector adapter | `Anthropic Claude API 连接器适配器` |
| `adapters/ai/openai.py` | OpenAI-compatible AI connector adapter | `OpenAI 兼容 API 连接器适配器` |

## `adapters/auth/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/auth/__init__.py` | Auth adapter package | - |
| `adapters/auth/ldap.py` | LDAP / Active Directory connector adapter for Integration Hub | `LDAP / Active Directory 连接器适配器` |
| `adapters/auth/saml.py` | SAML Identity Provider connector adapter for Integration Hub | `SAML Identity Provider 连接器适配器` |

## `adapters/automation/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/automation/__init__.py` | Automation adapters — CI/CD, Ansible Tower/AWX, etc. | - |
| `adapters/automation/awx.py` | AWX / Ansible Tower connector adapter | `AWX / Ansible Tower REST API v2 连接器适配器` |

## `adapters/cloud/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/cloud/__init__.py` | Cloud adapter package | - |
| `adapters/cloud/aliyun.py` | Aliyun Cloud connector adapter | `阿里云 ECS 适配器` |

## `adapters/database/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/database/__init__.py` | - | - |
| `adapters/database/neo4j.py` | Neo4j 图数据库连接器适配器 | `Neo4j 图数据库连接器` |

## `adapters/datasource/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/datasource/__init__.py` | Datasource adapters for Integration Hub | - |
| `adapters/datasource/influxdb.py` | InfluxDB datasource connector adapter for Integration Hub | `InfluxDB 数据源连接器适配器 (v2 / Flux)` |
| `adapters/datasource/prometheus.py` | Prometheus datasource connector adapter for Integration Hub | `Prometheus 数据源连接器适配器` |

## `adapters/notification/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `adapters/notification/__init__.py` | Notification adapter package | - |
| `adapters/notification/dingtalk.py` | DingTalk Bot notification adapter | `钉钉群机器人适配器` |
| `adapters/notification/email_adapter.py` | Email (SMTP) notification adapter | `SMTP 邮件适配器` |
| `adapters/notification/sms.py` | SMS notification adapter | `阿里云短信适配器` |
| `adapters/notification/wecom.py` | WeCom Bot notification adapter | `企业微信群机器人适配器` |

## `management/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management/__init__.py` | Management commands for integration app | - |

## `management/commands/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `management/commands/__init__.py` | Management commands package | - |
| `management/commands/seed_integration.py` | Seed connector definitions | `Command` |

## `models/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `models/__init__.py` | Re-export all models for integration app | - |
| `models/connector.py` | Model definitions for Integration Hub | `连接器定义`, `连接器实例` |
| `models/credential.py` | Credential model for Integration Hub | `连接器凭证` |
| `models/integration_log.py` | Integration call audit log model | `集成调用审计日志` |

## `services/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `services/__init__.py` | Services package for integration app | - |
| `services/connector_service.py` | 集成中心 — 连接器服务层 | `获取当前活跃的 AI 连接器实例()`, `获取 AI 连接器，找不到时抛出异常()` |
| `services/credential_service.py` | Credential encryption/decryption service for Integration Hub | `加密凭证明文 → 返回加密后的字符串()`, `解密凭证密文 → 返回明文()` |
| `services/health_service.py` | Health check service for Integration Hub | `健康检查调度器`, `对单个连接器实例执行健康检查()` |

## `views/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `views/__init__.py` | Views package for integration app | - |
| `views/connector.py` | ViewSet for ConnectorDefinition and ConnectorInstance | `连接器定义管理`, `连接器实例管理` |
| `views/credential.py` | ViewSet for ConnectorCredential | `连接器凭证管理` |
| `views/integration_log.py` | ViewSet for IntegrationLog | `集成调用日志（只读）` |
