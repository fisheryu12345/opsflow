"""
env_prod.py — 生产环境覆写

只写与 env_base.py 不同的值。
由运维根据实际生产环境填写。
"""
DEBUG = False
ENABLE_LOGIN_ANALYSIS_LOG = False
LOGIN_NO_CAPTCHA_AUTH = False
# ALLOWED_HOSTS = ["opsflow.company.com"]
OPSFLOW_SCHEDULER_AUTOSTART = False  # 使用独立进程运行

# DATABASE_HOST = "10.0.1.100"
# DATABASE_USER = "opsflow_prod"
# DATABASE_PASSWORD = "..."
