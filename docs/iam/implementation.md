# IAM — 开发进度跟踪

> 最后更新: 2026-07-01 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 状态 | ✅ 企业级 RBAC 闭环完成（模型迁移+申请/审批+角色模板+统一授权UI+v-can指令） |

## 功能点清单

> IAM 在 opsflow_target.md 中作为系统管理的子能力出现，非独立子产品。当前实现覆盖所有需求。

| 功能模块 | 优先级 | 状态 | 目标描述 | 当前实现 |
|---------|:------:|:----:|---------|---------|
| Business 模型 | P0 | ✅ | 业务线 — 核心隔离单位 | 完整：name/code/group/db_alias/created_at，CRUD API |
| BusinessGroup 分组 | P1 | ✅ | 可选视觉分组 | name/code/sort/is_active，无权限语义 |
| DeployEnvironment 环境 | P0 | ✅ | 全局横切环境定义 | dev/staging/prod 种子数据，risk_level(0-100) |
| Project (从 opsflow 迁入) | P0 | ✅ | 运维工作空间 | 11 个已有项目迁入，business FK 可空向后兼容 |
| ProjectMember 项目成员 | P0 | ✅ | admin/editor/viewer 角色 | 14 个成员已迁入，Business 角色向下继承 |
| BusinessMember 业务成员 | P0 | ✅ | 业务线角色 | Admin 自动继承 Project Admin 权限 |
| DeployEnvironmentPermission | P0 | ✅ | 环境执行授权 | 显式授权，不继承，prod 需手动授权 |
| TenantPermission | P0 | ✅ | DRF 权限后端 | has_project_role 检查 + Business 继承 |
| EnvironmentGatePermission | P0 | ✅ | 环境门禁 | can_execute + prod 需 editor+ |
| resolvers 权限解析 | P0 | ✅ | 7 个公开函数 | get_visible_projects/get_visible_businesses/has_project_role/can_execute_in_environment |
| ApiToken 增强 | P1 | ✅ | Token 绑定 Business+Env | 按业务线/环境范围控制外部 API |
| OperationRecord 增强 | P1 | ✅ | 审计记录加业务线归属 | business_id + project_id 冗余字段 |
| 权限申请审批 | P1 | ✅ | 用户自助申请角色/菜单 | PermissionRequest + UserDirectPermission |
| 物理隔离扩展点 | P2 | ✅ | TenantDatabaseRouter | 骨架已建，Business.db_alias 预留，当前始终返回 default |
| 管理前端 | P1 | ✅ | Business/Environment/Project 管理页面 | BusinessManage/EnvironmentManage + i18n (中英各 90+ key) |
| grant_default_env_permissions | P1 | ✅ | 批量授权 dev+staging | management command |
| seed_deploy_environments | P1 | ✅ | 初始化环境 | management command |
| my_permissions 端点 | P0 | ✅ | 返回用户 ITSM 权限 (role + pages + permissions) | GET /api/iam/my_permissions/?project_id=X — 查 ProjectMember/BusinessMember 确定 role → 返回 visible pages + itsm:* perm keys |
| ITSM Role 自动同步 | P0 | ✅ | IAM 成员变更自动分配/移除 dvadmin Role | signals.py — BusinessMember/ProjectMember post_save/post_delete → _sync_dvadmin_role() |
| seed_itsm_permissions | P1 | ✅ | ITSM 权限种子数据 | management command — 11 itsm:* MenuButton + 3 Role |
| RBAC 模型迁移 | P0 | ✅ | Role/Menu/MenuButton → IAM | iam/models/menu_rbac.py，19 文件 import 替换，旧 dvadmin 模型移除 |
| 统一授权 UI | P0 | ✅ | Role 权限配置面板 | RolePermissionPanel.vue — 菜单树+按钮勾选+一键保存 |
| 角色模板 | P0 | ✅ | 预定义角色模板 | RoleTemplate 模型 + apply_to_role() + 7 个系统模板 |
| 审批增强 | P0 | ✅ | business admin 可审批 + project_role | PermissionRequest 扩展 target_project/target_project_role，approve 自动创建 ProjectMember |
| 权限申请 UI | P0 | ✅ | 菜单+按钮 checkbox 选择 | MyRequests 扩展 project_role 类型 + 项目选择器 + 按钮分组 grid |
| v-can 指令 | P0 | ✅ | 无权限自动拦截+弹出申请 | directive/iamPermission.ts + RequestPermission.vue 全局弹窗 |
| 全 App 权限 Key | P0 | ✅ | ITSM+OPSflow+CMDB 权限注册 | seed_iam_permissions + init_iam 一键初始化 |
| 通知 | P1 | ✅ | 审批结果站内信 | _notify_user → MessageCenter |
| 旧权限体系清理 | P0 | ✅ | 删除 v-auth/v-permission/btnPermission | 14 个文件删除 + 7 个页面 v-auth 剥离 |
| 身份同步引擎 | P1 | ✅ | LDAP/AD 部门+用户同步 | DeptMapping/UserMapping + Differ + LDAPSyncProvider + LDAPBackend + SAML ACS |
| LDAP/SAML 连接器 | P1 | ✅ | 集成中心身份源适配器 | LDAPConnector + SAMLConnector (health_check/search) |

## TODO

- [ ] 物理隔离实际启用（创建独立库 → 设 db_alias → migrate）
- [ ] IAM 权限全链路测试：申请→审批→赋权→前端按钮显隐

### 2026-07-01 Update
> 提交: 6e98e98a
- RBAC 模型迁移: Role/Menu/MenuButton → iam/models/menu_rbac.py，19 文件 import 替换
- 企业级 RBAC 闭环: 角色模板 + 统一授权 UI + 审批增强 + v-can 指令 + 全 App 权限 Key
- 清理: ApiWhiteList/Area/Dictionary 模型 + fixtures + 旧权限指令(14 文件)
- 已知问题: 权限全链路测试未完成

### 2026-06-30 Update (Identity Sync)
> 提交: 6e98e98a
- 身份同步引擎: 新增 — DeptMapping/UserMapping 模型 + Differ 对比算法 + LDAPSyncProvider + LDAPBackend
- 连接器适配器: 新增 — LDAPConnector + SAMLConnector（复用集成中心体系）
- 前端: 新增 — 集成中心身份同步 Tab + SAML SSO 登录按钮
- 文档: 生成 — 设计方案、功能文档、配置指南

### 2026-07-01 Update
> 提交: (pending push)
- ...
### 2026-06-30 Update
> 提交: 80f9ed95
- my_permissions 端点: 新增 — 统一 ITSM 权限查询，支持 ProjectMember + BusinessMember 继承
- ITSM Role 同步: 新增 — signals.py 自动同步 dvadmin Role
- seed_itsm_permissions: 新增 — 一键种子 ITSM 权限体系
- 测试用例: 补充 — test_my_permissions.py (5 cases) + test_signals.py (3 cases)
