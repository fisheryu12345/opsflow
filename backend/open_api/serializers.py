"""Serializers for Open API Gateway
"""

from rest_framework import serializers
from dvadmin.utils.serializers import CustomModelSerializer
from .models.models import ApiApp, OpenApiToken, WebhookSubscription, OpenApiLog


class ApiAppSerializer(CustomModelSerializer):
    class Meta:
        model = ApiApp
        fields = "__all__"


class ApiAppCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = ApiApp
        fields = "__all__"


class OpenApiTokenSerializer(CustomModelSerializer):
    """Token 详情 — 隐藏 secret_key，仅显示掩码"""
    secret_key_mask = serializers.SerializerMethodField()

    class Meta:
        model = OpenApiToken
        fields = ['id', 'app', 'app_name', 'access_key', 'secret_key_mask',
                  'status', 'last_used_at', 'expire_at', 'description',
                  'create_datetime', 'update_datetime']
        read_only_fields = ['access_key', 'secret_key_mask', 'last_used_at',
                            'create_datetime', 'update_datetime']

    app_name = serializers.SerializerMethodField()

    def get_app_name(self, obj):
        return obj.app.name if obj.app else ''

    def get_secret_key_mask(self, obj):
        """返回掩码后的 secret_key"""
        sk = obj.secret_key
        if sk and len(sk) > 8:
            return sk[:4] + '*' * (len(sk) - 8) + sk[-4:]
        return '****'


class OpenApiTokenCreateSerializer(CustomModelSerializer):
    """创建 Token — 创建后返回完整的 access_key 和 secret_key"""
    access_key = serializers.CharField(read_only=True)
    secret_key = serializers.CharField(read_only=True)

    class Meta:
        model = OpenApiToken
        fields = ['app', 'description', 'expire_at', 'access_key', 'secret_key']


class OpenApiTokenRegenerateSerializer(serializers.Serializer):
    """重新生成凭证"""
    description = serializers.CharField(required=False, allow_blank=True)


class WebhookSubscriptionSerializer(CustomModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = "__all__"


class OpenApiLogSerializer(CustomModelSerializer):
    class Meta:
        model = OpenApiLog
        fields = "__all__"
        read_only_fields = [f.name for f in OpenApiLog._meta.fields]
