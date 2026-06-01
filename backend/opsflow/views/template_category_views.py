"""模板分类 API"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import TemplateCategory
from opsflow.serializers import TemplateCategorySerializer


class TemplateCategoryViewSet(viewsets.ModelViewSet):
    queryset = TemplateCategory.objects.filter(is_active=True)
    serializer_class = TemplateCategorySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'
    ordering = ['sort_order', 'name']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            if not self.request.user.is_superuser:
                return TemplateCategory.objects.none()
            return TemplateCategory.objects.all()
        return qs

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({'code': 4000, 'msg': '仅超级管理员可管理分类', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({'code': 4000, 'msg': '仅超级管理员可管理分类', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({'code': 4000, 'msg': '仅超级管理员可管理分类', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
