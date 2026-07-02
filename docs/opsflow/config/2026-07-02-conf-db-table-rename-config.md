# 数据库表名迁移配置变更 — opsflow_system_* → opsflow_iam_* / opsflow_common_*

> 提交: 58f68b5d | 日期: 2026-07-02
> 涉及 App: iam, common, job_platform
> 类型: 配置变更

---

## 变更内容

dvadmin app 迁移后，所有相关数据库表名从 `opsflow_system_*` 重命名为 `opsflow_iam_*` 或 `opsflow_common_*`。

### 表重命名

| 旧表名 | 新表名 | 归属 App |
|--------|--------|---------|
| opsflow_system_users | opsflow_iam_users | iam |
| opsflow_system_dept | opsflow_iam_dept | iam |
| opsflow_system_config | opsflow_common_config | common |
| opsflow_system_operation_log | opsflow_common_operation_log | common |
| opsflow_system_login_log | opsflow_common_login_log | common |
| opsflow_system_file_list | opsflow_common_file_list | common |
| opsflow_system_message_center | opsflow_common_message_center | common |
| opsflow_system_message_center_target_user | opsflow_common_message_center_target_user | common |

### 模型变更

| 旧模型名 | 新模型名 | 新位置 |
|---------|---------|-------|
| Users | IAMUsers | iam/models/users.py |
| Dept | IAMDept | iam/models/dept.py |
| Post | 删除（无外部引用） | — |

### 新增列

job_platform 的 `opsflow_job_dangerous_cmd_rule` 和 `opsflow_job_dangerous_check_log` 表缺少 `creator` 列（CoreModel 基类字段），使用 `ALTER TABLE ADD COLUMN` 补齐。

### PluginLoader 日志

- 移除重复的 `v` 前缀（显示 `v1.0` 而非 `vv1.0`）
- 跳过 `_tower_base` 内部抽象基类的注册到 DB
- 所有中文日志改为英文

## 影响的服务

所有服务需重启：Django 主进程 + Celery

## 部署注意事项

1. `python manage.py migrate` + `--fake` 已执行
2. `opsflow_system_*` 表不再存在，使用旧表名的直连查询需更新

## 回退方式

`git revert` 后重新执行 `ALTER TABLE RENAME` 恢复表名
