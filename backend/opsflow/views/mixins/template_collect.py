"""Template Collect — 收藏/取消收藏端点 Mixin"""

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from opsflow.models import TemplateCollect
from opsflow.serializers import TemplateCollectSerializer


class TemplateCollectMixin:
    """收藏管理端点混入"""

    @action(detail=True, methods=['post'])
    def collect(self, request, pk=None):
        """收藏模板"""
        template = self.get_object()
        obj, created = TemplateCollect.objects.get_or_create(
            user=request.user,
            template=template,
        )
        return Response({
            'code': 2000, 'msg': 'Collected' if created else 'Already collected',
            'data': {'collected': True},
        })

    @action(detail=True, methods=['post'])
    def uncollect(self, request, pk=None):
        """取消收藏"""
        template = self.get_object()
        deleted, _ = TemplateCollect.objects.filter(
            user=request.user, template=template
        ).delete()
        return Response({
            'code': 2000, 'msg': 'Uncollected' if deleted else 'Not collected',
            'data': {'collected': False},
        })

    @action(detail=True, methods=['get'])
    def is_collected(self, request, pk=None):
        """检查当前用户是否已收藏"""
        template = self.get_object()
        collected = TemplateCollect.objects.filter(
            user=request.user, template=template
        ).exists()
        return Response({
            'code': 2000, 'data': {'collected': collected},
        })
