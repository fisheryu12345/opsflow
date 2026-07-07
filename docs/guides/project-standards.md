# OPSflow Project & Engineering Standards

## 架构布局

- **Backend:** Django apps under `dvadmin/` (RBAC), `opsflow/` (ops), `opsagent/`,
  `plugins/` — config in `conf/env.py`, settings in `application/settings.py`.
  Reference sources in `reference/` (bk-sops, bk-cmdb, bk-itsm, bk-job, bamboo-engine).
- **Frontend:** `web/src/views/apps/` (OpsFlow app pages), `views/system/` (RBAC),
  `api/` (axios clients), `stores/` (Pinia), `router/`, `utils/`
- **API:** `api/system/*` (RBAC), `api/opsflow/*`, `api/ops/*` (opsagent)
- **Docs:** `docs/architecture/` (架构), `docs/design/` (设计), `docs/knowledge/` (知识库)
- **Deploy:** `deploy/docker/`, `deploy/nginx/`

---

## API Response Convention

All opsflow API responses **MUST** use `DetailResponse` / `ErrorResponse` from `dvadmin.utils.json_response`. **Bare `Response()` or default DRF format is forbidden** — the frontend interceptor requires `code` field in every response.

| Function | When | Signature |
|----------|------|-----------|
| `DetailResponse(data, msg='success')` | Success (any endpoint) | Returns `{"code": 2000, "data": ..., "msg": "success"}` |
| `ErrorResponse(msg, data=None, code=4000, status=400)` | Business error | Returns `{"code": 4000, "data": ..., "msg": "..."}` |
| `SuccessResponse(data, msg='success', page=1, limit=1, total=1)` | Paginated list | Returns `{"code": 2000, "page": ..., "limit": ..., "total": ..., "data": ..., "msg": "success"}` |

| Code | Meaning |
|------|---------|
| `2000` | Success | `4000` | Business error | `401` | Auth | `400` | Bad request |

- Success (no pagination) → `DetailResponse(data=serializer.data)`
- Success (paginated list) → use `self.get_paginated_response()` or `SuccessResponse(data=data, total=count)`
- Business error → `ErrorResponse(msg='something went wrong', code=4000)`

---

## Logging Convention

Use `import logging; logger = logging.getLogger(__name__)` for standard Django logging.
Define module-level `FSM = 'my_func_name'` constant for reusable context labels.

---

## 项目结构规范

### 目录职责

| 目录 | 职责 |
|------|------|
| `backend/` | Django 后端（dvaadmin，application，opsflow，cmdb，itsm 等所有 Django app） |
| `web/` | Vue 3 前端 |
| `refrence/` | 第三方蓝鲸参考源码（只读，不修改） |
| `docs/` | 统一文档，按 Django app 分子目录（opsflow/、cmdb/、itsm/ 等） |
| `deploy/` | 部署配置（docker compose、nginx、Dockerfile） |
| `scripts/` | 全局脚本（数据库维护、CI/CD、环境初始化） |
| `.claude/skills/` | 项目级 Claude 技能 |

**不允许在根目录创建新的顶层目录或文件。** 所有新增内容必须归入以上已有目录。

### 后端 App 规范

每个 Django app（opsflow，cmdb，itsm，monitor，opsagent 等）内部统一使用以下目录结构：

```
opsflow/
├── models/           # 数据模型
├── views/            # API 视图
├── services/         # 业务逻辑层
├── signals/          # 信号处理（如果存在）
├── tests/            # 测试
├── migrations/
├── serializers.py
├── urls.py
└── apps.py
```

- `dvadmin/` 和 `application/` 保持原名，不改动
- 命名规范：app 名全小写，下划线分隔

### 后端模块分层规范

每个 Django app 内部按 **views → services → models** 三层分层，职责单向依赖：

```
请求 → views（参数校验 + 序列化）→ services（业务逻辑）→ models（数据访问）
                        ↕ (可选，异步)
                     signals（事件通知）
```

| 层 | 职责 | 允许做的事 | 禁止做的事 |
|----|------|-----------|-----------|
| **views** | 参数校验、权限检查、调用 services、序列化输出 | 调 services、调 serializer、校验 request.data | 直接操作 model、写业务逻辑、触发 signal |
| **services** | 业务编排、跨 model 协调、事务管理、触发 signal | 调 models、触发 signal、管理事务 `atomic()` | 直接返回 `Response`、调另一个 services（用 signal 解耦） |
| **models** | 数据访问、属性计算、简单验证 | 定义字段、`property`、`clean()`、`classmethod` 查询 | 调 services、触发 signal、引用 views |
| **signals** | 异步解耦（如缓存更新、WebSocket 推送、日志记录） | 收 signal 后执行副作用 | 返回数据给发送方、修改触发方状态 |

**例外情况：** 对极其简单的 CRUD（一个 model + 一个 viewset），可以跳过 services 层，views 直接调 models。但一旦涉及多数据源、跨表事务、或第三方 API，就必须引入 services。

### 后端 API 命名规范

| # | 规则 | 说明 |
|---|------|------|
| 1 | **RESTful 资源路径** | URL 用**复数名词**表示资源，如 `/api/system/users/`、`/api/opsflow/templates/`。避免 URL 中出现动词（如 `/all_dept/` 应为 `/depts/`） |
| 2 | **HTTP Method 表达操作** | GET=查询、POST=创建、PUT/PATCH=更新、DELETE=删除。不要在 GET 路径中加 `create_` 或 `delete_` |
| 3 | **viewset 优先** | 优先使用 DRF `ModelViewSet`，配合 `router.register()`。只有非 CRUD 操作才使用 `APIView` + 自定义 URL |
| 4 | **查询参数命名** | `snake_case`，如 `?page=1&limit=20&search=foo` |
| 5 | **自定义动作** | 对 `ViewSet` 中的非 CRUD 动作，用 `@action(detail=True, methods=['post'])` 装饰器 |

### ProjectFilteredViewSet 项目过滤规范

`ProjectFilteredViewSet`（`opsflow/views/base.py`）为所有 project-scoped ViewSet 提供统一的 queryset 过滤。

**核心规则：`project_id` 查询参数只在 `list` 和 `create` 两个 action 生效。**

```python
# base.py - get_queryset()
project_id = self.request.query_params.get('project_id') if self.action in ('list', 'create') else None
```

| Action 类型 | project_id 过滤 | 说明 |
|------------|:---:|------|
| `list` | ✅ 生效 | 列表页按项目隔离数据 |
| `create` | ✅ 生效 | 创建时确定资源归属项目 |
| `retrieve` | ❌ 忽略 | 详情页按 PK 查单条，不应被当前项目卡死 |
| `update` / `partial_update` / `destroy` | ❌ 忽略 | 操作已有记录，按 PK 定位 |
| `@action(detail=True)` 自定义动作 | ❌ 忽略 | 如 `submit`、`approve`、`status` 等，操作特定记录 |
| `@action(detail=False)` 自定义动作 | ✅ 生效 | 列表型自定义动作，等同于 `list` |

**设计原因：** 前端 `service.ts` 的 Axios 拦截器会全局自动注入 `project_id` 到所有请求（`localStorage.opsflow_active_project_id`）。如果后端不加区分地对所有 action 都按该参数过滤，会导致 detail 接口查不到其他项目的资源。因此后端只对需要项目上下文的 `list`/`create` 生效，其余 action 忽略。

**注意事项：**
- 新增 `@action(detail=True)` → 自动走不过滤分支，无需额外处理
- 新增 `@action(detail=False)` → 自动走过滤分支，行为与 `list` 一致
- 非超管用户的 `get_user_project_ids()` 过滤（基于用户所有可见项目）始终生效，不受此规则影响
- `ItsmProjectViewSet` 额外包含 `project_id IS NULL` 的兜底查询，用于向后兼容迁移期间的旧数据

---

### 错误处理规范

| 层 | 规范 | 说明 |
|----|------|------|
| **前端 catch** | `warningNotification()` / `ElMessage.error()` | 所有 `try-catch` 必须向用户展示反馈，禁止空 catch 或仅 `console.error()` |
| **前端 API 调用** | `ElMessage.success(msg || '操作成功')` | 成功后统一使用 `successMessage()` / `successNotification()` |
| **后端视图** | 抛异常，不要返回 `ErrorResponse` | 继承 `APIException`，由 DRF exception handler 统一处理。仅在**确实需要返回特定 HTTP status** 时用 `ErrorResponse` |
| **后端服务层** | 抛自定义 Exception | 在 `services/` 层中抛 `Raise(APIException)`，不要在 services 里 return `ErrorResponse` |
| **全局异常** | `application/exception.py` | 所有未捕获异常统一走配置文件中的 `EXCEPTION_HANDLER`，确保返回 `{"code": 5000, "msg": ...}` 格式 |

### 前端规范

- `views/` 下按 app 分目录（`opsflow/`，`system/`，`cmdb/` 等）
- `views/apps/opsflow/components/` 下按功能拆分子目录（`canvas/`，`dialogs/`，`panels/` 等）
- 组件使用 PascalCase 命名（如 `DesignCanvas.vue`）
- 新增 opsflow 独立页面必须在 `views/apps/opsflow-*/` 下创建独立目录

---

## Skills 规范

- 所有 Claude 技能放在项目级 `.claude/skills/` 目录
- 新技能创建后立即放入项目级目录
- 保持用户级 `.claude/skills/` 与项目级同步（或项目级优先）

## 其他规范

- 运行脚本放在 `scripts/`，后端内部脚本放在 `backend/tools/`
- 参考源码放在 `refrence/` 目录，内容通过 `.gitignore` 忽略
- 任何生成运行时目录（`logs/`，`media/`，`static/`）在 `.gitignore` 中声明

---

## 配置治理规范

配置体系采用 conf/ 分层 + components/ 组件化结构，详见 [配置体系重构设计](../../superpowers/specs/2026-06-10-config-architecture-design.md)。

### 配置放置决策树

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

### 组件文件对照表

| 文件 | 职责 | 关联 env 变量 |
|------|------|-------------|
| `application/components/database.py` | DATABASES, Neo4j, CACHES, DB 路由 | DATABASE_*, NEO4J_* |
| `application/components/logging.py` | LOGGING 字典 | 无（路径基于 BASE_DIR） |
| `application/components/rest_framework.py` | DRF, Spectacular, simplejwt | 无 |
| `application/components/auth.py` | 登录、OAuth2/SSO、验证码 | OAUTH_PROVIDERS 密钥 |
| `application/components/channels.py` | CHANNEL_LAYERS, ASGI | 无 |
| `application/components/cors_security.py` | CORS 跨域 | 无 |
| `application/components/celery.py` | Celery 队列、Broker、Backend | 无 |
| `application/components/monitor_adapters.py` | Monitor SPI 适配器注册表 | 无 |
| `application/components/pipeline.py` | Pipeline 引擎行为配置 | 无 |

### 强制规则

1. **新增变量必须在 env_base.py 声明** — 禁止只在一个环境文件中单独定义
2. **组件文件不跨域** — `database.py` 不放 LOGGING，不确定归属时新建文件
3. **新增组件文件要登记** — 同步更新 settings.py 的 import 区和本规范表的对照表

---

## 数据初始化规范

### 统一入口

新环境数据初始化统一通过一条命令完成：

```bash
python manage.py bootstrap
```

支持 `--essential-only`（仅参考数据）和 `--demo-only`（仅演示数据），详细说明见 [Mock 数据生成指南](mock-data-guide.md)。

### 文件职责

所有 seed/mock 数据集中维护在 `backend/common/management/commands/` 下的 **3 个文件**：

| 文件 | 职责 | 包含内容 |
|------|------|----------|
| `bootstrap.py` | 阶段编排入口 | 按 Phase 0→1→2→3 链式调用 |
| `seed_reference.py` | 系统参考数据 | 菜单树、模板分类、CMDB 模型、监控插件、连接器定义、知识库、示例模板、IAM 菜单 |
| `seed_demo.py` | 演示数据 | 示例项目/模板/执行记录、ITSM 演示数据、Neo4j CMDB 拓扑 |

### 强制规则

**新增 model 或生成任何 mock/seed 数据时，必须同步更新对应的 seed 文件。** 不允许在独立的 management command 或临时脚本中写一次性数据生成逻辑。

| 场景 | 应修改的文件 | 禁止的做法 |
|------|-------------|-----------|
| 新增业务 model，需要基础参考数据 | `seed_reference.py` | 新建独立 `seed_xxx.py` |
| 新增开发/演示用的假数据 | `seed_demo.py` | 在 `apps.py` 中写 `ready()` 自动插入 |
| 新增字段/修改已有 seed 数据 | `seed_reference.py` 或 `seed_demo.py` | 直接改数据库后手动 dump |

**例外：** 数据迁移（`migrations.RunPython`）仅用于**表结构变更伴随的数据修复**，不属于 seed 数据。
