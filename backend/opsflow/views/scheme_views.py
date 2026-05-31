"""ExecutionScheme ViewSet — 执行方案 CRUD（嵌套于模板下）"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from opsflow.models import FlowTemplate, ExecutionScheme
from opsflow.serializers import ExecutionSchemeSerializer


class ExecutionSchemeViewSet(viewsets.ModelViewSet):
    """执行方案 CRUD — 预定义节点排除集 + 变量覆盖"""
    queryset = ExecutionScheme.objects.all()
    serializer_class = ExecutionSchemeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        template_id = self.kwargs.get('template_pk')
        if template_id:
            qs = qs.filter(template_id=template_id)
        return qs

    def perform_create(self, serializer):
        template_id = self.kwargs.get('template_pk')
        if template_id:
            try:
                template = FlowTemplate.objects.get(id=template_id)
            except FlowTemplate.DoesNotExist:
                return Response(
                    {'code': 4000, 'msg': 'Template not found', 'data': None},
                    status=status.HTTP_404_NOT_FOUND,
                )
            # 如设为默认方案，先清除其他方案的 is_default
            if serializer.validated_data.get('is_default'):
                ExecutionScheme.objects.filter(template=template, is_default=True).update(is_default=False)
            serializer.save(template=template, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # 如设为默认方案，先清除其他方案的 is_default
        if serializer.validated_data.get('is_default'):
            instance = self.get_object()
            ExecutionScheme.objects.filter(template=instance.template, is_default=True).exclude(
                id=instance.id
            ).update(is_default=False)
        serializer.save()
