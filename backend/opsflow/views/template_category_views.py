"""模板分类 API"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import TemplateCategory
from opsflow.serializers import TemplateCategorySerializer
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({'code': 4000, 'msg': 'Only superusers can manage categories', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg="创建成功")

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({'code': 4000, 'msg': 'Only superusers can manage categories', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return DetailResponse(data=serializer.data, msg="更新成功")

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({'code': 4000, 'msg': 'Only superusers can manage categories', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})
