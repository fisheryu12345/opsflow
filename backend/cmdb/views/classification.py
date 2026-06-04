# -*- coding: utf-8 -*-
"""Classification views — 模型分类管理"""

from dvadmin.utils.viewset import CustomModelViewSet

from ..models.classification import Classification
from ..serializers import (
    ClassificationSerializer,
    ClassificationCreateUpdateSerializer,
)


class ClassificationViewSet(CustomModelViewSet):
    """
    模型分类管理

    list: 查询分类列表
    create: 创建分类
    update: 修改分类
    retrieve: 分类详情
    destroy: 删除分类
    """
    model = Classification
    queryset = Classification.objects.all()
    serializer_class = ClassificationSerializer
    create_serializer_class = ClassificationCreateUpdateSerializer
    update_serializer_class = ClassificationCreateUpdateSerializer
    search_fields = ['cls_id', 'name']
    ordering = ['sort_order', 'name']
