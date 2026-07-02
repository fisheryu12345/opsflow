# 分层配置系统设计 — conf/env 架构

> 提交: 76e42387 | 日期: 2026-07-01
> 涉及 App: opsflow
> 类型: 配置变更

---

## 变更内容

将 Redis 连接的 5 处硬编码 `127.0.0.1:6379` 统一替换为 `conf/env.py` 配置变量：

| 文件 | 修改前 | 修改后 |
|------|--------|--------|
| `application/components/database.py:51` | `f"redis://127.0.0.1:6379/1"` | `f"{REDIS_URL}/1"` |
| `application/components/channels.py:16` | `('127.0.0.1', 6379)` | `(REDIS_HOST, REDIS_PORT)` |
| `application/components/celery.py:9-10` | 两处硬编码 URL | `f'{REDIS_URL}/0'` + `f'{REDIS_URL}/1'` |
| `opsflow/core/node_timeout_strategy.py:153` | `host="127.0.0.1", port=6379` | `from conf.env import REDIS_HOST, REDIS_PORT` |
| `opsflow/signals/timeout.py:28` | 同上 | 同上 |

## 配置分层设计

```
conf/
├── env.py          ← 入口：加载 base → 按 DJANGO_ENV 覆写
├── env_base.py     ← 共享默认值（所有环境相同）
├── env_dev.py      ← 本地开发覆盖（可选）
├── env_uat.py      ← UAT 环境覆盖
├── env_prod.py     ← 生产环境覆盖
└── env.example.py  ← 配置示例模板
```

### 加载顺序

```python
# conf/env.py
from conf.env_base import *          # 1) 加载共享默认值
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'dev')
exec(compile(open(f'conf/env_{DJANGO_ENV}.py'), ...))  # 2) 按环境覆写
```

**优先级**：`env_prod.py > env_base.py`（同名变量后者覆盖前者）

### 环境控制

通过 `DJANGO_ENV` 环境变量控制：

```bash
# 本地开发（默认，不设环境变量即为 dev）
python manage.py runserver

# UAT 环境
DJANGO_ENV=uat python manage.py runserver

# 生产环境
DJANGO_ENV=prod python manage.py runserver
```

### 当前 env_base.py 定义的 Redis 变量

```python
REDIS_PASSWORD = ""
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_URL = f"redis://:{REDIS_PASSWORD or ''}@{REDIS_HOST}:{REDIS_PORT}"
```

### 环境中使用方式

各组件 `from conf.env import *` 后直接引用变量：

```python
# 引用 REDIS_URL（含密码）
CELERY_BROKER_URL = f'{REDIS_URL}/0'

# 单独引用 host/port
CHANNEL_LAYERS = {'CONFIG': {'hosts': [(REDIS_HOST, REDIS_PORT)]}}

# 直接引用完整 URL
CACHES = {'default': {'LOCATION': f'{REDIS_URL}/1'}}

# 无 Django 环境的模块用函数级 import
def get_redis():
    from conf.env import REDIS_HOST, REDIS_PORT
    return redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), ...)
```


### 提取通用函数

在 `backend/common/utils/redis_helper.py` 新增 `get_redis()` 工具函数，替换所有硬编码：

| 文件 | 修改前 | 修改后 |
|------|--------|--------|
| `common/utils/redis_helper.py` | **新增** | `get_redis(db, socket_timeout, decode)` |
| `opsflow/signals/timeout.py` | `redis.Redis(host=..., port=...)` | `get_redis(db=0)` |
| `opsflow/core/node_timeout_strategy.py` | 同上 | 同上 |
| `opsflow/apps.py` | `redis.Redis(host=getattr(settings...))` | `get_redis(db=0, decode=False)` |
| `opsflow/management/commands/start_opsflow_scheduler.py` | 同上 | 同上 |
| `itsm/management/commands/start_itsm_scheduler.py` | 同上 | 同上 |

```python
# backend/common/utils/redis_helper.py
def get_redis(db=0, socket_timeout=3, decode=True):
    from django.conf import settings
    import redis
    host = getattr(settings, 'REDIS_HOST', '127.0.0.1')
    port = int(getattr(settings, 'REDIS_PORT', 6379))
    return redis.Redis(host=host, port=port, db=db,
                       socket_connect_timeout=socket_timeout,
                       decode_responses=decode)
```

使用规则：**所有 Redis 直连代码必须使用 `common.utils.redis_helper.get_redis()`**，不要重复 `from conf.env import REDIS_HOST`。业务代码通过 `django.conf.settings` 间接读取配置，配置来源变化时业务代码无需修改。

## 影响的服务

修改 Redis 地址后需重启的服务：
- Django 主进程（`python manage.py runserver` / uwsgi）
- Celery Worker（`celery -A application worker`）
- Celery Beat（`celery -A application beat`）
- ASGI 服务（Daphne / Uvicorn）

## 部署注意事项

1. 生产环境设置 `DJANGO_ENV=prod`，在 `env_prod.py` 中覆写 `REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD`
2. 密码安全：`env_prod.py` 应通过环境变量或密钥管理服务读取密码，不硬编码
3. 如需新增配置变量，在 `env_base.py` 定义默认值，各环境文件按需覆写
4. 不要将 `env_prod.py` 提交到 git，建议在 `.gitignore` 中排除

## 回退方式

回退到硬编码：将各文件中 `REDIS_HOST`/`REDIS_URL` 替换回 `'127.0.0.1'`/`6379`，或 `git revert` 本次提交。
