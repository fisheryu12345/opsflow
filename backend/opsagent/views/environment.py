from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from opsagent.models import EnvironmentContext
from opsagent.serializers import EnvironmentContextSerializer


class EnvironmentContextViewSet(ModelViewSet):
    queryset = EnvironmentContext.objects.all()
    serializer_class = EnvironmentContextSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['env_type', 'is_active']
    search_fields = ['name', 'slug']
    ordering = ['name']
