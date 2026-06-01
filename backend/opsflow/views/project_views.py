"""OpsProject ViewSet — 项目 CRUD + 用户默认项目"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import OpsProject
from dvadmin.utils.json_response import DetailResponse, SuccessResponse


class OpsProjectViewSet(viewsets.ModelViewSet):
    """项目管理 CRUD"""
    queryset = OpsProject.objects.all()
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'description']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = [
            {
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'is_active': p.is_active,
                'owner_name': p.owner.username if p.owner else None,
                'template_count': p.templates.count(),
                'execution_count': p.executions.count(),
                'created_at': p.created_at.isoformat(),
            }
            for p in queryset
        ]
        return SuccessResponse(data=data)

    def retrieve(self, request, *args, **kwargs):
        p = self.get_object()
        data = {
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'is_active': p.is_active,
            'owner_name': p.owner.username if p.owner else None,
            'created_at': p.created_at.isoformat(),
        }
        return DetailResponse(data=data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(owner=request.user)
        return DetailResponse(data=serializer.data, msg='Project created')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return DetailResponse(data=serializer.data, msg='success')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.templates.exists():
            return Response(
                {'code': 4000, 'msg': 'Project has templates, delete them first', 'data': None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})
