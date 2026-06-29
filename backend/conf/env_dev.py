"""
env_dev.py — 开发环境覆写

只写与 env_base.py 不同的值。
"""
# 当前开发环境的实际配置值
DEBUG = True
ENABLE_LOGIN_ANALYSIS_LOG = True
LOGIN_NO_CAPTCHA_AUTH = True
ALLOWED_HOSTS = ["*"]
COLUMN_EXCLUDE_APPS = []

OPSFLOW_SCHEDULER_AUTOSTART = True

# ================================================= #
# *************** Agent Server  ******************** #
# ================================================= #
AGENT_SERVER_URL = "http://192.168.1.36:18080"

NEO4J_PROTOCOL = "bolt"
NEO4J_HOST = "127.0.0.1"
NEO4J_PORT = 7687
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
NEO4J_DATABASE = "neo4j"
