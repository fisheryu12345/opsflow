from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import OpsKnowledge
from opsflow.serializers import OpsKnowledgeSerializer


class OpsKnowledgeViewSet(viewsets.ModelViewSet):
    queryset = OpsKnowledge.objects.all()
    serializer_class = OpsKnowledgeSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['title', 'content', 'tags']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'])
    def search(self, request):
        """RAG 搜索 — 基于文本匹配，后续可升级为向量检索"""
        query = request.data.get('query', '')
        if not query:
            return Response({'code': 4000, 'msg': 'query required', 'data': None})
        results = OpsKnowledge.objects.filter(content__icontains=query)
        ser = self.get_serializer(results[:10], many=True)
        return Response({'code': 2000, 'msg': 'success', 'data': ser.data})
