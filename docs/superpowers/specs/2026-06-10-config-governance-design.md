# OPSflow 配置治理规范

> **日期:** 2026-06-10
> **状态:** 设计已批准
> **关联设计:** [配置体系重构设计](2026-06-10-config-architecture-design.md)

---

## 1. 背景

配置体系重构完成后（settings.py 拆为 conf/ 分层 + components/ 组件），需要明确定义**新增/修改配置的流程规则**，避免：
- 不知道该改哪个文件
- 新增配置乱放
- 跨环境遗漏

---

## 2. 配置放置决策树

```
要新增/修改一个配置 → 问：
├─ 是原始值（字符串/数字/布尔）？
│   ├─ 所有环境相同？     → conf/env_base.py
│   └─ 不同环境不同值？   → conf/env_dev.py / env_uat.py / env_prod.py
│
├─ 是 Django 结构体（DATABASES、LOGGING）？
│   ├─ 已有对应组件文件？ → application/components/xxx.py
│   └─ 无对应文件？       → 新建组件文件 + settings.py 加 import
│
├─ 是注册新 App？
│   └─ 直接在 settings.py 的 INSTALLED_APPS 加一行
│
└─ 是新增独立配置类别？
    └─ 新建 application/components/xxx.py
       ├─ from conf.env import *（如果需要 env 值）
       └─ 在 settings.py 的组件配置区加 import
```

---

## 3. 分场景规则

### 场景 A：新增/修改 env 值

| 步骤 | 操作 |
|------|------|
| 1 | 先在 `env_base.py` 定义变量 + 注释 + 默认值 |
| 2 | 如需某个环境不同 → 去对应的 `env_dev/uat/prod.py` 覆写 |
| 3 | 若组件文件已 `from conf.env import *` 则该变量自动可用 |

**强制规则：新增变量必须在 env_base.py 声明，禁止只在一个环境文件中单独定义。**

### 场景 B：新增/修改 Django 结构配置

| 步骤 | 操作 |
|------|------|
| 1 | 定位属于哪个组件：database / logging / rest_framework / auth / channels / celery / cors_security / monitor / pipeline |
| 2 | 直接编辑对应的 `application/components/xxx.py` |
| 3 | settings.py 已 `import *`，无需修改 |

**强制规则：找到已有组件文件就直接改，不要绕回 settings.py 塞新变量。**

### 场景 C：注册新 App

直接在 `settings.py` 的 `INSTALLED_APPS` 列表加一行，不触及 conf 或 components。

### 场景 D：新增独立配置类别

| 步骤 | 操作 |
|------|------|
| 1 | 在 `application/components/` 下新建 `xxx.py` |
| 2 | 文件内 `from conf.env import *`（如需要）或直接写字面量 |
| 3 | 在 `settings.py` 组件配置区块加 `from application.components.xxx import *` |
| 4 | 更新 `docs/opsflow/guides/project-standards.md` 中的配置索引 |

---

## 4. 辅助原则

1. **env_base.py 是唯一配置清单** — 需要某个值，先看 base 有没有，没有就先加 base 再加环境覆写。
2. **组件文件不跨域** — `database.py` 不放 LOGGING，`auth.py` 不放 CELERY。不确定归属时新建文件。
3. **新增组件文件要登记** — 同步更新 `project-standards.md` 的组件索引表。
