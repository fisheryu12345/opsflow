# IAM — 开发进度跟踪

> 最后更新: 2026-06-28 | 参考目标: docs/opsflow_target.md

## 成熟度评估

| 维度 | 评估 |
|------|:----:|
| 当前成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 目标成熟度 | ⭐⭐⭐⭐⭐ (5/5) |
| 状态 | ✅ 目标达成（Phase 1-2 多租户基础设施完成） |

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
| seed_itsm_permissions | P1 | ✅ | ITSM 权限种子数据 | management command — 11 itsm:* MenuButton + 3 Role (admin/editor/viewer) + 角色权限 |

## TODO

- [ ] 物理隔离实际启用（创建独立库 → 设 db_alias → migrate）
- [x] 补充测试用例 ✅

### 2026-06-30 Update
> 提交: 80f9ed95
- my_permissions 端点: 新增 — 统一 ITSM 权限查询，支持 ProjectMember + BusinessMember 继承
- ITSM Role 同步: 新增 — signals.py 自动同步 dvadmin Role
- seed_itsm_permissions: 新增 — 一键种子 ITSM 权限体系
- 测试用例: 补充 — test_my_permissions.py (5 cases) + test_signals.py (3 cases)
