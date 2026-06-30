# Integration Hub — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐☆☆ (3/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 差距 | 连接器管理就绪，但凭证加密存储未实现，运行监控(熔断/重试/健康检查)未建设 |

## 功能点清单

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| ConnectorDefinition 定义 | P0 | ✅ | 连接器类型定义 | 名称、版本、协议(REST/SSH)、表单 schema |
| ConnectorInstance 实例 | P0 | ✅ | 连接器具体配置 | 实例 CRUD，business FK 新增，status 在线/离线/异常 |
| ConnectorCredential 凭证 | P1 | 🔄 | 加密存储凭证 | credential 模型存在(encrypted_config)，<b>实际加密未实现(明文存储)</b> |
| IntegrationLog 日志 | P1 | ✅ | 调用日志 | method/url/status/duration/error 完整 |
| 运行监控 | P2 | 📅 | 熔断/重试/健康检查 | — |
| 连接池管理 | P2 | 📅 | 连接池复用 | — |
| AI 连接器 | P1 | ✅ | DeepSeek/OpenAI/Anthropic 适配 | connector_service.get_ai_connector() 完整，opsagent 通过此接口使用 AI |
| 协议适配扩展 | P2 | 📅 | REST/SOAP/SNMP/gRPC 统一抽象 | — |
| 前端页面 | P1 | ✅ | 连接器管理界面 | ConnectorManager + CredentialPanel + RunMonitor 视图 |
| 多租户隔离 | P2 | ✅ | Business FK | ConnectorInstance 已加 business FK |
| LDAP 连接器适配器 | P1 | ✅ | LDAP/AD 目录连接测试与搜索 | LDAPConnector (health_check + search + _bind), 复用 ConnectorCredential 存储 Bind DN+密码 |
| SAML 连接器适配器 | P1 | ✅ | SAML IdP metadata 验证 | SAMLConnector (health_check + metadata 验证) |
| 身份同步 Tab | P1 | ✅ | 集成中心身份同步管理 | identity-sync.vue 卡片+历史模式，复用 cloud-sync 模板 |

### 2026-06-30 Update (Identity Sync)
> 提交: a8358e14
- 连接器适配器: LDAPConnector(ldap3) + SAMLConnector，注册为 category=auth
- Seed 数据: ldap/saml 连接器定义加入 seed_opsflow.py
- 前端: 集成中心新增身份同步 Tab + 字段映射组件
- 文档: LDAP/SAML 配置指南 + 功能文档

## TODO

### P1
- [ ] 凭证加密存储（vault/django-fernet-fields）
- [ ] AI 连接器可用性监控（当前无健康检查）

### P2
- [ ] 运行监控（熔断/重试）
- [ ] 连接池管理
- [ ] 协议适配扩展
- [ ] 补充测试用例
