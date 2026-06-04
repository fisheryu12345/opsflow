# -*- coding: utf-8 -*-
"""Serializers for CMDB app

MySQL 模型 + Neo4j 节点混合序列化
"""

import logging

from rest_framework import serializers
from dvadmin.utils.serializers import CustomModelSerializer

from .models.model_schema import ModelDefinition, ModelField

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  ModelDefinition (MySQL/ORM)
# ──────────────────────────────────────────────
class ModelDefinitionSerializer(CustomModelSerializer):
    """模型定义 — 列表/详情"""
    field_count = serializers.SerializerMethodField()

    class Meta:
        model = ModelDefinition
        fields = "__all__"

    def get_field_count(self, obj):
        return obj.fields.count()


class ModelDefinitionCreateUpdateSerializer(CustomModelSerializer):
    """模型定义 — 创建/修改"""
    class Meta:
        model = ModelDefinition
        fields = "__all__"


# ──────────────────────────────────────────────
#  ModelField (MySQL/ORM)
# ──────────────────────────────────────────────
class ModelFieldSerializer(CustomModelSerializer):
    """模型字段 — 列表/详情"""
    class Meta:
        model = ModelField
        fields = "__all__"


class ModelFieldCreateUpdateSerializer(CustomModelSerializer):
    """模型字段 — 创建/修改"""
    class Meta:
        model = ModelField
        fields = "__all__"


# ──────────────────────────────────────────────
#  Neo4j 节点序列化器 (不继承 CustomModelSerializer)
# ──────────────────────────────────────────────
class Neo4jNodeSerializer(serializers.Serializer):
    """Neo4j 节点通用序列化器"""
    node_id = serializers.CharField(source='element_id', read_only=True)
    labels = serializers.ListField(read_only=True)


class BizSerializer(serializers.Serializer):
    biz_id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    lifecycle = serializers.CharField()
    operator = serializers.CharField(required=False, default='')
    description = serializers.CharField(required=False, default='')
    labels = serializers.JSONField(required=False, default={})
    created_at = serializers.DateTimeField(read_only=True)


class HostSerializer(serializers.Serializer):
    host_id = serializers.CharField(read_only=True)
    ip = serializers.CharField()
    hostname = serializers.CharField(required=False, default='')
    os_type = serializers.CharField(required=False, default='linux')
    cpu_cores = serializers.IntegerField(required=False, default=0)
    memory_mb = serializers.IntegerField(required=False, default=0)
    disk_gb = serializers.IntegerField(required=False, default=0)
    status = serializers.CharField(required=False, default='normal')
    agent_status = serializers.CharField(required=False, default='unknown')
    labels = serializers.JSONField(required=False, default={})
    created_at = serializers.DateTimeField(read_only=True)


class SetSerializer(serializers.Serializer):
    set_id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    env_type = serializers.CharField(required=False, default='生产')
    description = serializers.CharField(required=False, default='')
    labels = serializers.JSONField(required=False, default={})
    created_at = serializers.DateTimeField(read_only=True)


class ModuleSerializer(serializers.Serializer):
    module_id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    service_type = serializers.CharField(required=False, default='web')
    description = serializers.CharField(required=False, default='')
    labels = serializers.JSONField(required=False, default={})
    created_at = serializers.DateTimeField(read_only=True)


class ProcessSerializer(serializers.Serializer):
    process_id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    port = serializers.IntegerField(required=False, default=0)
    protocol = serializers.CharField(required=False, default='tcp')
    status = serializers.CharField(required=False, default='running')
    version = serializers.CharField(required=False, default='')
    labels = serializers.JSONField(required=False, default={})
    created_at = serializers.DateTimeField(read_only=True)
