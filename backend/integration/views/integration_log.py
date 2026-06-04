# -*- coding: utf-8 -*-
"""ViewSet for IntegrationLog

调用日志 — 只读列表/详情
"""

from rest_framework import filters, mixins, viewsets

from dvadmin.utils.json_response import DetailResponse

from ..models.integration_log import IntegrationLog
from ..serializers import IntegrationLogSerializer


class IntegrationLogViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """
    集成调用日志（只读）

    list: 查询列表
    retrieve: 查询详情
    """
    queryset = IntegrationLog.objects.all()
    serializer_class = IntegrationLogSerializer
    filter_fields = ['instance', 'status', 'action', 'source_app']
    search_fields = ['action', 'error_message']
    ordering = ['-create_datetime']
    # 只读视图不需要 create/update/destroy
