"""
env_uat.py — UAT 环境覆写

只写与 env_base.py 不同的值。
由运维根据实际 UAT 环境填写。
"""
DEBUG = False
LOGIN_NO_CAPTCHA_AUTH = False
OPSFLOW_SCHEDULER_AUTOSTART = False

# DATABASE_HOST = "uat-db.internal"
# DATABASE_USER = "opsflow_uat"
# DATABASE_PASSWORD = "..."
