"""Template Collect — 收藏/取消收藏端点 Mixin"""

from rest_framework.decorators import action
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
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
        return DetailResponse(data={'collected': True}, msg='Collected' if created else 'Already collected')

    @action(detail=True, methods=['post'])
    def uncollect(self, request, pk=None):
        """取消收藏"""
        template = self.get_object()
        deleted, _ = TemplateCollect.objects.filter(
            user=request.user, template=template
        ).delete()
        return DetailResponse(data={'collected': False}, msg='Uncollected' if deleted else 'Not collected')

    @action(detail=True, methods=['get'])
    def is_collected(self, request, pk=None):
        """检查当前用户是否已收藏"""
        template = self.get_object()
        collected = TemplateCollect.objects.filter(
            user=request.user, template=template
        ).exists()
        return DetailResponse(data={'collected': collected})
