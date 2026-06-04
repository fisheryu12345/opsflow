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
    class Meta:
        model = OpenApiToken
        fields = "__all__"
        read_only_fields = ['access_key', 'secret_key', 'last_used_at']


class OpenApiTokenCreateSerializer(CustomModelSerializer):
    class Meta:
        model = OpenApiToken
        fields = ['app', 'description', 'expire_at']


class WebhookSubscriptionSerializer(CustomModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = "__all__"


class OpenApiLogSerializer(CustomModelSerializer):
    class Meta:
        model = OpenApiLog
        fields = "__all__"
        read_only_fields = [f.name for f in OpenApiLog._meta.fields]
