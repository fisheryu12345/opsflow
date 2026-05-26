# backend/opsagent/views/session.py
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from opsagent.models import Session
from opsagent.serializers import SessionSerializer


class SessionViewSet(ReadOnlyModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['mode', 'status', 'operator']
    ordering = ['-started_at']
