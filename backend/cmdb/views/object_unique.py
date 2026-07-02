# -*- coding: utf-8 -*-
"""ObjectUnique views — 唯一约束管理"""

from common.utils.viewset import CustomModelViewSet

from ..models.object_unique import ObjectUnique
from ..serializers import ObjectUniqueSerializer


class ObjectUniqueViewSet(CustomModelViewSet):
    """
    唯一约束管理

    list: 查询唯一约束列表
    create: 创建唯一约束
    update: 修改唯一约束
    destroy: 删除唯一约束
    """
    model = ObjectUnique
    queryset = ObjectUnique.objects.all()
    serializer_class = ObjectUniqueSerializer
    filter_fields = ['model_definition']
