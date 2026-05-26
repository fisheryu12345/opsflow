# backend/opsagent/views/audit.py
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from opsagent.models import AuditRecord
from opsagent.serializers import AuditRecordSerializer


class AuditRecordViewSet(ReadOnlyModelViewSet):
    queryset = AuditRecord.objects.all()
    serializer_class = AuditRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['tool_name', 'safety_decision', 'risk_operation', 'execution_success', 'session_id']
    search_fields = ['target', 'result_summary']
    ordering = ['-timestamp']
