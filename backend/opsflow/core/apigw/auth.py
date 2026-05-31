"""API 网关 Token 认证"""
from django.utils import timezone
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from opsflow.models import ApiToken


class ApiTokenAuthentication(authentication.BaseAuthentication):
    """基于 X-Opsflow-ApiToken Header 的认证"""

    def authenticate(self, request):
        token_str = request.META.get('HTTP_X_OPSFLOW_APITOKEN') or request.META.get('HTTP_X_OPSFLOW_API_TOKEN', '')
        if not token_str:
            return None  # 无 token 时不拦截（让其他认证器处理）

        try:
            token_obj = ApiToken.objects.get(token=token_str, is_active=True)
        except ApiToken.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive API token')

        if token_obj.expires_at and token_obj.expires_at < timezone.now():
            raise AuthenticationFailed('API token expired')

        return (token_obj.created_by or None, token_obj)
