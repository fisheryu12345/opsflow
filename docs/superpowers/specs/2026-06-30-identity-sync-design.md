# LDAP/AD/SAML 身份同步与认证集成方案

## Overview

支持从 LDAP、Active Directory、SAML IdP 同步企业组织架构（部门树）和用户数据到系统，同时提供 LDAP Bind 认证和 SAML SSO 登录能力。系统为单一组织，部门通过 Dept 树形结构管理。

## 核心设计原则

- **集成中心（Integration Hub）负责连接管理**：注册连接器类型、配置实例、存储凭证、健康检查
- **IAM 负责身份同步**：部门 Diff、用户 Diff、映射追踪、APScheduler 调度
- **单向同步**：LDAP/AD/SAML 作为权威数据源，数据流向系统，远端删除只标记本地禁用
- **LDAP Bind + SAML SSO 混合认证**

## 架构

```
集成中心 (integration/)
  ├── ConnectorDefinition (ldap/saml 注册)
  ├── ConnectorInstance (每个 LDAP 服务器 / SAML IdP 为一个实例)
  ├── ConnectorCredential (AES-256 加密凭证)
  ├── adapters/auth/ldap.py (LDAPConnector → health_check)
  └── adapters/auth/saml.py (SAMLConnector → health_check)

IAM 同步引擎 (iam/sync/)
  ├── models.py (DeptMapping, UserMapping)
  ├── provider.py (BaseSyncProvider + LDAPSyncProvider)
  ├── differ.py (DeptDiff / UserDiff 算法)
  ├── backends.py (LDAPBackend → Django auth chain)
  └── jobs.py (APScheduler 定时任务)
```

## 后端数据模型

### ConnectorDefinition（集成中心已有）

新增两条记录：
- `code=ldap`, `category=auth` → LDAP/AD 连接器
- `code=saml`, `category=auth` → SAML IdP 连接器

### DeptMapping / UserMapping（IAM sync 新增）

- `DeptMapping`: source_instance (FK→ConnectorInstance) + dept (FK→Dept) + remote_dn + remote_attrs
- `UserMapping`: source_instance (FK→ConnectorInstance) + user (FK→Users) + remote_dn + remote_attrs

## 同步引擎流程

```
1. test_connection() → health_check 验证 LDAP Bind
2. fetch_all_depts() → 读取 OU 树
3. diff_depts() → remote - local = add, local - remote = disable
4. apply_dept_diff() → 增/禁 Dept
5. fetch_all_users() → 搜索用户
6. diff_users() → 同上，每个用户关联到 Dept
7. apply_user_diff() → 增/禁 User
8. 写 IntegrationLog
```

## 认证层

- `LDAPBackend`：依次尝试启用的 LDAP/AD 实例，Bind 成功后查找或 JIT 创建用户
- `SAML SP`：POST `/api/iam/saml/acs/{id}/` 接收断言，验证签名后匹配用户
- 认证链：CustomBackend → LDAPBackend

## API 端点

| 端点 | 说明 |
|------|------|
| POST /api/iam/sync/{instance_id}/trigger/ | 手动触发同步 |
| GET /api/iam/sync/{instance_id}/mappings/ | 查看映射状态 |
| GET /api/iam/sync/status/ | 同步概览 |
| POST /api/iam/saml/acs/{instance_id}/ | SAML ACS |
| GET /api/iam/saml/metadata/{instance_id}/ | SP metadata |

## 前端

- 集成中心新增「身份同步」Tab
- 每个 LDAP/AD/SAML 实例显示为状态卡片（同步/历史/立即同步）
- 实例编辑表单通过 config_schema 自动渲染字段映射
- 登录页显示 SAML SSO 按钮

## 实现阶段

Phase 1: ldap3/python3-saml 安装 + 适配器
Phase 2: 映射模型 + 同步引擎 + Differ
Phase 3: LDAPBackend + SAML ACS + 认证链
Phase 4: APScheduler 定时任务 + API
Phase 5: Seed 数据
Phase 6: 前端集成中心 Tab + 字段映射组件
Phase 7: 登录页 SAML 按钮
Phase 8: 测试

## 验证方式

- LDAPBackend mock 测试、Differ 算法测试
- 创建 ConnectorInstance → health_check → 触发同步 → 验证映射
- 前端 Tab 可见 → 配置实例 → 同步 → 查看结果
- LDAP 用户登录 → LDAPBackend 返回 JWT → 跳转首页
- SAML IdP 配置 → 登录页跳转 → 回调获取 JWT
