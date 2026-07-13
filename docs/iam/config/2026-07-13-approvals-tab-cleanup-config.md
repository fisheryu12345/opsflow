# IAM 数据迁移 — 清理 OpsFlow Approvals 标签和权限

> 提交: 88c59d27 | 日期: 2026-07-13
> 涉及 App: iam
> 类型: 配置变更

---

## 变更内容

新增数据迁移 `backend/iam/migrations/0003_remove_opsflow_approvals_tab.py`：

- 删除 `PageTab` 中 `app='opsflow', key='approvals'` 的审批中心页面标签行
- 删除 `IAMPermission` 中 `codename='opsflow:approvals:view'` 的权限记录
- 关联的 `IAMRolePermission` 通过 FK `on_delete=CASCADE` 自动级联删除

```python
def remove_approvals_tab(apps, schema_editor):
    PageTab = apps.get_model('iam', 'PageTab')
    IAMPermission = apps.get_model('iam', 'IAMPermission')
    PageTab.objects.filter(app='opsflow', key='approvals').delete()
    IAMPermission.objects.filter(codename='opsflow:approvals:view').delete()
```

同时从 `seed_iam_page_configs.py` 移除 `opsflow:approvals:view` 权限注册。

## 影响的服务

- **backend (iam)** — 仅迁移操作，无运行时影响

## 部署注意事项

1. 确保 `0002_initial` 迁移已执行
2. 运行 `python manage.py migrate iam` 即可
3. 种子数据命令 `python manage.py seed_iam_page_configs` 已不再包含 approvals 条目的注册

## 回退方式

```bash
python manage.py migrate iam 0002
```

### 关联文档

- 相关架构文档: [2026-07-13-approval-plugin-removal-refactor.md](../../opsflow/architecture/2026-07-13-approval-plugin-removal-refactor.md)
