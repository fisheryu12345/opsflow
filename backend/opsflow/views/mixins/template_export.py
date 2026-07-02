"""Template Export/Import — 导出/导入/分类端点 Mixin"""

from datetime import datetime

from rest_framework.decorators import action
from common.utils.json_response import DetailResponse, ErrorResponse
from rest_framework.response import Response

from opsflow.models import FlowTemplate
from opsflow.serializers import FlowTemplateSerializer


class TemplateExportImportMixin:
    """导出、导入、分类端点混入"""

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """导出模板为 JSON 包（含版本历史）"""
        template = self.get_object()
        versions = template.versions.values(
            'version', 'pipeline_tree', 'global_vars',
            'version_note', 'created_at',
        )
        bundle = {
            "opsflow_version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "template": {
                "name": template.name,
                "pipeline_tree": template.pipeline_tree,
                "global_vars": template.global_vars,
                "category": template.category or "",
                "tags": template.tags or [],
                "description": template.description or "",
            },
            "versions": list(versions),
        }
        return DetailResponse(data=bundle)

    @action(detail=False, methods=['post'])
    def import_template(self, request):
        """导入模板 JSON（创建草稿）"""
        from django.utils import timezone
        data = request.data.get('data') or request.data
        td = data.get('template', data)
        name = td.get('name', 'Imported Template')
        if FlowTemplate.objects.filter(name=name).exists():
            name = f"{name} (imported {timezone.now().strftime('%Y%m%d_%H%M%S')})"
        project_kwargs = self.resolve_project_kwargs(request)
        template = FlowTemplate.objects.create(
            name=name,
            pipeline_tree=td.get('pipeline_tree', {}),
            global_vars=td.get('global_vars', {}),
            category=td.get('category', ''),
            tags=td.get('tags', []),
            description=td.get('description', ''),
            is_draft=True,
            created_by=request.user,
            **project_kwargs,
        )
        return DetailResponse(data=FlowTemplateSerializer(template).data, msg=f'Imported: {template.name}')

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """返回所有已使用的类别列表"""
        cats = FlowTemplate.objects.values('category').distinct().order_by('category')
        data = [c['category'] for c in cats if c['category']]
        return DetailResponse(data=data)
