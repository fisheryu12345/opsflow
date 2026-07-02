"""
OAuth2/SSO 登录视图
OAuth2/SSO Login Views
"""
import logging
import uuid

from django.conf import settings
from django.shortcuts import redirect
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.utils.json_response import DetailResponse, ErrorResponse

logger = logging.getLogger(__name__)

# 简单的 state 存储 (生产环境应使用 Redis)
# In-memory state store (use Redis in production)
_oauth_states: dict = {}


class OAuthLoginView(APIView):
    """OAuth2 登录入口 — 跳转到授权页面"""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, provider):
        """GET /api/system/oauth/login/{provider}/"""
        from iam.services.oauth_service import OAuthService

        provider_config = settings.OAUTH_PROVIDERS.get(provider)
        if not provider_config or not provider_config.get("client_id"):
            return ErrorResponse(msg=f"OAuth provider '{provider}' not configured", code=4000)

        state = str(uuid.uuid4())
        _oauth_states[state] = provider

        callback_url = (
            provider_config.get("redirect_uri")
            or request.build_absolute_uri(f"/api/system/oauth/callback/{provider}/")
        )

        provider_config = dict(provider_config)
        provider_config["redirect_uri"] = callback_url

        provider_cls = OAuthService.PROVIDER_MAP.get(provider)
        if not provider_cls:
            return ErrorResponse(msg=f"Unsupported provider: {provider}", code=4000)

        provider_obj = provider_cls(provider_config)
        authorize_url = provider_obj.get_authorize_url(state=state)
        if not authorize_url:
            return ErrorResponse(msg=f"Failed to generate authorize URL", code=4000)

        return redirect(authorize_url)


class OAuthCallbackView(APIView):
    """OAuth2 回调处理 — 获取token并创建/绑定用户"""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, provider):
        """GET /api/system/oauth/callback/{provider}/?code=xxx&state=xxx"""
        from iam.services.oauth_service import OAuthService

        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")

        if not code:
            return ErrorResponse(msg="Missing authorization code", code=4000)

        # Verify state (CSRF prevention)
        expected_provider = _oauth_states.pop(state, None)
        if state and expected_provider and expected_provider != provider:
            logger.warning(f"State mismatch: expected={expected_provider}, got={provider}")
            return ErrorResponse(msg="Invalid state parameter", code=4000)

        result = OAuthService.handle_callback(provider, code, state=state)
        if result is None:
            return ErrorResponse(msg="OAuth authentication failed", code=4000)

        redirect_url = request.query_params.get("redirect", "")
        if redirect_url:
            token_str = result.get("data", {}).get("access", "")
            return redirect(f"{redirect_url}#token={token_str}")

        return DetailResponse(data=result.get("data"), msg=result.get("msg", "OAuth login success"))


urlpatterns = [
    path("login/<str:provider>/", OAuthLoginView.as_view(), name="oauth-login"),
    path("callback/<str:provider>/", OAuthCallbackView.as_view(), name="oauth-callback"),
]
