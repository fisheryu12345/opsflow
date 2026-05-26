from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from opsagent.models import AgentMemory
from opsagent.serializers import AgentMemorySerializer


class AgentMemoryViewSet(ModelViewSet):
    queryset = AgentMemory.objects.all()
    serializer_class = AgentMemorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['memory_type', 'is_active']
    search_fields = ['title', 'content']
    ordering = ['-created_at']
