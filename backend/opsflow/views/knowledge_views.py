import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import OpsKnowledge
from opsflow.serializers import OpsKnowledgeSerializer
from opsflow.views.base import ProjectFilteredViewSet
from iam.permissions import TenantPermission
from iam.permission_backend import IAMPermissionBackend
from common.utils.json_response import DetailResponse, SuccessResponse

logger = logging.getLogger(__name__)


class OpsKnowledgeViewSet(ProjectFilteredViewSet):
    queryset = OpsKnowledge.objects.all()
    serializer_class = OpsKnowledgeSerializer
    permission_classes = [IsAuthenticated, TenantPermission, IAMPermissionBackend]
    search_fields = ['title', 'content', 'tags']
    filterset_fields = ['source', 'project']
    ordering = ['-created_at']
    pagination_class = None
    project_field = 'project'
    required_permission = None
    action_permissions = {
        'create': 'opsflow:knowledge:create',
        'destroy': 'opsflow:knowledge:delete',
    }

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
        # Generate embedding on creation
        try:
            from opsflow.services.vector_service import VectorService
            instance = serializer.instance
            text = f"{instance.title} {instance.content} {' '.join(instance.tags or [])}"
            embedding = VectorService.generate_embedding(text)
            instance.set_embedding_vector(embedding)
            instance.save(update_fields=["embedding"])
        except Exception as e:
            logger.warning(f"Failed to generate embedding on create: {e}")
        return DetailResponse(data=serializer.data, msg='success')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Re-generate embedding on update
        try:
            from opsflow.services.vector_service import VectorService
            text = f"{instance.title} {instance.content} {' '.join(instance.tags or [])}"
            embedding = VectorService.generate_embedding(text)
            instance.set_embedding_vector(embedding)
            instance.save(update_fields=["embedding"])
        except Exception as e:
            logger.warning(f"Failed to regenerate embedding on update: {e}")
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

    @action(detail=False, methods=['get'])
    def semantic_search(self, request):
        """语义向量搜索 — 使用向量相似度查找相关知识条目
        Semantic vector search — find relevant knowledge via similarity
        GET /api/opsflow/knowledge/semantic_search/?q=xxx
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response({'code': 4000, 'msg': 'query parameter "q" required', 'data': None})

        top_k = int(request.query_params.get('top_k', 5))
        try:
            from opsflow.services.vector_service import VectorService
            results = VectorService.search_similar(query, top_k=top_k)
            return DetailResponse(data=results)
        except Exception as e:
            logger.exception(f"Semantic search failed: {e}")
            return Response({'code': 4000, 'msg': f'Semantic search error: {str(e)}', 'data': None})
