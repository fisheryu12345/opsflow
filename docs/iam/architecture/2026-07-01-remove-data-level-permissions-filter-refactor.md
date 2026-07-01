# 删除 dvadmin DataLevelPermissionsFilter（废弃过滤器）

> 提交: e3761d79 | 日期: 2026-07-01
> 涉及 App: iam, opsflow
> 类型: 重构

---

## 动机

`DataLevelPermissionsFilter` 是 dvadmin 旧权限体系的产物，已被 IAM 新系统取代。它基于 `RoleMenuButtonPermission.data_range` 做数据行级过滤，但存在以下问题：

1. **已损坏** — 重构提取 `_extracted_from_filter_queryset_33` 方法时漏洞 `api` 和 `method` 变量定义，所有非 superadmin 请求都报 `NameError: name 'api' is not defined`
2. **已被绕过** — `MessageCenterViewSet`、`RoleMenuButtonPermissionViewSet` 等已显式 `extra_filter_backends = []` 关掉
3. **IAM 已覆盖** — `CustomPermission` 做 API 级权限控制，`TenantPermission` 做项目级权限控制，不需要额外的数据级过滤器

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `dvadmin/utils/filters.py` | 170 行，包含 `get_dept()` + `DataLevelPermissionsFilter` | 14 行，只保留 `CustomDjangoFilterBackend` |
| `dvadmin/utils/viewset.py` | 引用 `DataLevelPermissionsFilter` 并设为 `extra_filter_class` 默认值 | 移除引用，删除 `extra_filter_class`，`filter_queryset` 用 `getattr` 安全读取 |
| `dvadmin/system/views/dept.py` | 2 个 `@action` 传 `extra_filter_class=[]` | 去掉该参数（类属性已不存） |

### 代码对比

```python
# 重构前 — viewset.py 第 39 行
extra_filter_class = [DataLevelPermissionsFilter]

def filter_queryset(self, queryset):
    for backend in set(set(self.filter_backends) | set(self.extra_filter_class or [])):
        queryset = backend().filter_queryset(self.request, queryset, self)

# 重构后
# extra_filter_class 被彻底删除
def filter_queryset(self, queryset):
    for backend in set(set(self.filter_backends) | set(getattr(self, 'extra_filter_class', []) or [])):
        queryset = backend().filter_queryset(self.request, queryset, self)
```

### 设计决策

**为什么直接删不保留？** `DataLevelPermissionsFilter` 基于 `data_range` 字段，这个字段是 `RoleMenuButtonPermission` 上的遗留属性。新 IAM 项目角色体系（`ProjectMember.role`）完全覆盖了按人/部门/全部的数据范围需求。

## 迁移说明

无。运行 `git diff --cached` 确认 `filters.py` 中已无 `DataLevelPermissionsFilter` 引用即可。
