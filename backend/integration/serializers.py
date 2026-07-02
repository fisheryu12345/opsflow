# -*- coding: utf-8 -*-
"""Serializers for integration app

遵循统一规范：继承 CustomModelSerializer，自动填充审计字段
"""

from common.utils.serializers import CustomModelSerializer
from rest_framework import serializers

from .models.connector import ConnectorDefinition, ConnectorInstance
from .models.credential import ConnectorCredential
from .models.integration_log import IntegrationLog


# ──────────────────────────────────────────────
#  ConnectorDefinition Serializers
# ──────────────────────────────────────────────
class ConnectorDefinitionSerializer(CustomModelSerializer):
    """连接器定义 — 列表/详情"""
    class Meta:
        model = ConnectorDefinition
        fields = "__all__"


class ConnectorDefinitionCreateUpdateSerializer(CustomModelSerializer):
    """连接器定义 — 创建/修改"""
    class Meta:
        model = ConnectorDefinition
        fields = "__all__"


# ──────────────────────────────────────────────
#  ConnectorInstance Serializers
# ──────────────────────────────────────────────
class ConnectorInstanceSerializer(CustomModelSerializer):
    """连接器实例 — 列表/详情"""
    definition_code = ConnectorDefinitionSerializer(
        source='definition', read_only=True
    )

    class Meta:
        model = ConnectorInstance
        fields = "__all__"
        read_only_fields = ['last_health_check', 'last_health_message', 'status']


class ConnectorInstanceCreateUpdateSerializer(CustomModelSerializer):
    """连接器实例 — 创建/修改"""
    class Meta:
        model = ConnectorInstance
        fields = "__all__"


# ──────────────────────────────────────────────
#  ConnectorCredential Serializers
# ──────────────────────────────────────────────
class ConnectorCredentialSerializer(CustomModelSerializer):
    """连接器凭证 — 列表/详情（解密展示）"""
    class Meta:
        model = ConnectorCredential
        fields = "__all__"
        # encrypted_value 通过自定义 action 解密，序列化时不暴露
        read_only_fields = ['encrypted_value', 'last_used_at']


class ConnectorCredentialCreateUpdateSerializer(CustomModelSerializer):
    """连接器凭证 — 创建/修改（自动加密）"""
    class Meta:
        model = ConnectorCredential
        fields = "__all__"

    def validate_encrypted_value(self, value):
        """创建时自动加密凭证值"""
        from integration.services.credential_service import encrypt_credential
        return encrypt_credential(value)


class ConnectorCredentialDecryptSerializer(serializers.Serializer):
    """连接器凭证 — 解密返回（仅用于显式查看操作）"""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    decrypted_value = serializers.CharField(read_only=True, help_text="解密后的凭证值")
    cred_type = serializers.CharField(read_only=True)
    expire_at = serializers.DateTimeField(read_only=True)


# ──────────────────────────────────────────────
#  IntegrationLog Serializers
# ──────────────────────────────────────────────
class IntegrationLogSerializer(CustomModelSerializer):
    """集成调用日志 — 列表/详情"""
    class Meta:
        model = IntegrationLog
        fields = "__all__"
        read_only_fields = [field.name for field in IntegrationLog._meta.fields]
