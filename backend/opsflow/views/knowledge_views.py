from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import OpsKnowledge
from opsflow.serializers import OpsKnowledgeSerializer
from opsflow.views.base import ProjectFilteredViewSet
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


class OpsKnowledgeViewSet(ProjectFilteredViewSet):
    queryset = OpsKnowledge.objects.all()
    serializer_class = OpsKnowledgeSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['title', 'content', 'tags']
    filterset_fields = ['source', 'project']
    ordering = ['-created_at']
    pagination_class = None
    project_field = 'project'

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, total=queryset.count())

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg='success')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return DetailResponse(data=serializer.data, msg='success')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})

    @action(detail=False, methods=['post'])
    def search(self, request):
        """RAG search — text-based matching, upgrade to vector search later"""
        query = request.data.get('query', '')
        if not query:
            return Response({'code': 4000, 'msg': 'query required', 'data': None})
        results = self.get_queryset().filter(content__icontains=query)
        ser = self.get_serializer(results[:20], many=True)
        return Response({'code': 2000, 'msg': 'success', 'data': ser.data})
