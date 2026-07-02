# -*- coding: utf-8 -*-
"""ViewSet for ConnectorCredential

凭证管理 — CRUD + 解密查看
"""

from rest_framework.decorators import action
from rest_framework import filters

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse, ErrorResponse

from ..models.credential import ConnectorCredential
from ..serializers import (
    ConnectorCredentialSerializer,
    ConnectorCredentialCreateUpdateSerializer,
    ConnectorCredentialDecryptSerializer,
)

FSM = 'credential_viewset'


class ConnectorCredentialViewSet(CustomModelViewSet):
    """
    连接器凭证管理

    list: 查询凭证列表
    create: 创建凭证（自动加密存储）
    update: 修改凭证
    retrieve: 凭证详情（不返回密文）
    destroy: 删除凭证
    decrypt: 解密查看凭证值（需要独立授权）
    """
    model = ConnectorCredential
    queryset = ConnectorCredential.objects.all()
    serializer_class = ConnectorCredentialSerializer
    create_serializer_class = ConnectorCredentialCreateUpdateSerializer
    update_serializer_class = ConnectorCredentialCreateUpdateSerializer
    filter_fields = ['instance', 'cred_type']
    search_fields = ['name']
    ordering = ['-create_datetime']

    @action(methods=['POST'], detail=True)
    def decrypt(self, request, pk=None):
        """解密查看凭证值"""
        instance = self.get_object()
        from integration.services.credential_service import decrypt_credential
        plain_value = decrypt_credential(instance.encrypted_value)
        # 更新最后使用时间
        from django.utils import timezone
        instance.last_used_at = timezone.now()
        instance.save(update_fields=['last_used_at'])
        return DetailResponse(data={
            'id': instance.id,
            'name': instance.name,
            'decrypted_value': plain_value,
            'cred_type': instance.cred_type,
        })
