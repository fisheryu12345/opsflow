# Django 4.2 → 5.2 升级说明

升级时间: 2026-06-09
升级分支: `upgrade/django-5.2`

---

## 新环境部署步骤

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

> ⚠️ 注意：bamboo-pipeline 4.0.2 的 PyPI 元数据声明了 `Django<5` 约束，
> 但实际与 Django 5.2 兼容（仅需要修补一处已废弃的 API）。
> 如果 pip 因依赖冲突报错，使用 `--no-deps` 安装 bamboo-pipeline：
> ```bash
> pip install bamboo-pipeline==4.0.2 --no-deps
> ```

### 2. 运行 bamboo-pipeline 兼容补丁

```bash
python scripts/patch_bamboo_pipeline.py
```

该脚本会将 `site-packages/pipeline/eri/models.py` 中的
`index_together` 替换为 Django 5.x 的 `indexes` 语法。

> 💡 如果你的机器上有多个虚拟环境（如同时存在 `.venv` 和 `Vue/.venv`），
> 用 `--all` 参数可一次性修补所有副本：
> ```bash
> python scripts/patch_bamboo_pipeline.py --all
> ```

### 3. 迁移 & 启动

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 4. 启动 Celery Worker

> ⚠️ **不要直接使用 `celery` 命令** — Windows 上 .exe shim 可能绑定到错误的 Python 解释器。
> **始终使用 `python -m celery`**：

```bash
python -m celery -A application worker -Q er_execute,er_schedule,default -l info -P gevent -c 10
```

---

## API 文档变更

| 项目 | 旧 (drf-yasg) | 新 (drf-spectacular) |
|------|---------------|---------------------|
| Schema JSON | `/swagger.json` | `/api/schema/` |
| Swagger UI | `/` | `/` (不变) |
| Redoc | `/redoc/` | `/redoc/` (不变) |

---

## 升级内容清单

### 依赖版本变更

| 包 | 旧版本 | 新版本 |
|------|--------|--------|
| Django | 4.2.7 | **5.2.15** |
| djangorestframework | 3.14.0 | **3.17.1** |
| channels | 3.0.5 | **4.3.2** |
| daphne | 3.0.2 | **4.2.2** |
| channels-redis | 4.1.0 | **4.3.0** |
| drf-yasg | 1.21.7 | → **drf-spectacular 0.29.0** |
| django-restql | 0.15.3 | **0.18.0** |
| django-simple-captcha | 0.5.20 | **0.6.3** |
| django-cors-headers | 4.3.0 | **4.9.0** |
| django-filter | 23.3 | **25.2** |
| django-timezone-field | 6.0.1 | **7.2.2** |
| djangorestframework-simplejwt | 5.3.0 | **5.5.1** |
| simpleui | (旧版) | **django-simpleui 2026.1.13** |
| whitenoise | 6.6.0 | **6.12.0** |

### 已移除的依赖

- `django-ranged-response` — 被 captcha 间接引用，captcha 0.6.3 已自带

### 代码修改清单

| 文件 | 修改内容 |
|------|----------|
| `application/settings.py` | 添加 `"daphne"` app；`drf_yasg` → `drf_spectacular`；`SWAGGER_SETTINGS` → `SPECTACULAR_SETTINGS`；添加 `DEFAULT_SCHEMA_CLASS` |
| `application/urls.py` | drf-yasg 路由 → drf-spectacular 路由 (`/api/schema/`) |
| `dvadmin/utils/swagger.py` | 重写为 drf-spectacular `AutoSchema` |
| `dvadmin/utils/viewset.py` | `swagger_auto_schema` → `extend_schema`；`openapi.Schema` → inline dict |
| `dvadmin/utils/filters.py` | 移除 `import six`；`six.text_type()` → `str()` |
| `dvadmin/system/views/login.py` | `swagger_auto_schema` → `extend_schema` |
| `monitor/models/strategy.py` | `index_together` → `indexes` (×2) |
| `monitor/models/alert.py` | `index_together` → `indexes` |

### 新增文件

| 文件 | 说明 |
|------|------|
| `scripts/patch_bamboo_pipeline.py` | bamboo-pipeline Django 5.x 兼容补丁脚本 |
| `docs/architecture/upgrade-django5.md` | 本文档 |
