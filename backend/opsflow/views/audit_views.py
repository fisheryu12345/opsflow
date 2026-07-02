"""操作审计视图 — 只读查询接口"""

from rest_framework import viewsets, mixins
from opsflow.models import OperationRecord
from opsflow.serializers import OperationRecordSerializer
from common.utils.json_response import DetailResponse, SuccessResponse


class OperationRecordViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """操作审计记录 — 只读"""
    queryset = OperationRecord.objects.all()
    serializer_class = OperationRecordSerializer
    filterset_fields = ['action', 'resource_type', 'operator']
    ordering = ['-created_at']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")
