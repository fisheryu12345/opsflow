# AGENTS.md — 项目开发指南

> 本文件面向 AI 编程助手。如果你正在阅读本文件，说明你对本项目一无所知。以下内容基于项目实际代码和配置整理，所有信息均来自现有仓库，不做假设或泛化。

---

## 项目概述

本项目是一套基于 **django-vue3-admin（dvadmin）** 开源框架深度定制的中后台管理系统，业务核心为**量化期货交易系统**。项目采用经典的前后端分离架构：

- **前端**：Vue 3 + Composition API + TypeScript + Vite + Element Plus
- **后端**：Django 4.2 + Django REST Framework + Django Channels + Celery + APScheduler
- **数据库**：MySQL 8.0（主库）+ Redis（缓存 / 消息队列 / Celery Broker）
- **量化交易接入**：天勤 SDK（TqSdk 3.9.1）

项目中文名为 FT（Fisher Trade），生产域名指向 `fishertrade.com.cn`。

---

## 技术栈详情

### 前端（`web/`）

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | ^3.2.45 | Composition API + `<script setup>` |
| TypeScript | ^4.9.4 | 严格模式 |
| Vite | ^4.0.0 | 构建工具 |
| Element Plus | ^2.3.9 | UI 组件库 |
| Pinia | ^2.0.28 | 状态管理，搭配 `pinia-plugin-persist` |
| Vue Router | ^4.1.6 | 前端路由，使用 `createWebHashHistory` |
| Tailwind CSS | ^3.2.7 | 原子化 CSS |
| Fast CRUD | ^1.19.2 | 中后台表格/表单快速生成框架 |
| Axios | ^1.2.1 | HTTP 请求库 |
| ECharts | ^5.4.1 | 图表库 |
| VXE Table | ^4.4.1 | 高性能表格 |
| mitt | ^3.0.0 | 事件总线 |

### 后端（`backend/`）

| 技术 | 版本 | 说明 |
|------|------|------|
| Django | 4.2.7 | Web 框架 |
| djangorestframework | 3.14.0 | REST API 框架 |
| djangorestframework-simplejwt | 5.3.0 | JWT 认证 |
| Django Channels | 3.0.5 | WebSocket 支持 |
| Celery | 5.6.3 | 异步任务队列 |
| APScheduler | 3.11.2 | 定时任务调度 |
| django-apscheduler | 0.7.0 | Django 集成 APScheduler |
| TqSdk | 3.9.1 | 天勤量化期货 SDK |
| pandas | 3.0.2 | 数据处理 |
| numpy | 2.4.4 | 数值计算 |
| scipy | 1.17.1 | 科学计算 |
| langchain | 1.2.15 | LLM 应用框架 |
| langgraph | 1.1.6 | LangChain 工作流 |
| influxdb-client | 1.50.0 | 时序数据库客户端 |
| redis | 7.4.0 | Redis 客户端 |
| mysqlclient | 2.2.8 | MySQL 驱动 |
| uvicorn | 0.23.2 | ASGI 服务器 |
| gunicorn | 21.2.0 | WSGI/ASGI 生产服务器 |

---

## 目录结构

```
.
├── backend/                 # Django 后端
│   ├── application/         # Django 项目配置（settings/urls/asgi/wsgi/celery）
│   ├── conf/                # 环境配置（env.py、env.example.py）
│   ├── dvadmin/             # 核心系统模块（用户、角色、菜单、部门、字典、日志等）
│   ├── stock/               # 量化交易业务模块
│   ├── plugins/             # 插件扩展点（目前为空）
│   ├── media/               # 用户上传文件
│   ├── static/              # 静态文件（已包含 simpleui-x、DRF、Swagger UI）
│   ├── logs/                # 运行时日志
│   ├── manage.py            # Django 管理入口
│   ├── requirements.txt     # Python 依赖
│   ├── requirements_prod.txt# 生产依赖（与 requirements.txt 基本一致）
│   ├── gunicorn_conf.py     # Gunicorn + UvicornWorker 配置
│   └── docker_start.sh      # 生产启动脚本（uvicorn 4  worker）
├── web/                     # Vue3 前端
│   ├── src/
│   │   ├── api/             # API 接口封装
│   │   ├── assets/          # 静态资源
│   │   ├── components/      # 公共组件
│   │   ├── directive/       # 自定义指令
│   │   ├── i18n/            # 国际化（zh-cn / en / zh-tw）
│   │   ├── layout/          # 布局系统（classic / columns / defaults / transverse）
│   │   ├── plugin/          # 权限插件
│   │   ├── router/          # 路由配置
│   │   ├── stores/          # Pinia Store
│   │   ├── theme/           # 全局样式（SCSS）
│   │   ├── types/           # TypeScript 类型声明
│   │   ├── utils/           # 工具函数（request、storage、websocket 等）
│   │   └── views/           # 页面视图
│   │       ├── system/      # 系统管理页面
│   │       ├── apps/        # 业务页面（合约、策略、持仓、交易日志等）
│   │       └── signal/      # 信号相关页面
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── .eslintrc.js
│   ├── .prettierrc.js
│   ├── .env / .env.development / .env.production
│   └── dist/                # 生产构建产物（已提交到仓库）
├── .venv/                   # Python 虚拟环境
├── .vscode/                 # VS Code 工作区配置
├── README.md                # 根目录 README（仅标题 FT）
└── document.md              # 本地备忘（PowerShell 策略、npm/pip 国内镜像）
```

---

## 构建与启动命令

### 前端（`web/`）

```bash
# 安装依赖
npm install

# 开发环境启动（默认端口 8080）
npm run dev

# 生产构建（输出到 web/dist/）
npm run build

# 自动修复 ESLint 错误
npm run lint-fix
```

前端开发代理配置在 `.env.development` 中，`VITE_API_URL` 指向 `http://127.0.0.1:8000`。生产环境指向 `https://fishertrade.com.cn`。

### 后端（`backend/`）

```bash
# 1. 配置环境
cp conf/env.example.py conf/env.py
# 编辑 conf/env.py，配置数据库连接信息

# 2. 安装依赖
pip install -r requirements.txt

# 3. 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 4. 初始化基础数据
python manage.py init
python manage.py init_area

# 5. 开发启动
python manage.py runserver 0.0.0.0:8000

# 或使用 ASGI 服务器（支持 WebSocket）
daphne -b 0.0.0.0 -p 8000 application.asgi:application
```

### 生产部署

```bash
# 方案一：Gunicorn + UvicornWorker（ASGI）
gunicorn -c gunicorn_conf.py application.asgi:application

# 方案二：直接 Uvicorn（docker_start.sh 中使用）
uvicorn application.asgi:application --port 8000 --host 0.0.0.0 --workers 4
```

---

## 代码组织与模块划分

### 后端核心模块

#### 1. `application/` — Django 项目核心
- `settings.py`：集中所有配置（数据库、Redis、Celery、Channels、DRF、JWT、CORS、日志、静态文件等）
- `urls.py`：根路由，挂载 Swagger/ReDoc 文档、认证接口、系统 API、业务 API
- `asgi.py`：ASGI 入口，集成 Channels `ProtocolTypeRouter`（HTTP + WebSocket）
- `wsgi.py`：WSGI 入口
- `celery.py`：Celery 应用配置 + 自定义重试装饰器
- `dispatch.py`：运行时从数据库加载字典和系统配置到 `settings`
- `routing.py`：WebSocket 路由（`ws/<str:service_uid>/`）
- `websocketConfig.py`：WebSocket Consumer（`DvadminWebSocket`、`MegCenter`），支持 JWT 鉴权、消息推送

#### 2. `dvadmin/` — 基础系统管理模块
- `system/models.py`：核心模型，包括用户、角色、部门、岗位、菜单、字典、系统配置、操作日志、登录日志、消息中心、文件列表、地区、接口白名单，以及字段权限和角色菜单权限模型
- `system/views/`：所有系统实体的 DRF ViewSet
- `system/fixtures/`：JSON 数据 fixtures 和初始化脚本
- `system/management/commands/`：自定义管理命令（`init`、`init_area`、`generate_init_json`）
- `utils/`：高度封装的通用工具层
  - `models.py`：`CoreModel`（审计字段）、`SoftDeleteModel`（软删除）
  - `viewset.py`：`CustomModelViewSet`（统一响应、批量创建、导入导出、字段权限、批量删除）
  - `pagination.py`：自定义分页
  - `filters.py`：自定义过滤后端、数据权限过滤
  - `exception.py`：自定义异常处理器
  - `json_response.py`：`SuccessResponse`、`DetailResponse`、`ErrorResponse`
  - `middleware.py`：API 日志中间件、健康检查中间件
  - `backends.py`：自定义认证后端

#### 3. `stock/` — 量化交易业务模块（核心定制部分）
- `models.py`：交易相关模型（交易账户、合约列表、策略配置、日策略信号、每日权益快照、滚动绩效指标、账户绩效汇总、持仓状态、已平仓记录、错误日志、交易日志）
- `views/`：各模型对应的 DRF ViewSet
- `serializers/`：序列化器
- `scheduler/`：APScheduler 定时任务定义
  - `tasks_daily_open.py`：开盘任务
  - `tasks_daily_close.py`：收盘任务
  - `calculate_atr.py`：ATR 计算
  - `calculate_unit_lots.py`：手数计算
  - `performance_cal.py`：绩效计算
  - `send_report.py`：报告发送
  - `check_min_position_requirement.py`：最小持仓检查
- `tasks/`：Celery 异步任务（邮件发送等）
- `utils/`：业务工具（指标计算、日志、合约同步等）
- `deepseek/`：DeepSeek SDK 集成
- `management/commands/sync_contracts.py`：合约同步命令
- `apps.py`：AppConfig，包含 `ready()` 钩子——**仅在服务器 IP 为 `172.25.21.216` 时启动调度器**，并使用 Redis 分布式锁防止多实例冲突

#### 4. `plugins/` — 插件扩展点
- 目前仅包含空 `__init__.py`
- `settings.py` 支持动态注入子目录到 `sys.path`，并读取 `PLUGINS_URL_PATTERNS`

---

## 前端代码组织

### 路径别名

| 别名 | 指向 |
|------|------|
| `/@/` | `src/` |
| `@views` | `src/views` |

### 核心目录

- `src/api/`：按模块组织的 API 接口层
- `src/utils/request.ts`：Axios 统一实例，拦截器处理 JWT Token 和 dvadmin 自定义响应码（`2000` 成功，`401`/`4001` 登出）
- `src/stores/`：Pinia Store，包括主题配置、路由列表、用户信息、标签页、字典、按钮权限、字段权限、消息中心等
- `src/router/`：路由系统，支持后端控制路由（`isRequestRoutes`）和前端控制路由两种模式，使用 `createWebHashHistory`
- `src/layout/`：多套布局模式（classic / columns / defaults / transverse），含侧边栏、顶部导航、标签页、面包屑、锁屏等
- `src/views/system/`：系统管理页面（用户、角色、菜单、部门、字典、配置、日志等）
- `src/views/apps/`：业务页面（合约管理、策略配置、持仓、交易日志）

### 页面开发模式（Fast CRUD）

大量中后台页面遵循 **三件套模式**：

```
src/views/xxx/
├── api.ts      # 该模块的 API 调用
├── crud.tsx    # Fast CRUD 配置（列定义、表单、搜索规则）
└── index.vue   # 页面壳组件，挂载 CRUD
```

示例：`src/views/system/user/api.ts`、`crud.tsx`、`index.vue`

---

## 数据库与中间件配置

### MySQL（主数据库）

- **库名**：`stock`
- **用户**：`trade`
- **字符集**：`utf8mb4`
- **表前缀**：`dvadmin_`
- **连接池**：`CONN_MAX_AGE: 300`，`CONN_HEALTH_CHECKS: True`
- **SSL**：`ssl-mode: DISABLED`
- **主机选择逻辑**：根据服务器本地 IP 判断
  - 若本地 IP 为 `172.25.21.216` → 连接 `127.0.0.1`
  - 否则 → 连接 `139.196.194.73`

### Redis

- **Cache**：`redis://:redis123456@127.0.0.1:6379/1`
- **Celery Broker**：`redis://:redis123456@127.0.0.1:6379/0`
- **Celery Result Backend**：`redis://:redis123456@127.0.0.1:6379/1`

### 认证与权限

- **JWT**：`djangorestframework-simplejwt`，自定义 Header 类型为 `JWT`
- **Token 有效期**：Access Token 24 小时，Refresh Token 1 天
- **权限模型**：RBAC，支持菜单权限、按钮权限、接口权限、字段权限、数据权限（按部门范围）
- **语言/时区**：`zh-hans` / `Asia/Shanghai`

---

## 开发约定与代码风格

### 后端

1. **模型基类**：所有业务模型应继承 `dvadmin.utils.models.CoreModel`（自动包含 `creator`、`modifier`、`create_datetime`、`update_datetime`、`dept_belong_id`、`description`），需要软删除的继承 `SoftDeleteModel`（通过 `is_deleted` 字段实现）。
2. **视图基类**：所有 DRF 视图应继承 `dvadmin.utils.viewset.CustomModelViewSet`，以统一响应格式、分页、导入导出和权限控制。
3. **响应格式**：后端 API 统一返回 `SuccessResponse` / `DetailResponse` / `ErrorResponse`，前端根据 `code` 字段判断（`2000` 为成功）。
4. **审计字段**：`create_datetime` 和 `update_datetime` 由基类自动维护，不要手动覆盖。
5. **IP 敏感行为**：调度器启动（`stock/apps.py`）和数据库主机选择（`conf/env.py`）均通过判断本地 IP 是否为 `172.25.21.216` 来区分开发和生产环境。修改这些逻辑时需格外谨慎。
6. **环境配置**：数据库密码、Redis 密码等敏感信息目前硬编码在 `conf/env.py` 中。新增环境变量时，应同步更新 `conf/env.example.py`。

### 前端

1. **组件写法**：统一使用 `<script setup lang="ts">`，组件名通过 `vite-plugin-vue-setup-extend` 直接在 script 标签上声明（如 `<script setup lang="ts" name="app">`）。
2. **Prettier 配置**：`printWidth: 150`，`tabWidth: 2`，`useTabs: true`，`semi: true`，`singleQuote: true`，`trailingComma: 'es5'`。
3. **API 请求**：统一从 `src/utils/request.ts` 引入，不要在页面中直接创建 axios 实例。
4. **权限指令**：使用自定义指令 `v-auth` 控制按钮级权限。
5. **存储封装**：使用 `src/utils/storage.ts` 中的 `Local` / `Session` 替代原生 `localStorage` / `sessionStorage`。
6. **事件总线**：使用 `mittBus`（挂载在全局属性上）进行跨组件通信。

---

## 测试策略

> **现状：本项目目前没有配置任何自动化测试框架。**

- 后端：`dvadmin/system/tests.py` 为空（仅导入 `TestCase`）。
- 后端：`stock/views/test.py` 不是单元测试，而是 TqSDK 集成调试脚本（含硬编码账号密码）。
- 前端：`src/` 下没有任何 `*.spec.*` 或 `*.test.*` 文件。
- 没有 `pytest.ini`、没有 Jest/Vitest/Cypress/Playwright 配置，没有 CI/CD 流水线。

**如果你需要添加测试：**
- 后端推荐引入 `pytest-django`，在 `backend/` 下创建 `pytest.ini`。
- 前端推荐引入 `vitest`（与 Vite 同生态）。
- **请勿修改** `stock/views/test.py`，它不是测试文件；如需正式测试，请在 `stock/tests/` 下新建。

---

## 部署说明

### 部署方式

1. **手动部署**：前端 `npm run build` 生成 `web/dist/`，配合 Nginx 托管静态资源；后端使用 `gunicorn_conf.py` 或 `docker_start.sh` 启动 ASGI 服务。
2. **Docker Compose**：`web/README.md` 中提及了 `docker-compose up -d` 的用法，但**仓库中并未提交 `docker-compose.yml` 或 `Dockerfile`**。
3. **预构建产物**：`web/dist/` 目录已提交到仓库，包含预编译的生产环境前端文件。

### Nginx 反向代理（推荐）

参考 `web/README.md` 中的描述，典型配置为：
- 前端静态文件由 Nginx 直接服务
- `/api` 路径代理到后端 ASGI 服务（`8000` 端口）

### 生产启动脚本

`backend/docker_start.sh`：
```bash
uvicorn application.asgi:application --port 8000 --host 0.0.0.0 --workers 4
```

`backend/gunicorn_conf.py`：
- 绑定 `0.0.0.0:8000`
- Workers: `1`（注释中保留了自动计算逻辑）
- Threads: `3`
- Worker Class: `uvicorn.workers.UvicornWorker`
- Max requests: `10000`
- Timeout: `120s` / Graceful `300s`

---

## 安全注意事项

1. **硬编码凭证**：`conf/env.py` 中包含数据库密码（`312711936!@#GHS`）、Redis 密码（`redis123456`）、TqSDK 账号（`yupei1986`）等生产级敏感信息。**绝对不要将这些凭据提交到公共仓库**；当前仓库为私有，但仍建议尽快迁移到环境变量注入。
2. **IP 白名单**：`stock/apps.py` 中的调度器启动和 `conf/env.py` 中的数据库主机选择，均依赖本地 IP 是否为 `172.25.21.216`。在多节点或云服务器部署时，需确认该逻辑是否仍然适用。
3. **CORS**：后端已配置 `django-cors-headers`，开发环境下允许跨域。生产环境请收紧 `CORS_ALLOWED_ORIGINS`。
4. **JWT Secret**：Django 的 `SECRET_KEY` 存储在 `settings.py` 中，生产环境应通过环境变量注入。
5. **DEBUG 模式**：`settings.py` 中的 `DEBUG` 值由 `conf/env.py` 控制，部署到生产前务必确认已关闭。
6. **WebSocket 鉴权**：`websocketConfig.py` 中实现了基于 JWT 的 WebSocket 鉴权，Token 从 query string 中读取。注意避免 Token 泄露到日志中。
7. **Baidu 统计**：`web/index.html` 中嵌入了百度统计脚本，若部署到非中国区或需合规场景，请评估是否移除。

---

## 常用管理命令

```bash
# 后端
python manage.py init              # 初始化系统基础数据
python manage.py init_area         # 初始化省市区数据
python manage.py generate_init_json # 生成初始化 JSON
python manage.py sync_contracts    # 同步期货合约列表（stock 模块）

# 前端
npm run dev                        # 启动开发服务器
npm run build                      # 生产构建
npm run lint-fix                   # ESLint 自动修复
```

---

## 开发者备忘

- **项目语言**：中文优先。后端 `LANGUAGE_CODE = "zh-hans"`，前端默认语言为 `zh-cn`，注释和文档以中文为主。
- **虚拟环境**：仓库根目录已包含 `.venv/`，Windows 下激活方式为 `& .venv\Scripts\Activate.ps1`。
- **国内镜像**：`document.md` 中记录了 npm 和 pip 的国内镜像配置（淘宝 / 清华源）。
- **调度器行为**：`stock` 模块的 APScheduler 定时任务仅在特定 IP 服务器上启动，本地开发时不会自动运行。如需本地调试调度任务，需手动修改 `stock/apps.py` 中的 IP 判断逻辑。
- **WebSocket 路径**：`ws://host/ws/<service_uid>/`，用于系统消息推送和实时通知。
