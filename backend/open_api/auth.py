"""OpenAPI Authentication — token-based auth for external API endpoints

对外开放 API 的 Token 认证 + 调用日志记录。
"""

import logging
import time

from django.utils import timezone
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from open_api.models.models import OpenApiToken, OpenApiLog, ApiApp

logger = logging.getLogger(__name__)

FSM = "open_api_auth"


class OpenApiAuthentication(authentication.BaseAuthentication):
    """OpenAPI Token 认证 — 从 Header 或 Query 参数读取 token

    认证流程:
      1. 从 Authorization: Bearer <token> 或 access_token 查询参数读取 token
      2. 验证 token 有效性（过期、吊销、应用状态）
      3. 记录 API 调用日志到 OpenApiLog
      4. 返回 (api_app, token)

    注意:
      - 返回 None 表示无认证信息（不拦截），由其他认证器继续处理
      - 抛出 AuthenticationFailed 表示认证失败
    """

    # 不需要认证的路径前缀
    BYPASS_PATHS = [
        "/api/v2/open/health/",
        "/api/v2/open/swagger/",
        "/api/v2/open/docs/",
    ]

    def authenticate(self, request):
        """执行认证

        Returns:
            tuple: (api_app, token) 认证成功
            None: 无认证信息，跳过
        """
        # 健康检查等端点免认证
        path = request.path
        for bypass in self.BYPASS_PATHS:
            if path.startswith(bypass):
                return None

        # 1. 从请求中提取 token
        token_str = self._extract_token(request)
        if not token_str:
            return None

        # 2. 验证 token
        try:
            token_obj = OpenApiToken.objects.select_related("app").get(
                access_key=token_str,
            )
        except OpenApiToken.DoesNotExist:
            logger.warning("[%s] Invalid token: %s...", FSM, token_str[:8])
            raise AuthenticationFailed("Invalid API token")

        # 3. 检查 token 状态
        if token_obj.status == "revoked":
            logger.warning("[%s] Revoked token: %s", FSM, token_obj.access_key)
            raise AuthenticationFailed("Token has been revoked")

        if token_obj.status == "expired":
            raise AuthenticationFailed("Token has expired")

        if token_obj.expire_at and token_obj.expire_at < timezone.now():
            token_obj.status = "expired"
            token_obj.save(update_fields=["status"])
            raise AuthenticationFailed("Token has expired")

        # 4. 检查应用状态
        app = token_obj.app
        if app.status == "disabled":
            raise AuthenticationFailed("Application is disabled")

        if app.status == "expired":
            raise AuthenticationFailed("Application has expired")

        if app.expire_at and app.expire_at < timezone.now():
            app.status = "expired"
            app.save(update_fields=["status"])
            raise AuthenticationFailed("Application has expired")

        # 5. 检查 IP 白名单
        if app.allowed_ips:
            client_ip = self._get_client_ip(request)
            if client_ip and client_ip not in app.allowed_ips:
                logger.warning(
                    "[%s] IP %s not in whitelist for app %s",
                    FSM, client_ip, app.name,
                )
                raise AuthenticationFailed("IP not allowed")

        # 6. 更新 token 最后使用时间
        token_obj.last_used_at = timezone.now()
        token_obj.save(update_fields=["last_used_at"])

        # 7. 异步记录 API 调用日志
        self._log_api_call(request, app, token_obj)

        return (app, token_obj)

    def authenticate_header(self, request):
        """返回认证头描述"""
        return 'Bearer realm="open-api"'

    @staticmethod
    def _extract_token(request) -> str:
        """从请求中提取 token 字符串

        优先级: Authorization Header > access_token query param
        """
        # 从 Authorization Header 提取
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # 从查询参数提取
        token = request.query_params.get("access_token")
        if token:
            return token.strip()

        return ""

    @staticmethod
    def _get_client_ip(request) -> str:
        """获取客户端 IP 地址"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def _log_api_call(request, app: ApiApp, token: OpenApiToken):
        """记录 API 调用日志"""
        try:
            body_preview = {}
            if request.method in ("POST", "PUT", "PATCH") and hasattr(request, "data"):
                try:
                    data = request.data
                    if isinstance(data, dict):
                        # 只记录部分数据，避免敏感信息
                        body_preview = {k: v for k, v in list(data.items())[:10]}
                except Exception:
                    pass

            ip = OpenApiAuthentication._get_client_ip(request)
            OpenApiLog.objects.create(
                app=app,
                token=token,
                request_path=request.path,
                request_method=request.method,
                request_params=body_preview,
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )
        except Exception as e:
            logger.warning("[%s] Failed to log API call: %s", FSM, e)
