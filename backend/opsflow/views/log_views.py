from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from opsflow.models import OpsLog
from opsflow.serializers import OpsLogSerializer


class OpsLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OpsLog.objects.all()
    serializer_class = OpsLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['execution', 'risk_level', 'step']
    ordering = ['created_at']
