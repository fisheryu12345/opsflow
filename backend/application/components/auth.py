"""
auth.py — 登录方式 / JWT / OAuth2/SSO / 验证码 配置
"""
from conf.env import *

# ── 认证后端 ──
AUTHENTICATION_BACKENDS = ["dvadmin.utils.backends.CustomBackend"]

# ── 验证码 ──
CAPTCHA_IMAGE_SIZE = (160, 46)
CAPTCHA_LENGTH = 4
CAPTCHA_TIMEOUT = 1
CAPTCHA_OUTPUT_FORMAT = "%(image)s %(text_field)s %(hidden_field)s "
CAPTCHA_FONT_SIZE = 36
CAPTCHA_FOREGROUND_COLOR = "#64DAAA"
CAPTCHA_BACKGROUND_COLOR = "#F5F7F4"
CAPTCHA_NOISE_FUNCTIONS = (
    "captcha.helpers.noise_arcs",
)
CAPTCHA_CHALLENGE_FUNCT = "captcha.helpers.math_challenge"

# ── OAuth2/SSO ──
OAUTH_PROVIDERS = {
    'oidc': {
        'client_id': '',
        'client_secret': '',
        'authorize_url': '',
        'token_url': '',
        'userinfo_url': '',
        'scopes': ['openid', 'profile', 'email'],
        'redirect_uri': '',
    },
    'wecom': {
        'client_id': '',
        'client_secret': '',
        'authorize_url': 'https://open.weixin.qq.com/connect/oauth2/authorize',
        'token_url': 'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
        'userinfo_url': 'https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo',
        'scopes': ['snsapi_base'],
        'redirect_uri': '',
    },
    'dingtalk': {
        'client_id': '',
        'client_secret': '',
        'authorize_url': 'https://login.dingtalk.com/oauth2/auth',
        'token_url': 'https://api.dingtalk.com/v1.0/oauth2/userAccessToken',
        'userinfo_url': 'https://api.dingtalk.com/v1.0/contact/users/me',
        'scopes': ['openid', 'profile'],
        'redirect_uri': '',
    },
}
