# OPSflow 配置体系重构设计

> **日期:** 2026-06-10
> **状态:** 设计已批准
> **顶层约束:** 参见 [docs/opsflow_target.md](../../opsflow_target.md)

---

## 1. 问题陈述

### 1.1 当前痛点

| # | 问题 | 表现 |
|---|------|------|
| 1 | **单环境配置** | `conf/env.py` 仅一套值，无法按 dev/uat/prod 切换 |
| 2 | **密钥明文入库** | DB 密码、DeepSeek API Key 等敏感信息已提交到 git 历史 |
| 3 | **settings.py 过重** | 593 行混了~15 个不同领域的配置区块 |
| 4 | **配置发现困难** | 新增配置不知放哪里 — env.py? settings.py? 哪个区块? |
| 5 | **子 App 注册散乱** | 每新增一个 App 需要手动改 settings.py 的 INSTALLED_APPS |

### 1.2 设计目标

- **环境隔离** — 按 dev/uat/prod 三套组配置，通过环境变量切换
- **领域拆分** — settings.py 按 Django 配置领域拆为独立组件
- **零侵入** — 现有 `from conf.env import *` 入口不动，对外无感
- **可追溯** — 配置入 git，变更可审查

---

## 2. 架构设计

### 2.1 文件格局

```
backend/
├── conf/                            ← 运行时值（环境分层）
│   ├── env.py                       #   入口：动态加载 base + 环境覆写
│   ├── env_base.py                  #   共享变量定义（所有环境相同的键+默认值）
│   ├── env_dev.py                   #   dev 差异覆写（约 15 行）
│   ├── env_uat.py                   #   uat 差异覆写（约 10 行）
│   ├── env_prod.py                  #   prod 差异覆写（约 15 行）
│   └── env.example.py               #   模板（入 git，值留空作为参考）
│
├── application/
│   ├── settings.py                  #   ~80 行，仅做 import 聚合
│   ├── components/                  #   ← 按领域拆分的配置组件
│   │   ├── __init__.py
│   │   ├── database.py              #   DATABASES + Neo4j + DB 路由
│   │   ├── logging.py               #   LOGGING（最大块）
│   │   ├── rest_framework.py        #   DRF + Spectacular + simplejwt
│   │   ├── channels.py              #   CHANNEL_LAYERS + ASGI
│   │   ├── auth.py                  #   登录方式 + JWT + OAuth2/SSO + 验证码
│   │   ├── cors_security.py         #   CORS + 安全中间件
│   │   └── monitor_adapters.py      #   Monitor 适配器注册表
│   └── ...
```

### 2.2 分层关系

```
DJANGO_ENV=prod  (环境变量)
       │
       ▼
conf/env.py ───→ from conf.env_base import *  (加载所有变量定义)
       │
       └──────→ exec(conf/env_prod.py)        (覆写环境差异值)
       │
       ▼ (变量全部就绪)
application/
├── settings.py       ───→ import * from conf.env
├── components/       ───→ import * from conf.env
│   ├── database.py       组装 DATABASES
│   ├── logging.py        组装 LOGGING
│   ...
```

### 2.3 env.py 入口逻辑

```python
# conf/env.py — 唯一入口
import os
from conf.env_base import *

DJANGO_ENV = os.environ.get('DJANGO_ENV', 'dev')
env_file = f'conf/env_{DJANGO_ENV}.py'
exec(compile(open(env_file).read(), env_file, 'exec'))
```

**关键行为：**
- 默认 `DJANGO_ENV=dev`，无需额外配置
- `env_base.py` 定义所有变量+合理默认值（如 `NEO4J_HOST = "localhost"`）
- 环境文件只写与本环境不同的值，保持短小
- 所有引用方（settings.py, components/*.py）都 `from conf.env import *`，结构不变

### 2.4 base vs 环境文件划分

| 变量 | env_base.py | env_dev.py | env_prod.py |
|------|:-----------:|:----------:|:-----------:|
| `DATABASE_HOST` | 默认值 `127.0.0.1` | ✅ 覆写 | ✅ 覆写 |
| `DATABASE_USER/PASSWORD` | 默认值 | ✅ | ✅ |
| `REDIS_HOST` | `127.0.0.1` | — | ✅ |
| `NEO4J_HOST/PORT/USER/PASSWORD` | 默认值 | ✅ | ✅ |
| `OPSAGENT_API_KEY/BASE_URL/MODEL` | 占位值 | ✅ | ✅ |
| `ANSIBLE_API_URL/TOKEN` | 默认值 | — | ✅ |
| `DEBUG` | `True` | — | `False` |
| `ALLOWED_HOSTS` | `["*"]` | — | `["opsflow.company.com"]` |
| `LOGIN_NO_CAPTCHA_AUTH` | `True` | — | `False` |
| `OPSFLOW_SCHEDULER_AUTOSTART` | `True` | — | `False` |
| `EMAIL_*` | 占位 | — | ✅ |
| `OAUTH_PROVIDERS` 密钥 | 占位 | — | ✅ |

原则：**base 放所有键+合理默认值，环境文件只覆写 value 不同者。**

---

## 3. settings.py 拆分方案

### 3.1 拆分对照表

| 源 settings.py 行号 | 内容 | 目标文件 |
|-------------------|------|---------|
| L29-L52 | `SECRET_KEY`, `PLUGINS_PATH`, `DEBUG`, `ALLOWED_HOSTS`, `COLUMN_EXCLUDE_APPS` | **保留** |
| L54-L92 | `INSTALLED_APPS` | **保留** |
| L94-L107 | `MIDDLEWARE` | **保留** |
| L109-L125 | `ROOT_URLCONF`, `TEMPLATES`, `WSGI_APPLICATION` | **保留** |
| L131-L173 | `DATABASES` + test mode SQLite 覆写 | `components/database.py` |
| L175-L184 | `NEO4J_*` 变量 + `DATABASE_ROUTERS` | `components/database.py` |
| L186-L205 | `AUTH_USER_MODEL`, `AUTH_PASSWORD_VALIDATORS` | `components/auth.py` |
| L207-L225 | `LANGUAGE_CODE`, `TIME_ZONE`, `USE_I18N/TZ` | **保留**（Django 骨架） |
| L227-L246 | `STATIC_URL/MEDIA/STATICFILES` | **保留** |
| L248-L255 | `CORS_ORIGIN_ALLOW_ALL`, `CORS_ALLOW_CREDENTIALS` | `components/cors_security.py` |
| L257-L272 | `ASGI_APPLICATION`, `CHANNEL_LAYERS` | `components/channels.py` |
| L275-L363 | `LOGGING`（含 log 路径/SERVER_LOGS_FILE 等） | `components/logging.py` |
| L365-L392 | `REST_FRAMEWORK` | `components/rest_framework.py` |
| L393-L409 | `AUTHENTICATION_BACKENDS`, `SIMPLE_JWT` | `components/auth.py` |
| L411-L426 | `SPECTACULAR_SETTINGS` | `components/rest_framework.py` |
| L428-L443 | `CAPTCHA_*` | `components/auth.py` |
| L445-L477 | 其他杂项（`DEFAULT_AUTO_FIELD`, `API_LOG*`, `CELERY*`, `CACHES` 等） | **保留** |
| L497-L507 | `CACHES` (Redis) | `components/database.py` |
| L509-L522 | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_QUEUES` | **保留** |
| L524-L530 | Pipeline 引擎配置 | **保留** |
| L536-L567 | `OAUTH_PROVIDERS` | `components/auth.py` |
| L569-L593 | `MONITOR_ADAPTERS` | `components/monitor_adapters.py` |

### 3.2 改造后的 settings.py 骨架

```python
import os
import sys
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

from conf.env import *   # ← 环境变量入口（不变）

# ── 骨架（不拆分） ──
SECRET_KEY = "..."
PLUGINS_PATH = os.path.join(BASE_DIR, "plugins")
sys.path.insert(0, os.path.join(PLUGINS_PATH))
DEBUG = locals().get("DEBUG", True)
ALLOWED_HOSTS = ['*']
COLUMN_EXCLUDE_APPS = ['channels', 'captcha'] + locals().get("COLUMN_EXCLUDE_APPS", [])

INSTALLED_APPS = [...]     # 同前
MIDDLEWARE = [...]          # 同前
ROOT_URLCONF = "application.urls"
TEMPLATES = [...]           # 同前
WSGI_APPLICATION = "application.wsgi.application"

AUTH_USER_MODEL = "system.Users"
USERNAME_FIELD = "username"

# ── 国际化骨架 ──
LANGUAGE_CODE = "zh-hans"
LANGUAGES = [...]
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ── 静态文件 ──
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
MEDIA_ROOT = "media"
MEDIA_URL = "/media/"

# ── 组件配置（拆分出去） ──
from application.components.database import *
from application.components.channels import *
from application.components.logging import *
from application.components.rest_framework import *
from application.components.auth import *
from application.components.cors_security import *
from application.components.monitor_adapters import *

# ── 杂项配置（保留） ──
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
API_LOG_ENABLE = True
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TASK_QUEUES = [...]
# Pipeline 引擎配置
ENABLE_PIPELINE_EVENT_SIGNALS = True
PIPELINE_ENABLE_ROLLBACK = True
...
```

---

## 4. 迁移策略

### Phase 1: conf 分层（不碰 settings.py）

| 步骤 | 操作 |
|------|------|
| 1.1 | 从当前 `conf/env.py` 提取所有变量到 `conf/env_base.py`，加中文注释 |
| 1.2 | 当前值原样写入 `conf/env_dev.py` |
| 1.3 | 创建 `conf/env_uat.py` 占位（值待定） |
| 1.4 | 创建 `conf/env_prod.py` 占位（值待定） |
| 1.5 | 重写 `conf/env.py` 为动态加载逻辑 |
| 1.6 | 更新 `conf/env.example.py` 为纯模板 |

验证: `python manage.py check --deploy` + `python manage.py runserver` 正常启动

### Phase 2: 拆分 settings.py

| 步骤 | 操作 |
|------|------|
| 2.1 | 创建 `application/components/` 目录 |
| 2.2-2.8 | 逐个创建各 component 文件，每创建一个运行 `python manage.py check` 验证 |
| 2.9 | 替换 settings.py 为 import 聚合版本 |

### Phase 3: 清理

| 步骤 | 操作 |
|------|------|
| 3.1 | `conf/__init__.py` 确保包结构干净 |
| 3.2 | 验证所有 apps.py 中 `from django.conf import settings` 仍正常工作 |
| 3.3 | 全量测试 `python manage.py test` |

---

## 5. 验证标准

| 检查项 | 方法 | 预期 |
|--------|------|------|
| Django 检查 | `python manage.py check --deploy` | 零错误 |
| 开发启动 | `python manage.py runserver` | 正常启动，dev 配置生效 |
| UAT 切换 | `DJANGO_ENV=uat python manage.py check` | 对应配置生效 |
| Prod 切换 | `DJANGO_ENV=prod python manage.py check` | 对应配置生效 |
| 组件隔离 | 删除 `components/database.py` 再 check | 应报错（证明被引用） |
| 全量测试 | `python manage.py test` | 零回归 |
| 密钥审计 | 检查 `env_dev.py` 中密钥值 | 与旧 env.py 一致 |
