"""
database.py — DATABASES / Neo4j / CACHES / DB 路由配置

从 conf.env 获取原始值，组装为 Django 所需的结构体。
"""
from conf.env import *

# ── MySQL 主库 ──
DATABASES = {
    'default': {
        'ENGINE': DATABASE_ENGINE,
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'PASSWORD': DATABASE_PASSWORD,
        'HOST': DATABASE_HOST,
        'PORT': str(DATABASE_PORT),
        'CONN_MAX_AGE': 5,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'ssl': {'ssl-mode': 'DISABLED'},
        },
        'TEST': {
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        },
    }
}

# ── Test mode: use SQLite (MySQL test DB not available) ──
import sys
if 'test' in sys.argv or 'test_coverage' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }

# ── Neo4j 图数据库 (CMDB 拓扑存储) ──
NEO4J_PROTOCOL = locals().get("NEO4J_PROTOCOL", "bolt")
NEO4J_HOST = locals().get("NEO4J_HOST", "localhost")
NEO4J_PORT = locals().get("NEO4J_PORT", 7687)
NEO4J_USER = locals().get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = locals().get("NEO4J_PASSWORD", "password")

# Django database router: cmdb MySQL models → 'default'
DATABASE_ROUTERS = ['cmdb.neo4j_router.CmdbNeo4jRouter']

# ── Redis 缓存 ──
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
