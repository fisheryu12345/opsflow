"""
OAuth2 认证服务 — 支持多 provider
OAuth2 Authentication Service — Multi-provider support
"""
import json
import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class OAuthProviderBase:
    """OAuth2 provider 基类 (Base OAuth2 Provider)"""

    def __init__(self, config: dict):
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.authorize_url = config.get("authorize_url", "")
        self.token_url = config.get("token_url", "")
        self.userinfo_url = config.get("userinfo_url", "")
        self.scopes = config.get("scopes", ["openid", "profile", "email"])
        self.redirect_uri = config.get("redirect_uri", "")

    def get_authorize_url(self, state: str = "") -> str:
        """生成授权页面 URL (Generate authorization URL)"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "redirect_uri": self.redirect_uri,
        }
        if state:
            params["state"] = state
        return f"{self.authorize_url}?{urlencode(params)}"

    def exchange_code(self, code: str) -> Optional[dict]:
        """用 code 换取 access_token (Exchange code for access token)"""
        try:
            resp = requests.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"OAuth token exchange failed: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[dict]:
        """获取用户信息 (Fetch user info)"""
        try:
            resp = requests.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"OAuth userinfo failed: {e}")
            return None

    def parse_user(self, user_info: dict) -> dict:
        """从 provider 返回的用户信息中提取统一字段
        Extract unified fields from provider user info
        Returns: {open_id, username, email, avatar}
        """
        raise NotImplementedError


class OIDCProvider(OAuthProviderBase):
    """通用 OIDC Provider (Keycloak / Okta / Azure AD)"""

    def parse_user(self, user_info: dict) -> dict:
        return {
            "open_id": user_info.get("sub", ""),
            "username": user_info.get("preferred_username", user_info.get("name", "")),
            "email": user_info.get("email", ""),
            "avatar": user_info.get("picture", ""),
        }


class WeComProvider(OAuthProviderBase):
    """企业微信 OAuth2"""

    def get_authorize_url(self, state: str = "") -> str:
        params = {
            "appid": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "snsapi_base",
            "state": state or "wecom",
        }
        return f"{self.authorize_url}?{urlencode(params)}#wechat_redirect"

    def exchange_code(self, code: str) -> Optional[dict]:
        """企业微信使用 code 获取用户信息 (两步)"""
        # Step 1: 获取 access_token
        try:
            resp = requests.get(
                self.token_url,
                params={
                    "corpid": self.client_id,
                    "corpsecret": self.client_secret,
                },
                timeout=15,
            )
            resp.raise_for_status()
            token_data = resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error(f"WeCom token error: {token_data}")
                return None

            # Step 2: 获取用户信息
            user_resp = requests.get(
                self.userinfo_url,
                params={"access_token": access_token, "code": code},
                timeout=15,
            )
            user_resp.raise_for_status()
            result = user_resp.json()
            result["_access_token"] = access_token
            return result
        except Exception as e:
            logger.error(f"WeCom code exchange failed: {e}")
            return None

    def parse_user(self, user_info: dict) -> dict:
        return {
            "open_id": user_info.get("UserId", user_info.get("OpenId", "")),
            "username": user_info.get("UserId", ""),
            "email": user_info.get("email", ""),
            "avatar": user_info.get("avatar", ""),
        }


class DingTalkProvider(OAuthProviderBase):
    """钉钉 OAuth2"""

    def exchange_code(self, code: str) -> Optional[dict]:
        # 钉钉需要通过 code 获取用户 token
        try:
            resp = requests.post(
                self.token_url,
                json={
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret,
                    "code": code,
                    "grantType": "authorization_code",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"DingTalk token exchange failed: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[dict]:
        try:
            resp = requests.get(
                self.userinfo_url,
                headers={"x-acs-dingtalk-access-token": access_token},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"DingTalk userinfo failed: {e}")
            return None

    def parse_user(self, user_info: dict) -> dict:
        return {
            "open_id": user_info.get("openId", user_info.get("unionId", "")),
            "username": user_info.get("nick", user_info.get("name", "")),
            "email": user_info.get("email", ""),
            "avatar": user_info.get("avatarUrl", ""),
        }


class OAuthService:
    """OAuth2 认证服务入口"""

    PROVIDER_MAP = {
        "oidc": OIDCProvider,
        "wecom": WeComProvider,
        "dingtalk": DingTalkProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> Optional[OAuthProviderBase]:
        """获取 provider 实例 (Get provider instance)"""
        provider_cls = cls.PROVIDER_MAP.get(provider_name)
        if not provider_cls:
            return None
        config = settings.OAUTH_PROVIDERS.get(provider_name, {})
        if not config.get("client_id"):
            logger.warning(f"OAuth provider '{provider_name}' not configured")
            return None
        return provider_cls(config)

    @classmethod
    def get_authorize_url(cls, provider_name: str, state: str = "") -> str:
        """获取授权页面 URL"""
        provider = cls.get_provider(provider_name)
        if not provider:
            return ""
        return provider.get_authorize_url(state=state)

    @classmethod
    def handle_callback(cls, provider_name: str, code: str, state: str = "") -> Optional[dict]:
        """处理 OAuth 回调，返回 JWT token 数据
        Process OAuth callback, return JWT token data
        Returns: {"access": ..., "refresh": ..., "name": ..., "userId": ...} or None
        """
        provider = cls.get_provider(provider_name)
        if not provider:
            logger.error(f"Unknown provider: {provider_name}")
            return None

        # 1. Exchange code for token
        token_data = provider.exchange_code(code)
        if not token_data:
            logger.error("Failed to exchange code for token")
            return None

        # 2. Get access_token from response (key varies by provider)
        access_token = (
            token_data.get("access_token")
            or token_data.get("_access_token")
            or ""
        )
        if not access_token:
            logger.error(f"No access_token in exchange response: {token_data}")
            return None

        # 3. Fetch user info
        user_info = provider.get_user_info(access_token)
        if not user_info:
            logger.error("Failed to fetch user info")
            return None

        # 4. Extract unified user fields
        user_fields = provider.parse_user(user_info)
        open_id = user_fields.get("open_id", "")
        if not open_id:
            logger.error(f"No open_id from provider: {user_fields}")
            return None

        # 5. Find or create user by open_id (stored in username with prefix)
        return cls._resolve_user(provider_name, open_id, user_fields)

    @classmethod
    def _resolve_user(cls, provider_name: str, open_id: str, user_fields: dict) -> Optional[dict]:
        """根据 open_id 查找或创建用户，签发 JWT
        Find or create user by open_id, issue JWT
        """
        from rest_framework_simplejwt.tokens import RefreshToken

        # 使用 provider:open_id 作为唯一标识存储在 username 字段
        # 也可以创建一个单独的 OAuthAccount 模型，这里简化处理
        oauth_username = f"{provider_name}:{open_id}"
        user = UserModel.objects.filter(username=oauth_username).first()

        if not user:
            # 创建新用户
            email = user_fields.get("email", "") or f"{open_id}@{provider_name}.oauth"
            display_name = user_fields.get("username", open_id)[:40]
            user = UserModel.objects.create(
                username=oauth_username,
                name=display_name,
                email=email,
                avatar=user_fields.get("avatar", ""),
                user_type=0,
                is_active=True,
            )

        # 签发 JWT token
        refresh = RefreshToken.for_user(user)
        token_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "name": user.name,
            "userId": user.id,
            "avatar": user.avatar,
            "user_type": user.user_type,
        }

        # 记录登录日志 (无 request 对象时跳过)
        try:
            from dvadmin.utils.request_util import save_login_log
            # OAuth 回调没有传统 request, 记录基本日志
            from dvadmin.system.models import LoginLog
            LoginLog.objects.create(
                username=user.username,
                ip="0.0.0.0",
                agent=f"OAuth/{provider_name}",
                browser="OAuth",
                os="OAuth",
                creator_id=user.id,
                dept_belong_id=getattr(user, 'dept_id', None) or 0,
            )
        except Exception as e:
            logger.warning(f"Failed to save login log: {e}")

        return {"code": 2000, "msg": "OAuth login success", "data": token_data}
