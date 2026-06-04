# -*- coding: utf-8 -*-
"""MainlineTopo views — 主线拓扑定义管理"""

from dvadmin.utils.viewset import CustomModelViewSet

from ..models.mainline_topo import MainlineTopo
from ..serializers import MainlineTopoSerializer


class MainlineTopoViewSet(CustomModelViewSet):
    """
    主线拓扑定义管理

    list: 查询主线拓扑列表
    create: 定义拓扑层级
    update: 修改层级定义
    destroy: 删除层级定义
    """
    model = MainlineTopo
    queryset = MainlineTopo.objects.all()
    serializer_class = MainlineTopoSerializer
    filter_fields = ['model_definition', 'parent_model']
    ordering = ['sort_order']
