# -*- coding: utf-8 -*-
"""AttributeGroup views — 属性分组管理"""

from common.utils.viewset import CustomModelViewSet

from ..models.attribute_group import AttributeGroup
from ..serializers import AttributeGroupSerializer


class AttributeGroupViewSet(CustomModelViewSet):
    """
    属性分组管理

    list: 查询属性分组列表
    create: 创建属性分组
    update: 修改属性分组
    destroy: 删除属性分组
    """
    model = AttributeGroup
    queryset = AttributeGroup.objects.all()
    serializer_class = AttributeGroupSerializer
    filter_fields = ['model_definition']
    ordering = ['model_definition', 'sort_order']
