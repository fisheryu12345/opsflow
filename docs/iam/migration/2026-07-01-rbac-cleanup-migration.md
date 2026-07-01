# RBAC 模型迁移指南 — dvadmin 旧体系 → IAM 单体系

> 提交: 3ade6b9e | 日期: 2026-07-01
> 涉及 App: iam
> 类型: 破坏性变更

---

## 变更内容

旧 RBAC 模型（Role, MenuButton, RoleMenuPermission, RoleMenuButtonPermission）已被移除。
所有功能迁移到 IAM 模型（IAMRole, IAMPermission, IAMRolePermission, IAMUserRole, IAMMenu）。

## 影响范围

- **API**: 旧端点 `/api/iam/menu_button/`, `/api/iam/role_menu_permission/`, `/api/iam/role_menu_button_permission/` 已删除
- **Model import**: `iam.models.menu_rbac.Role` 等引用需要改为 `iam.models.permission.IAMRole`
- **ORM 查询**: `user.role` 需要改为 `IAMUserRole.objects.filter(user=user)`
- **DB 表**: 数据保留未删（安全）

## 迁移步骤

1. 同步代码到本地：`git pull`
2. 安装依赖（如有变化）：`pip install -r requirements.txt`
3. 运行迁移：`python manage.py migrate iam --fake` 和 `python manage.py migrate`
4. 启动后端验证：`python manage.py runserver`
5. 启动前端验证：`cd web && npm run dev`
6. 检查以下页面正常工作：
   - 侧边栏菜单渲染
   - IAM → 我的权限
   - IAM → 申请
   - IAM → 审批
   - 角色管理（admin → 角色）
   - 菜单管理（admin → 菜单）

## 回退方案

`git revert HEAD` 回退本次提交，重新运行 `python manage.py migrate`。

## 兼容性说明

旧系统已完全移除，不再兼容旧 Role/MenuButton 导入。
