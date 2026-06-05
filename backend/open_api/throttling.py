"""OpenAPI Rate Throttling — per-app rate limiting for external API endpoints

对外开放 API 的频率限制，基于 ApiApp 的 rate_limit 配置。
每个应用独立计数，应用级别 rate_limit 字段控制 QPS。
"""

import logging
import time

from django.core.cache import cache as default_cache
from rest_framework import throttling
from rest_framework.exceptions import Throttled

from open_api.models.models import ApiApp

logger = logging.getLogger(__name__)

FSM = "open_api_throttle"


class OpenApiRateThrottle(throttling.BaseThrottle):
    """基于 ApiApp 的频率限制

    使用 ApiApp.rate_limit 字段作为 QPS 限制。
    缓存 key 格式: throttle_open_api_{app_id} 或 throttle_open_api_ip_{ip}
    每秒重置计数窗口。
    """

    cache = default_cache
    CACHE_PREFIX = "throttle_open_api"
    WINDOW_SECONDS = 1  # 窗口大小（秒）
    DEFAULT_QPS = 100

    def allow_request(self, request, view):
        """判断请求是否允许通过

        健康检查端点不限流。
        """
        path = request.path
        if path.endswith("/health/"):
            return True

        # 获取限流 key 和 QPS 上限
        key = self._get_cache_key(request)
        max_qps = self._get_max_qps(request)

        if not key:
            return True

        # 使用滑动窗口计数
        now = time.time()
        window_start = int(now)

        # 获取当前窗口的计数
        cache_key = f"{self.CACHE_PREFIX}:{key}:{window_start}"
        count = self.cache.get(cache_key, 0)

        if count >= max_qps:
            # 达到限制
            self._record_throttle(request, key, max_qps)
            return False

        # 增加计数
        self.cache.set(cache_key, count + 1, self.WINDOW_SECONDS + 1)
        return True

    def wait(self):
        """返回需要等待的秒数"""
        return 1  # 固定返回 1 秒

    @staticmethod
    def _get_cache_key(request) -> str:
        """生成缓存 key

        优先使用认证后的 app_id，其次使用 IP。
        """
        if hasattr(request, "auth") and request.auth:
            app_id = None
            if hasattr(request.auth, "app_id"):
                app_id = request.auth.app_id
            elif hasattr(request.auth, "app"):
                app = request.auth.app
                if hasattr(app, "id"):
                    app_id = app.id
            if app_id:
                return f"app_{app_id}"

        # 未认证的请求，按 IP 限流
        ident = throttling.BaseThrottle().get_ident(request)
        return f"ip_{ident}"

    @staticmethod
    def _get_max_qps(request) -> int:
        """从 ApiApp 配置获取 QPS 上限"""
        if hasattr(request, "auth") and request.auth:
            try:
                # 从认证对象获取关联的 app
                if hasattr(request.auth, "app"):
                    app = request.auth.app
                elif hasattr(request.auth, "app_id"):
                    app = ApiApp.objects.filter(id=request.auth.app_id).first()
                else:
                    return OpenApiRateThrottle.DEFAULT_QPS

                if app and hasattr(app, "rate_limit"):
                    return max(1, app.rate_limit)
            except Exception as e:
                logger.warning("[%s] Failed to get QPS from app: %s", FSM, e)

        return OpenApiRateThrottle.DEFAULT_QPS

    @staticmethod
    def _record_throttle(request, key: str, max_qps: int):
        """记录限流事件日志"""
        try:
            from open_api.models.models import OpenApiLog
            ip = ""
            if hasattr(request, "META"):
                x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR", "")

            OpenApiLog.objects.create(
                app=getattr(request.auth, "app", None) if hasattr(request, "auth") else None,
                request_path=request.path,
                request_method=request.method,
                response_status=429,
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if hasattr(request, "META") else "",
                error_message=f"Rate limit exceeded: {key} > {max_qps} QPS",
            )
        except Exception as e:
            logger.warning("[%s] Failed to log throttle event: %s", FSM, e)


def throttle_failure_view(request, exception):
    """限流触发的自定义响应"""
    from django.http import JsonResponse
    return JsonResponse(
        {"code": 4029, "msg": "API rate limit exceeded. Please try again later.", "data": None},
        status=429,
    )
