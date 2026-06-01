from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import OpsLog
from opsflow.serializers import OpsLogSerializer
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


class OpsLogViewSet(viewsets.ReadOnlyModelViewSet):
    """OpsLog 通过 execution.project 间接隔离，不直接设 project FK"""
    queryset = OpsLog.objects.all()
    serializer_class = OpsLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['execution', 'risk_level', 'step']
    ordering = ['created_at']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return SuccessResponse(data=serializer.data, page=int(request.query_params.get('page', 1)),
                                   limit=self.paginator.get_page_size(request) if hasattr(self.paginator, 'get_page_size') else 10,
                                   total=self.paginator.page.paginator.count if hasattr(self.paginator, 'page') else queryset.count())
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, total=queryset.count())

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)
