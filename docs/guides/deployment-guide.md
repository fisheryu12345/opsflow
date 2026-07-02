# OPSflow 部署指南 — 全新服务器 + 全新数据库

> 适用场景：全新服务器、空 MySQL 数据库、首次部署整套 OPSflow 系统
> 最后更新: 2026-07-03

---

## 目录

1. [环境要求](#1-环境要求)
2. [基础依赖安装](#2-基础依赖安装)
3. [MySQL 初始化](#3-mysql-初始化)
4. [Redis / Neo4j 安装](#4-redis--neo4j-安装)
5. [后端部署](#5-后端部署)
6. [前端部署](#6-前端部署)
7. [数据库迁移与种子数据](#7-数据库迁移与种子数据)
8. [启动服务](#8-启动服务)
9. [验证](#9-验证)
10. [附录：配置参考](#10-附录配置参考)

---

## 1. 环境要求

| 组件 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建运行 |
| MySQL | 8.0+ | 主数据库 |
| Redis | 6+ | 缓存 / Celery Broker / Channel Layer |
| Neo4j | 5.x | CMDB 拓扑存储（可选，CMDB 功能依赖） |
| Git | — | 代码拉取 |

## 2. 基础依赖安装

### 2.1 克隆代码

```bash
git clone https://github.com/fisheryu12345/opsflow.git
cd opsflow
```

### 2.2 Python 虚拟环境

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

安装依赖：

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

> **注意：** `mysqlclient` 依赖 MySQL C 连接器。Linux 需提前安装：
> ```bash
> # Ubuntu/Debian
> sudo apt install python3-dev default-libmysqlclient-dev build-essential
>
> # CentOS/RHEL
> sudo yum install python3-devel mysql-devel gcc
> ```

### 2.3 应用 Django 5.x 兼容补丁

`bamboo-pipeline 4.0.2` 的 Meta 类使用了 Django 5.x 中已移除的 `index_together`。部署后需运行一次补丁脚本修复：

```bash
cd backend
python scripts/patch_bamboo_pipeline.py
```

脚本会自动查找当前虚拟环境中 `pipeline/eri/models.py` 的位置，将 `index_together` 替换为 Django 5.x 兼容的 `indexes`。支持通过 `--path` 指定其他路径，或 `--all` 修补所有虚拟环境副本。

> 该脚本可重复执行 — 已修补的文件会自动跳过。

### 2.4 前端依赖

```bash
cd web
npm install
```

## 3. MySQL 初始化

### 3.1 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS opsflow
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
```

### 3.2 创建数据库用户（可选）

```sql
CREATE USER 'opsflow'@'%' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON opsflow.* TO 'opsflow'@'%';
FLUSH PRIVILEGES;
```

## 4. Redis / Neo4j 安装

### 4.1 Redis

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl enable redis
sudo systemctl start redis

# macOS (Homebrew)
brew install redis
brew services start redis

# Windows — 下载安装包或使用 WSL
```

验证：

```bash
redis-cli ping
# 返回 PONG
```

### 4.2 Neo4j（可选）

Neo4j 仅 CMDB 拓扑功能需要。如果不需要 CMDB 拓扑图，可以跳过。

```bash
# Docker 方式（推荐）
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5
```

## 5. 后端部署

### 5.1 配置环境变量

OPSflow 使用分层配置系统（`conf/` 目录）：

```
backend/conf/
├── env.py            # 入口，加载 base + 按环境加载覆写
├── env_base.py       # 共享默认值（含开发环境可信密码）
├── env_dev.py        # 开发环境覆写
├── env_uat.py        # UAT 环境覆写
├── env_prod.py       # 生产环境覆写（推荐使用此文件）
└── env.example.py    # 配置模板参考
```

**生产部署步骤：**

```bash
cd backend
cp conf/env_prod.py conf/env_prod.py  # 已存在，直接编辑
```

编辑 `conf/env_prod.py`，填写实际值：

```python
"""
env_prod.py — 生产环境覆写
"""
DEBUG = False
ENABLE_LOGIN_ANALYSIS_LOG = False
LOGIN_NO_CAPTCHA_AUTH = False
ALLOWED_HOSTS = ["your-domain.com", "your-server-ip"]

# MySQL
DATABASE_HOST = "your-mysql-host"
DATABASE_PORT = 3306
DATABASE_NAME = "opsflow"
DATABASE_USER = "opsflow"
DATABASE_PASSWORD = "your_strong_password"

# Redis
REDIS_PASSWORD = ""          # 如果 Redis 有密码则填写
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379

# Neo4j（如有）
NEO4J_HOST = "127.0.0.1"
NEO4J_PORT = 7687
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_neo4j_password"

# 调度器 - 生产环境用独立进程
OPSFLOW_SCHEDULER_AUTOSTART = False

# 邮件（如有）
EMAIL_ENABLE = False
# EMAIL_HOST = "smtp.qq.com"
# EMAIL_HOST_USER = "..."
# EMAIL_HOST_PASSWORD = "..."
```

设置环境变量：

```bash
export DJANGO_ENV=prod
```

> **Windows：** `set DJANGO_ENV=prod`

### 5.2 收集静态文件

```bash
python manage.py collectstatic --noinput
```

## 6. 前端部署

### 6.1 构建

```bash
cd web
npm run build
```

构建产物输出到 `web/dist/` 目录。

### 6.2 部署方式

**方式 A：由 Django 托管（推荐）**

`web/dist/` 目录复制到 Django 的静态文件目录，或将白噪声（whitenoise）指向该目录。

编辑 `backend/application/settings.py`（或在环境配置中）：

```python
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, '../web/dist'),
]
```

**方式 B：独立 Nginx 托管**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/opsflow/web/dist;
    index index.html;

    # API 代理到 Django
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # SPA Fallback: 所有非文件请求返回 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 7. 数据库迁移与种子数据

### 7.1 执行数据库迁移

```bash
cd backend
python manage.py migrate
```

此命令会在 MySQL 中创建所有 20+ 个 App 的约 50+ 张表（含 `opsflow_` 前缀）。

### 7.2 导入种子数据

```bash
python manage.py seed_all
```

`seed_all` 按依赖顺序依次执行以下命令：

| 层级 | App | 命令 | 用途 |
|------|-----|------|------|
| L1 | iam | `seed_iam_page_configs` | 权限码、PageTab/PageButton、IAM 角色、角色权限绑定 |
| L1 | iam | `seed_iam_unified` | IAM 用户（superadmin）、默认角色分配 |
| L1 | iam | `seed_deploy_environments` | 部署环境配置 |
| L2 | opsflow | `seed_opsflow` | OpsFlow 菜单、初始化数据 |
| L2 | opsflow | `seed_template_presets` | AI 模板预设提示词 |
| L2 | cmdb | `seed_cmdb` | CMDB 模型定义 |
| L2 | cmdb | `seed_dr_models` | 容灾模型 |
| L2 | monitor | `seed_monitor` | 监控配置 |
| L2 | integration | `seed_integration` | 集成中心连接器定义 |
| L2 | itsm | `seed_itsm` | ITSM 流程模板、技能组等 |

### 7.3 默认凭据

种子数据执行后，默认管理员账号：

| 字段 | 值 |
|------|-----|
| 用户名 | `superadmin` |
| 密码 | `yupei1986` |

## 8. 启动服务

### 8.1 启动 Django（开发模式）

```bash
cd backend
export DJANGO_ENV=prod   # 或 dev
python manage.py runserver 0.0.0.0:8000
```

### 8.2 启动 Django（生产模式 — Gunicorn + Daphne）

生产环境使用 Gunicorn 处理 HTTP，Daphne 处理 WebSocket：

```bash
# HTTP (Gunicorn)
gunicorn application.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log

# WebSocket (Daphne) — 可选，需要 WebSocket 时使用
daphne application.asgi:application \
  --bind 0.0.0.0:8001 \
  --port 8001
```

### 8.3 启动调度器（独立进程）

生产环境需单独启动 APScheduler：

```bash
cd backend
python manage.py start_opsflow_scheduler &
```

> 该命令在 `opsflow/management/commands/` 中定义。

### 8.4 启动 Celery Worker（可选）

```bash
cd backend
celery -A application worker -l info -P gevent
```

### 8.5 启动前端开发服务器（开发模式）

```bash
cd web
npm run dev
```

默认访问 `http://localhost:8080`。

## 9. 验证

### 9.1 后端健康检查

```bash
curl http://localhost:8000/healthz
# 返回: OK

curl http://localhost:8000/readiness
# 返回: OK
```

### 9.2 API 检查

```bash
# 获取 Token
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"yupei1986"}'

# 应返回包含 access 和 refresh token 的 JSON
```

### 9.3 前端检查

浏览器打开 `http://localhost:8080`，使用 `superadmin / yupei1986` 登录。

### 9.4 功能检查清单

- [ ] 登录 → IAM 概览页
- [ ] IAM → 用户管理 → 可见用户列表
- [ ] IAM → 角色管理 → 可见角色列表
- [ ] IAM → 菜单管理 → 可见菜单树 + 详情面板
- [ ] OpsFlow → 模板中心 → 可查看
- [ ] ITSM → 工单 / 流程模板 → 可查看
- [ ] CMDB → 模型 / 实例 → 可查看
- [ ] 系统 → 操作日志 / 配置 → 可查看
- [ ] 右上角语言切换 → 中英文切换正常

## 10. 附录：配置参考

### 10.1 环境变量一览

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DJANGO_ENV` | `dev` | 加载对应 `env_{env}.py` 文件 |
| `DATABASE_ENGINE` | `django.db.backends.mysql` | 数据库引擎 |
| `DATABASE_NAME` | (必填) | 数据库名 |
| `DATABASE_HOST` | (必填) | 数据库主机 |
| `DATABASE_PORT` | 3306 | 数据库端口 |
| `DATABASE_USER` | (必填) | 数据库用户 |
| `DATABASE_PASSWORD` | (必填) | 数据库密码 |
| `REDIS_HOST` | `127.0.0.1` | Redis 主机 |
| `REDIS_PORT` | 6379 | Redis 端口 |
| `REDIS_PASSWORD` | 空 | Redis 密码 |
| `DEBUG` | `True`（dev） | Django DEBUG 模式 |
| `ALLOWED_HOSTS` | `["*"]` | 允许的主机名 |
| `OPSFLOW_SCHEDULER_AUTOSTART` | `True` | Django 启动时自动运行调度器 |
| `NEO4J_HOST` | `127.0.0.1` | Neo4j 主机 |
| `NEO4J_PORT` | 7687 | Neo4j Bolt 端口 |

### 10.2 表前缀

所有数据库表使用 `opsflow_` 前缀，在 `env_base.py` 中定义：

```python
TABLE_PREFIX = "opsflow_"
```

例如 `opsflow_iam_menu`, `opsflow_flow_execution` 等。

### 10.3 应用列表

包含以下 Django App，各有独立的迁移和模型：

- `common` — 公共工具、序列化器、基础模型（CoreModel, OperationLog, LoginLog, SystemConfig）
- `iam` — 身份与权限管理（用户、角色、菜单、权限码、PageTab）
- `opsflow` — 流程引擎（模板、执行、审批、知识库、调度器）
- `itsm` — IT 服务管理（工单、事件、变更、SLA、技能组）
- `cmdb` — 配置管理数据库（模型定义、实例管理、云同步）
- `integration` — 集成中心（连接器定义、云同步）
- `monitor` — 监控配置
- `job_platform` — 作业平台
- `portal` — 门户
- `open_api` — 开放接口
- `opsagent` — OpsAgent 管理
- `agent_backend` — Agent 后端服务
- `mock_service` — Mock 服务

### 10.4 生产部署架构图

```
┌─────────────┐     ┌──────────────────────────────────────┐
│   Nginx     │────▶│  Gunicorn (HTTP, :8000)              │
│  (80/443)   │     │  Daphne (WebSocket, :8001)          │
│             │     │  Start OpsFlow Scheduler (apsched)  │
│ 静态文件:   │     │  Celery Worker (异步任务)            │
│ web/dist/   │     └──────┬───────────────┬───────────────┘
└─────────────┘            │               │
                           ▼               ▼
                    ┌──────────┐    ┌──────────┐
                    │  MySQL   │    │  Redis   │
                    │  8.0+    │    │  6+      │
                    └──────────┘    └──────────┘
                                    (cache/broker)
                           ┌──────────┐
                           │  Neo4j   │
                           │  5.x     │
                           └──────────┘
                           (CMDB 拓扑, 可选)
```

### 10.5 关键目录结构

```
opsflow/
├── backend/
│   ├── conf/           # 分层配置系统
│   ├── application/    # Django 项目配置（settings, urls, wsgi, asgi）
│   ├── common/         # 公共工具与基础模型
│   ├── iam/            # 身份与权限
│   ├── opsflow/        # 流程引擎
│   ├── itsm/           # IT 服务管理
│   ├── cmdb/           # 配置管理
│   ├── integration/    # 集成中心
│   ├── monitor/        # 监控
│   ├── job_platform/   # 作业平台
│   ├── portal/         # 门户
│   ├── open_api/       # 开放接口
│   ├── opsagent/       # OpsAgent
│   ├── agent_backend/  # Agent 后端
│   └── manage.py       # Django 管理入口
├── web/
│   ├── src/            # Vue 3 源码
│   ├── vite.config.ts  # Vite 配置（API 代理）
│   └── package.json    # 前端依赖
├── docs/               # 文档
└── .githooks/          # Git 钩子
```
