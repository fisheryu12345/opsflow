"""Open API Gateway views — App, Token, Webhook management + external-facing endpoints
"""
import uuid
import hashlib
from datetime import datetime

from rest_framework.decorators import action
from django.utils import timezone
from django.conf import settings

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.models import ApiApp, OpenApiToken, WebhookSubscription, OpenApiLog
from ..serializers import (
    ApiAppSerializer, ApiAppCreateUpdateSerializer,
    OpenApiTokenSerializer, OpenApiTokenCreateSerializer,
    WebhookSubscriptionSerializer,
    OpenApiLogSerializer,
)
from ..services.webhook_service import dispatch_webhook

FSM = 'open_api_views'


class ApiAppViewSet(CustomModelViewSet):
    """第三方应用管理 CRUD"""
    model = ApiApp
    queryset = ApiApp.objects.all()
    serializer_class = ApiAppSerializer
    create_serializer_class = ApiAppCreateUpdateSerializer
    update_serializer_class = ApiAppCreateUpdateSerializer
    filter_fields = ['status', 'company']
    search_fields = ['name', 'company', 'contact_email']
    ordering = ['-create_datetime']


class OpenApiTokenViewSet(CustomModelViewSet):
    """凭证管理 CRUD + 重新生成"""
    model = OpenApiToken
    queryset = OpenApiToken.objects.all()
    serializer_class = OpenApiTokenSerializer
    create_serializer_class = OpenApiTokenCreateSerializer
    filter_fields = ['app', 'status']
    search_fields = ['access_key', 'description']
    ordering = ['-create_datetime']

    @action(methods=['POST'], detail=True)
    def revoke(self, request, pk=None):
        """吊销凭证"""
        instance = self.get_object()
        instance.status = 'revoked'
        instance.save(update_fields=['status'])
        return DetailResponse(msg='凭证已吊销')

    def perform_create(self, serializer):
        """自动生成 access_key / secret_key"""
        raw = uuid.uuid4().hex
        serializer.save(
            access_key=raw[:16].upper(),
            secret_key=hashlib.sha256((raw + settings.SECRET_KEY).encode()).hexdigest()[:32],
        )


class WebhookSubscriptionViewSet(CustomModelViewSet):
    """事件订阅管理 CRUD"""
    model = WebhookSubscription
    queryset = WebhookSubscription.objects.all()
    serializer_class = WebhookSubscriptionSerializer
    filter_fields = ['app', 'event_type', 'is_active']
    search_fields = ['name', 'callback_url']
    ordering = ['-create_datetime']


class OpenApiLogViewSet(CustomModelViewSet):
    """API 调用日志（只读）"""
    model = OpenApiLog
    queryset = OpenApiLog.objects.all()
    serializer_class = OpenApiLogSerializer
    filter_fields = ['app', 'response_status']
    ordering = ['-create_datetime']
    # 只读
    http_method_names = ['get', 'head', 'options']
