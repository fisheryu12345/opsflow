# LDAP/AD/SAML 身份同步配置指南

## 概述

系统通过**集成中心**统一管理 LDAP/AD/SAML 身份源。配置分为两步：

1. **在集成中心创建连接器实例** — 配置服务器地址、凭证、字段映射
2. **使用身份同步功能** — 测试连接、手动或定时同步组织架构

完成后效果：
- LDAP/AD 中的部门树（OU）自动同步为系统的 Dept 树
- LDAP/AD 中的用户自动同步为系统的 Users，并关联到对应部门
- 用户通过 LDAP Bind 或 SAML SSO 登录

---

## 目录

- [一、前置条件](#一前置条件)
- [二、配置 LDAP/AD 连接器](#二配置-ldapad-连接器)
- [三、LDAP 字段映射说明](#三ldap-字段映射说明)
- [四、执行 LDAP 同步](#四执行-ldap-同步)
- [五、配置 SAML SSO](#五配置-saml-sso)
- [六、LDAP Bind 登录验证](#六ldap-bind-登录验证)
- [七、常见问题](#七常见问题)

---

## 一、前置条件

### 1.1 环境要求

- ldap3（纯 Python，已安装）
- python3-saml（已安装）
- 系统已运行 `migrate`（`opsflow_iam_sync_dept_mapping` 和 `opsflow_iam_sync_user_mapping` 表已创建）

### 1.2 需要准备的信息

**LDAP/AD 配置：**

| 信息 | 说明 | 示例 |
|------|------|------|
| 服务器地址 | LDAP 服务器 IP 或域名 | `192.168.1.100` |
| 端口 | 389（非 SSL）或 636（SSL） | `389` |
| Base DN | 搜索根目录 | `dc=example,dc=com` |
| Bind DN | 绑定账号的完整 DN | `cn=admin,dc=example,dc=com` |
| Bind 密码 | 绑定账号的密码 | |
| 用户搜索过滤 | 匹配用户的 LDAP 过滤条件 | `(objectClass=person)` |
| 部门搜索过滤 | 匹配部门的 LDAP 过滤条件 | `(objectClass=organizationalUnit)` |
| 用户名属性 | 对应用户名字段的 LDAP 属性 | `sAMAccountName`（AD）或 `uid`（OpenLDAP） |

**SAML 配置：**

| 信息 | 说明 |
|------|------|
| IdP Entity ID | SAML IdP 的唯一标识 |
| IdP Metadata URL | IdP 的 metadata XML 地址 |
| 用户名属性 | SAML 断言中用户名字段的属性名 |
| 姓名属性 | SAML 断言中姓名字段的属性名 |
| IdP 证书 | （可选）IdP 的 x509 签名证书 |

---

## 二、配置 LDAP/AD 连接器

### 步骤 1：访问集成中心

1. 登录系统（超级管理员账号）
2. 左侧菜单导航到 **集成中心**（或访问 `/#/interhub`）

### 步骤 2：添加连接器实例

1. 切换到 **连接器实例** Tab
2. 点击右上角 **「添加实例」** 按钮

   ![添加实例](https://via.placeholder.com/400x60?text=添加实例+按钮)

3. 在弹出的对话框中填写：

   | 字段 | 说明 |
   |------|------|
   | **类型** | 选择 `LDAP / Active Directory` |
   | **名称** | 给这个 LDAP 源起个名字，如 `公司AD` |

4. 点击确定后，在实例列表中会出现刚创建的实例

### 步骤 3：配置连接参数

1. 在实例列表中，点击该实例的 **「配置」** 按钮
2. 在弹出的编辑对话框中填写连接信息：

   ```
   服务器地址:     ldap.company.com
   端口:          389
   启用 SSL:      关闭
   Base DN:       dc=company,dc=com
   用户搜索过滤:  (&(objectClass=person)(objectClass=user))
   部门搜索过滤:  (objectClass=organizationalUnit)
   用户名属性:    sAMAccountName
   同步定时:      0 2 * * *       (每天凌晨2点自动同步)
   字段映射 JSON:
     {"username":"sAMAccountName","name":"displayName","email":"mail","mobile":"telephoneNumber"}
   ```

   > **关于字段映射：**
   > - `username` = `sAMAccountName`（AD 用户的登录名）
   > - `name` = `displayName`（AD 的显示名称）
   > - `email` = `mail`（邮箱）
   > - `mobile` = `telephoneNumber`（电话）
   >
   > 如果使用 OpenLDAP，通常：
   > - `username` = `uid`
   > - `name` = `cn`
   > - `email` = `mail`

### 步骤 4：配置凭证（Bind 账号）

1. 在同一个编辑对话框中，找到 **凭证管理** 区域
2. 点击 **「添加凭证」**
3. 填写：

   | 字段 | 值 |
   |------|-----|
   | **类型** | 选择 `密码` |
   | **名称** | 输入 Bind DN，如 `cn=admin,dc=company,dc=com` |
   | **凭证值** | 输入 Bind 密码 |

   > **注意：** LDAP 连接器使用 **第一条 password 类型凭证** 作为 Bind DN（name 字段）和密码（encrypted_value 字段）。

4. 点击 **「保存」**

### 步骤 5：测试连接

1. 在集成中心的连接器实例列表中
2. 找到刚创建的 LDAP 实例
3. 点击该行的 **「检查」** 按钮（健康检查）

   - ✅ 成功：状态变为「在线」，显示「LDAP Bind 成功」
   - ❌ 失败：状态变为「异常」，查看错误消息排查

---

## 三、LDAP 字段映射说明

### 3.1 默认映射

```
字段映射 JSON:
{
  "username": "sAMAccountName",    ← 映射到系统 username 字段
  "name":     "displayName",       ← 映射到系统 name 字段
  "email":    "mail",              ← 映射到系统 email 字段
  "mobile":   "telephoneNumber"    ← 映射到系统 mobile 字段
}
```

### 3.2 常用 AD 属性参考

| AD 属性 | 说明 | 映射字段 |
|---------|------|---------|
| `sAMAccountName` | 登录名（User logon name） | `username` |
| `userPrincipalName` | 用户主体名（user@domain.com） | `username` |
| `displayName` | 显示名称 | `name` |
| `cn` | 通用名称 | `name` |
| `mail` | 电子邮件 | `email` |
| `telephoneNumber` | 电话号码 | `mobile` |
| `department` | 部门名称（用于自动关联到 Dept） | 内部使用 |
| `distinguishedName` | 完整 DN | 内部匹配用 |

### 3.3 常用 OpenLDAP 属性参考

| LDAP 属性 | 说明 | 映射字段 |
|-----------|------|---------|
| `uid` | 用户 ID | `username` |
| `cn` | 通用名称 | `name` |
| `sn` | 姓氏 | 可选 |
| `givenName` | 名 | 可选 |
| `mail` | 电子邮件 | `email` |
| `mobile` | 手机号 | `mobile` |

### 3.4 修改字段映射

1. 在实例的「配置」中，修改 `字段映射 JSON` 的内容
2. 保存后，下次同步时会使用新的映射

---

## 四、执行 LDAP 同步

### 4.1 手动同步

1. 在集成中心中，切换到 **「身份同步」** Tab
2. 会看到所有已配置的 LDAP/AD 身份数据源卡片
3. 点击数据源卡片的 **「立即同步」** 按钮
4. 系统开始执行全量同步，完成后会显示同步结果

   ```
   同步完成
   ─────────────────────────
   新增部门:  5
   更新部门:  2
   禁用部门:  0
   新增用户:  120
   更新用户:  15
   禁用用户:  3
   ```

### 4.2 定时自动同步

在实例配置中填写 `同步定时` 字段（cron 表达式）：

| 场景 | Cron 表达式 |
|------|-------------|
| 每天凌晨 2:00 | `0 2 * * *` |
| 每天凌晨 3:30 | `30 3 * * *` |
| 每 6 小时 | `0 */6 * * *` |
| 工作日每天早 8:00 | `0 8 * * 1-5` |
| 每周日凌晨 1:00 | `0 1 * * 0` |

定时任务由 APScheduler 管理，应用启动时自动注册。

### 4.3 同步逻辑说明

**部门同步：**
- **新增**：LDAP 中有但本地没有的 OU → 自动创建 Dept 并建立父级关联
- **更新**：名称等属性改变 → 更新本地 Dept
- **删除**：LDAP 中已删除的 OU → 本地 Dept 标记为 `status=False`（禁用，不删除）

**用户同步：**
- **新增**：LDAP 中有但本地没有的用户 → 创建 Users + UserMapping
- **更新**：姓名/邮箱/电话/部门改变 → 更新本地 Users
- **删除**：LDAP 中已删除的用户 → 本地标记为 `is_active=False`（禁用，不删除）
- **部门关联**：通过 LDAP 用户的 `department` 属性自动匹配到对应 Dept

---

## 五、配置 SAML SSO

### 5.1 添加 SAML 连接器实例

1. 在集成中心 → **连接器实例** → **添加实例**
2. 类型选择 `SAML Identity Provider`
3. 名称填写如 `企业 SAML IdP`
4. 点击确定

### 5.2 配置 SAML 参数

进入实例的 **「配置」** 编辑：

```
IdP Entity ID:     https://idp.company.com/saml/metadata
IdP Metadata URL:  https://idp.company.com/saml/metadata
用户名属性:        nameId
姓名属性:          displayName
邮箱属性:          email
```

### 5.3 配置凭证（可选）

如果 IdP 要求 SP 提供证书进行签名：

1. 在编辑对话框的凭证管理区域，点击 **「添加凭证」**
2. 类型选择 `证书`
3. 名称填写 `sp_private_key`
4. 值填写 SP 的私钥证书内容

### 5.4 获取 SP Metadata

SAML 连接器配置完成后，系统自动生成 SP metadata，用于在 IdP 侧配置：

```
GET /api/iam/sync/saml/metadata/{实例ID}/
```

返回 XML 示例：

```xml
<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="opsflow-saml-1">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="http://your-server/api/iam/sync/saml/acs/1/"
        index="1"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>
```

将上述 XML 或 metadata URL 配置到企业的 SAML IdP 中。

### 5.5 SAML SSO 登录流程

1. 用户访问系统登录页
2. 点击 **SAML** 按钮
3. 系统跳转到企业 IdP 登录页面
4. 用户在 IdP 侧完成认证
5. IdP 发送 SAML Response 到系统 ACS 端点
6. 系统解析断言，查找或 JIT 创建用户
7. 签发 JWT token，完成登录

---

## 六、LDAP Bind 登录验证

### 6.1 配置认证链

默认配置已生效（无需手动修改）：

```python
# backend/application/components/auth.py
AUTHENTICATION_BACKENDS = [
    "dvadmin.utils.backends.CustomBackend",   # 本地密码登录（始终可用）
    "iam.sync.backends.LDAPBackend",          # LDAP/AD Bind 认证
]
```

认证顺序：
1. 先尝试本地密码（CustomBackend）
2. 如果不匹配，尝试 LDAP Bind（LDAPBackend）
3. LDAPBackend 会依次尝试每个启用的 LDAP/AD 实例

### 6.2 LDAP 用户登录

LDAP 用户使用与 LDAP 中相同的 `username` + `password` 登录：

```
登录页面
├── 用户名:  zhangsan          ← LDAP 中的 sAMAccountName
├── 密码:    ********          ← LDAP 中的密码
└── 点击「登录」
```

登录流程：
1. 系统将 username + password 发送到后端
2. 后端依次尝试认证后端
3. LDAPBackend 连接 LDAP 服务器做 Bind
4. Bind 成功后，查找 UserMapping：
   - 找到 → 直接返回用户
   - 未找到 → JIT 创建用户（拉取 LDAP 属性自动创建）
5. 返回 JWT token，登录成功

### 6.3 首次登录自动创建

如果用户是首次通过 LDAP 登录（尚未同步），系统会自动 JIT 创建：
- 按 `field_mapping` 中的配置创建用户属性
- 自动建立 UserMapping 映射记录
- 后续再次登录时直接匹配

---

## 七、常见问题

### 7.1 连接测试失败

| 错误信息 | 可能原因 | 解决方法 |
|---------|---------|---------|
| `invalidCredentials` | Bind DN 或密码错误 | 检查凭证配置，确认 DN 格式正确 |
| `ldap_connect_timeout` | 服务器地址或端口不可达 | 检查网络连通性、防火墙规则 |
| `LDAP server is not available` | LDAP 服务未启动 | 确认 LDAP 服务运行中 |
| `SSL: CERTIFICATE_VERIFY_FAILED` | SSL 证书问题 | 如果是测试环境，暂时关闭 SSL |

### 7.2 同步成功但用户/部门未出现

1. **检查搜索过滤条件**：
   - `user_search_filter` 太严格 → 放宽条件如 `(objectClass=person)`
   - `dept_search_filter` 不匹配 → 检查 OU 的 objectClass

2. **检查 Base DN**：
   - Base DN 范围太小 → 使用更高的根节点如 `dc=company,dc=com`

3. **检查字段映射**：
   - 确认 LDAP 属性名拼写正确（例如 `sAMAccountName` 大小写敏感）

### 7.3 SAML SSO 无法登录

1. **检查 ACS 地址配置**：确保 IdP 中配置的 ACS URL 与系统实际地址一致
2. **检查 metadata**: 确认 `GET /api/iam/sync/saml/metadata/{id}/` 返回有效 XML
3. **查看 IdP 日志**：SAML 问题通常在 IdP 侧日志中有详细原因

### 7.4 同步定时任务不触发

- 确保 APScheduler 正常工作（系统日志中有 `Registered sync job` 信息）
- 检查 `sync_cron` 格式是否正确（建议先用在线 cron 工具验证）
- 定时任务注册在 `IamConfig.ready()` 中，需要重启应用

### 7.5 修改 LDAP 密码后如何更新

在集成中心的凭证编辑中：
1. 找到对应的 LDAP 实例
2. 点击 **「配置」**
3. 在凭证列表中，修改密码值
4. 点击 **「保存」**

---

## 配置示例汇总

### 场景 A：Windows AD 标准配置

```json
{
  "host": "192.168.1.10",
  "port": 389,
  "use_ssl": false,
  "base_dn": "dc=company,dc=local",
  "user_search_filter": "(&(objectClass=user)(objectCategory=person))",
  "dept_search_filter": "(objectClass=organizationalUnit)",
  "username_attr": "sAMAccountName",
  "sync_cron": "0 3 * * *",
  "field_mapping": {
    "username": "sAMAccountName",
    "name": "displayName",
    "email": "mail",
    "mobile": "telephoneNumber"
  }
}
```
- 凭证：`cn=administrator,cn=users,dc=company,dc=local` / password

### 场景 B：OpenLDAP 标准配置

```json
{
  "host": "ldap.company.com",
  "port": 636,
  "use_ssl": true,
  "base_dn": "dc=company,dc=com",
  "user_search_filter": "(objectClass=inetOrgPerson)",
  "dept_search_filter": "(objectClass=organizationalUnit)",
  "username_attr": "uid",
  "sync_cron": "30 2 * * *",
  "field_mapping": {
    "username": "uid",
    "name": "cn",
    "email": "mail",
    "mobile": "mobile"
  }
}
```
- 凭证：`cn=admin,dc=company,dc=com` / password

### 场景 C：SAML SSO（Okta/Azure AD）

```
IdP Entity ID:    http://www.okta.com/exkxxxxxx
IdP Metadata URL: https://company.okta.com/app/exkxxxxxx/sso/saml/metadata
attr_username:    nameId
attr_name:        firstName
attr_email:       email
```

---

> **相关文档：**
> - [LDAP/AD/SAML 身份同步设计方案](../superpowers/specs/2026-06-30-identity-sync-design.md)
> - [集成中心使用指南]（待补充）
