# -*- coding: utf-8 -*-
"""Model definition & field management views (MySQL CRUD)"""

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import ErrorResponse

from ..models.model_definition import ModelDefinition, ModelField
from ..serializers import (
    ModelDefinitionSerializer,
    ModelDefinitionCreateUpdateSerializer,
    ModelFieldSerializer,
    ModelFieldCreateUpdateSerializer,
)


class ModelDefinitionViewSet(CustomModelViewSet):
    """
    模型定义管理

    list: 查询模型定义列表
    create: 创建模型定义(如自定义路由器)
    update: 修改模型定义
    retrieve: 模型定义详情(含字段列表)
    destroy: 删除模型定义(内置模型不可删除)
    """
    model = ModelDefinition
    queryset = ModelDefinition.objects.all()
    serializer_class = ModelDefinitionSerializer
    create_serializer_class = ModelDefinitionCreateUpdateSerializer
    update_serializer_class = ModelDefinitionCreateUpdateSerializer
    filter_fields = ['classification', 'is_builtin', 'source']
    search_fields = ['code', 'name']
    ordering = ['-is_builtin', 'name']

    def perform_destroy(self, instance):
        if instance.is_builtin:
            return ErrorResponse(msg='内置模型不可删除')
        return super().perform_destroy(instance)


class ModelFieldViewSet(CustomModelViewSet):
    """
    模型字段管理

    list: 查询字段列表（可按模型过滤）
    create: 创建字段
    update: 修改字段
    retrieve: 字段详情
    destroy: 删除字段
    """
    model = ModelField
    queryset = ModelField.objects.all()
    serializer_class = ModelFieldSerializer
    create_serializer_class = ModelFieldCreateUpdateSerializer
    update_serializer_class = ModelFieldCreateUpdateSerializer
    filter_fields = ['model_definition', 'field_type', 'required', 'group']
    search_fields = ['name', 'label']
    ordering = ['model_definition', 'sort_order']
