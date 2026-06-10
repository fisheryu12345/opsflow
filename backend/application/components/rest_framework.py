"""
rest_framework.py — DRF / Spectacular / simplejwt 配置
"""
from datetime import timedelta
from conf.env import *

# ── Django REST Framework ──
REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DATE_FORMAT": "%Y-%m-%d",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "dvadmin.utils.filters.CustomDjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "dvadmin.utils.pagination.CustomPagination",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "dvadmin.utils.exception.CustomExceptionHandler",
}

# ── drf-spectacular (API 文档) ──
SPECTACULAR_SETTINGS = {
    'TITLE': 'OpsFlow API',
    'DESCRIPTION': 'OpsFlow API Documentation',
    'VERSION': 'v1',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'SWAGGER_UI_SETTINGS': {
        'apisSorter': 'alpha',
        'operationsSorter': 'alpha',
        'jsonEditor': True,
    },
}

# ── simplejwt ──
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("JWT",),
    "ROTATE_REFRESH_TOKENS": True,
}
