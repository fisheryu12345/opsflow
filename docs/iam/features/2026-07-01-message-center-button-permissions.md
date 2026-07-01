# IAM 初始化脚本修复 + 消息中心按钮权限

> 提交: 5ad24b89 | 日期: 2026-07-01
> 涉及 App: iam
> 类型: 功能修复 + 功能新增

---

## 背景

消息中心普通用户打开白屏，根因有两个：
1. `init_iam.py` 中的菜单 `component` 值带 `views/` 前缀，前端 `import.meta.glob` 的正则 `replace(/..\/views|../, '')` 处理后无法匹配到正确的 Vue 组件文件，导致路由注册失败
2. 消息中心没有 `MenuButton` 条目，`CustomPermission` 检查时非 superadmin 用户一律 403

## 实现方案

### 修复 component 路径（`init_iam.py`）

将所有 `MENU_TREE` 中的 `component` 值去掉 `views/` 前缀：

```python
# 错误
'component': 'views/apps/dashboard/index'
# 正确
'component': 'apps/dashboard/index'
```

前端动态导入解析逻辑（`backEnd.ts` 第 197-210 行）：
```typescript
const k = key.replace(/..\/views|../, '');  // 去掉 '../views' 前缀
return k.startsWith(`${component}`) || k.startsWith(`/${component}`);
```

当 component 为 `system/messageCenter/index` 时，key `../views/system/messageCenter/index.vue` 去掉前缀后变为 `/system/messageCenter/index.vue`，`startsWith` 匹配成功。

### 新增消息中心按钮（`_init_message_center_buttons()`）

创建 5 个 `MenuButton` 条目：

| value | api | method |
|-------|-----|--------|
| `messageCenter:Search` | `/api/system/message_center/` | GET(0) |
| `messageCenter:Retrieve` | `/api/system/message_center/{id}/` | GET(0) |
| `messageCenter:Create` | `/api/system/message_center/` | POST(1) |
| `messageCenter:Update` | `/api/system/message_center/{id}/` | PUT(2) |
| `messageCenter:Delete` | `/api/system/message_center/{id}/` | DELETE(3) |

并将 `messageCenter:Search` 和 `messageCenter:Retrieve` 授予所有活跃角色 — 确保每个角色用户都能查看消息。

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/iam/management/commands/init_iam.py` | 修复 6 个 component 路径，新增 `_init_message_center_buttons()` 方法 |
| `backend/dvadmin/system/views/message_center.py` | MessageCenterViewSet（未改动，依赖方） |
| `web/src/router/backEnd.ts:197-210` | `dynamicImport()` — 前端组件路径解析 |

## 使用方式

重新运行 `python manage.py init_iam` 或执行数据迁移脚本。已存在的记录（`get_or_create`）不受影响。

### 关联文档

- 相关架构文档: [2026-07-01-remove-data-level-permissions-filter-refactor.md](../architecture/2026-07-01-remove-data-level-permissions-filter-refactor.md)
