# LDAP/SAML Connector Adapters

> 提交: 4f73a692 | 日期: 2026-06-30
> 涉及 App: integration
> 类型: 功能新增

---

## 背景

集成中心（Integration Hub）需要扩展对 LDAP/AD 和 SAML 身份源的支持。新增两类连接器适配器，注册为 `ConnectorDefinition`（category=auth），使用已有 `CONnectorInstance/ConnectorCredential/IntegrationLog` 体系。

## 实现方案

### 核心架构

```
integration/adapters/auth/
  ├── __init__.py          (已有)
  ├── ldap.py              LDAPConnector
  └── saml.py              SAMLConnector
```

两个适配器均继承 `BaseConnector`（`integration/adapters/base.py:19-52`），实现 `health_check()` 和 `get_client()`。

### 关键代码

**LDAPConnector** (`integration/adapters/auth/ldap.py:26-120`)：

```python
class LDAPConnector(BaseConnector):
    def health_check(self) -> HealthResult:
        # 使用存储的 Bind DN + 密码尝试 LDAP Bind
        conn = self._bind()
        return HealthResult(is_healthy=conn.bound, message=str(conn.result))

    def get_client(self) -> Connection:
        return self._bind()

    def search(self, search_filter, attributes) -> list:
        # 在 base_dn 下执行 SUBTREE 搜索
        # 返回 [{dn, attributes}]

    def _bind(self):
        # 从 ConnectorCredential 读取 bind_dn(password 类型凭证)
        # bind_dn = cred.name, password = decrypt_credential(cred.encrypted_value)
        # ldap3.Connection(server, user=bind_dn, password=password, auto_bind=True)
```

**SAMLConnector** (`integration/adapters/auth/saml.py:26-95`)：

```python
class SAMLConnector(BaseConnector):
    def health_check(self) -> HealthResult:
        # 验证 metadata_url 可达且返回有效 XML
        # 或仅检查 entity_id 是否配置

    def get_client(self):
        # 返回配置字典（SAML 不需要传统 client）
```

### 连接器定义注册

在 `seed_opsflow.py` 中注册两条记录（`connection_definitions` 列表）：

```python
{"code": "ldap", "name": "LDAP / Active Directory", "category": "auth",
 "provider_class": "integration.adapters.auth.ldap.LDAPConnector",
 "config_schema": {
   "host": {"title": "服务器地址", "default": "ldap.example.com"},
   "port": {"title": "端口", "type": "integer", "default": 389},
   "use_ssl": {"title": "启用 SSL", "type": "boolean"},
   "base_dn": {"title": "Base DN"},
   "user_search_filter": {"title": "用户搜索过滤", "default": "(objectClass=person)"},
   "dept_search_filter": {"title": "部门搜索过滤", "default": "(objectClass=organizationalUnit)"},
   "username_attr": {"title": "用户名属性", "default": "sAMAccountName"},
   "sync_cron": {"title": "同步定时（cron）", "default": "0 2 * * *"},
   "field_mapping": {"title": "字段映射 JSON"},
 }}

{"code": "saml", "name": "SAML Identity Provider", "category": "auth",
 "provider_class": "integration.adapters.auth.saml.SAMLConnector",
 "config_schema": {
   "entity_id": {"title": "IdP Entity ID"},
   "metadata_url": {"title": "IdP Metadata URL"},
   "attr_username": {"title": "用户名属性", "default": "nameId"},
   "attr_name": {"title": "姓名属性", "default": "displayName"},
   "attr_email": {"title": "邮箱属性", "default": "email"},
 }}
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| LDAP 库 | ldap3 | 纯 Python，零 C 依赖，跨平台兼容 |
| 凭证类型 | password（Bind DN 存入 name 字段） | 复用已有 ConnectorCredential AES-256 加密 |
| 连接测试 | `health_check()` | 复用集成中心已有模式（阿里云 ECS 适配器同款） |
| 同步逻辑位置 | 在 iam/sync/ 中 | 集成中心只负责连接管理，不负责身份领域逻辑 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/integration/adapters/auth/ldap.py:26-120` | LDAPConnector — health_check + search + bind |
| `backend/integration/adapters/auth/saml.py:26-95` | SAMLConnector — health_check + metadata 验证 |
| `backend/opsflow/management/commands/seed_opsflow.py:735-756` | 注册 ldap/saml 连接器定义 |

## 使用方式

1. 运行 `python manage.py seed_opsflow` 注册连接器定义
2. 在集成中心 → 连接器实例 → 添加实例，类型选择 LDAP/AD 或 SAML
3. 配置连接参数和凭证
4. 点击「检查」测试连接（health_check）
5. 在身份同步 Tab 使用同步功能
