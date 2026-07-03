"""
env_base.py — 共享配置变量定义（所有环境相同的键 + 默认值）

各环境文件（env_dev/env_uat/env_prod）只覆写与本环境不同的值。
env.py 入口：先加载 base，再 exec 环境文件覆写。
"""

# ================================================= #
# *************** MySQL 数据库  ******************* #
# ================================================= #
DATABASE_ENGINE = "django.db.backends.mysql"
DATABASE_NAME = "stock"
DATABASE_USER = "trade"
DATABASE_HOST = "127.0.0.1"
DATABASE_PORT = 3306
# DATABASE_NAME = "opsflow"
# DATABASE_USER = "opsflow"
DATABASE_PASSWORD = "312711936!@#GHS"

# 表前缀
TABLE_PREFIX = "opsflow_"

# ================================================= #
# *************** Redis 配置  ********************* #
# ================================================= #
REDIS_PASSWORD = ""
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_URL = f"redis://:{REDIS_PASSWORD or ''}@{REDIS_HOST}:{REDIS_PORT}"

# ================================================= #
# *************** 功能开关  *********************** #
# ================================================= #
DEBUG = True
ENABLE_LOGIN_ANALYSIS_LOG = True
LOGIN_NO_CAPTCHA_AUTH = True

# ================================================= #
# *************** 主机/安全  ********************** #
# ================================================= #
ALLOWED_HOSTS = ["*"]
COLUMN_EXCLUDE_APPS = []

# ================================================= #
# *************** 邮件配置  *********************** #
# ================================================= #
EMAIL_ENABLE = False
EMAIL_HOST = "smtp.qq.com"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_FROM = ""
EMAIL_TO = []

# ================================================= #
# *************** OpsFlow 调度器  ***************** #
# ================================================= #
OPSFLOW_SCHEDULER_AUTOSTART = True

# ================================================= #
# *************** Neo4j 图数据库  ***************** #
# ================================================= #
NEO4J_PROTOCOL = "bolt"
NEO4J_HOST = "127.0.0.1"
NEO4J_PORT = 7687
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
NEO4J_DATABASE = "neo4j"
