"""操作审计视图 — 只读查询接口"""

from rest_framework import viewsets, mixins
from opsflow.models import OperationRecord
from opsflow.serializers import OperationRecordSerializer


class OperationRecordViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """操作审计记录 — 只读"""
    queryset = OperationRecord.objects.all()
    serializer_class = OperationRecordSerializer
    filterset_fields = ['action', 'resource_type', 'operator']
    ordering = ['-created_at']
