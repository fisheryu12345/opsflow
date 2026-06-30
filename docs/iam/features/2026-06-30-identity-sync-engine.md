# LDAP/AD Identity Sync Engine

> 提交: 4f73a692 | 日期: 2026-06-30
> 涉及 App: iam
> 类型: 功能新增

---

## 背景

企业用户需要通过 LDAP/Active Directory 同步组织架构（部门树）和用户数据到系统，同时支持 LDAP Bind 认证。系统需要支持：
- 从 LDAP/AD 读取 OU 结构并同步为本地 Dept 树
- 从 LDAP/AD 读取用户并同步为本地 Users，关联到对应部门
- LDAP Bind 认证作为 Django auth backend
- DeptMapping/UserMapping 追踪远端到本地的映射关系
- 差异对比（diff）算法实现增量同步
- APScheduler 定时任务调度

## 实现方案

### 核心架构

同步引擎位于 `iam/sync/`，作为 IAM 身份管理的一部分。它不直接管理连接，而是消费集成中心（Integration Hub）的 `ConnectorInstance` 来获取连接配置和凭证。

```
集成中心 (ConnectorInstance)
     ↓ 配置 + 凭证
IAM Sync Engine
  ├── DeptMapping / UserMapping  (映射追踪)
  ├── Differ.diff_depts()        (部门树对比)
  ├── Differ.diff_users()        (用户列表对比)  
  ├── LDAPSyncProvider           (同步执行器)
  └── LDAPBackend                (Django 认证)
```

### 关键代码

**映射模型** (`iam/sync/models.py:20-68`)：
```python
class DeptMapping(models.Model):
    source_instance = ForeignKey('integration.ConnectorInstance', ...)
    dept = ForeignKey('system.Dept', ...)
    remote_dn = CharField(max_length=512, db_index=True)  # LDAP 唯一标识
    remote_attrs = JSONField(default=dict)                # 远端属性快照

class UserMapping(models.Model):
    source_instance = ForeignKey('integration.ConnectorInstance', ...)
    user = ForeignKey('system.Users', ...)
    remote_dn = CharField(max_length=512, db_index=True)
    remote_attrs = JSONField(default=dict)
```

**Diff 算法** (`iam/sync/differ.py:86-130`)：
```python
class Differ:
    @staticmethod
    def diff_depts(remote_nodes, local_mappings) -> DeptDiff:
        # remote - local = added
        # local - remote = disabled (status=False, 不删除)
        # remote ∩ local, attrs changed = updated

    @staticmethod
    def diff_users(remote_users, local_mappings, dept_dn_to_id) -> UserDiff:
        # 用户通过 department 属性关联到 Dept
        # 同样三向对比：add / disable / update
```

**同步执行器** (`iam/sync/provider.py:55-82`)：
```python
class LDAPSyncProvider(BaseSyncProvider):
    def sync_full(self) -> SyncResult:
        # Phase 1: fetch_depts → diff_depts → apply_dept_diff
        # Phase 2: fetch_users → diff_users → apply_user_diff
        # 结果包含 stats: dept_added/updated/disabled, user_added/updated/disabled
```

**认证后端** (`iam/sync/backends.py:24-65`)：
```python
class LDAPBackend(ModelBackend):
    def authenticate(self, request, username, password):
        # 遍历所有启用的 LDAP/AD ConnectorInstance
        # LDAP Bind → 搜索用户 → 查找 UserMapping → JIT 创建
```

### 数据流

```
LDAP/AD Server
    ↓ fetch (ldap3 SUBTREE 搜索)
LDAPSyncProvider
    ↓ DeptNode / UserEntry 列表
Differ.diff_depts()
    ↓ DeptDiff {added, updated, disabled}
_apply_dept_diff()
    ↓ Dept.objects.create/update + DeptMapping
Differ.diff_users()
    ↓ UserDiff {added, updated, disabled}
_apply_user_diff()
    ↓ Users.objects.create/update + UserMapping
IntegrationLog (审计记录)
```

### 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| LDAP 库 | `ldap3`（纯 Python） | 避免 `python-ldap` 在 Windows 上的编译问题 |
| 同步日志 | 复用 `IntegrationLog` | 与集成中心统一审计 |
| 永不删除 | 远端删除→本地禁用 | 防止误删数据 |
| 映射模型 | DEPT/UserMapping 独立表 | 便于增量 diff 和父链重建 |
| 同步与认证分离 | LDAPBackend 只认证，同步引擎同步 | 职责清晰，JIT 创建兜底 |

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/iam/sync/models.py:20-118` | DeptMapping + UserMapping 映射模型 |
| `backend/iam/sync/differ.py:1-170` | DeptDiff + UserDiff 纯算法，无 I/O |
| `backend/iam/sync/provider.py:1-220` | BaseSyncProvider + LDAPSyncProvider 同步执行 |
| `backend/iam/sync/backends.py:1-130` | LDAPBackend Django 认证后端 |
| `backend/iam/sync/views.py:1-280` | 同步触发 API + SAML ACS 端点 |
| `backend/iam/sync/jobs.py:1-100` | APScheduler 定时任务注册 |
| `backend/iam/migrations/0005_add_sync_mappings.py` | 映射表迁移 |

## 使用方式

1. 在集成中心配置 LDAP/AD 连接器实例（host, port, bind_dn, password, base_dn）
2. 测试连接（health_check 验证 LDAP Bind）
3. 在集成中心 → 身份同步 Tab 点击「立即同步」
4. 或等待定时任务按 cron 配置自动同步
5. LDAP 用户通过统一登录页直接输入 LDAP 账号密码即可登录
