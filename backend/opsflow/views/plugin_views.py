"""标准插件 API — 对接前端 RenderForm 的插件元数据和表单配置"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import PluginMeta


class PluginViewSet(viewsets.ReadOnlyModelViewSet):
    """标准插件只读接口 — 提供插件列表、详情、分组树"""
    queryset = PluginMeta.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'

    def list(self, request, *args, **kwargs):
        """返回所有已注册插件（摘要信息，不含 form_schema）"""
        qs = self.get_queryset()
        data = [
            {
                "code": p.code,
                "name": p.name,
                "group": p.group,
                "version": p.version,
                "description": p.description,
                "risk_level": p.risk_level,
            }
            for p in qs
        ]
        return Response({"code": 2000, "msg": "success", "data": data})

    def retrieve(self, request, *args, **kwargs):
        """返回单个插件详情 + 完整 form_schema"""
        try:
            plugin = self.get_object()
        except Exception:
            return Response(
                {"code": 4000, "msg": "插件不存在", "data": None},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = {
            "code": plugin.code,
            "name": plugin.name,
            "group": plugin.group,
            "version": plugin.version,
            "description": plugin.description,
            "risk_level": plugin.risk_level,
            "form_schema": plugin.form_schema,
            "output_schema": plugin.output_schema,
        }
        return Response({"code": 2000, "msg": "success", "data": data})

    @action(detail=False, methods=['get'])
    def groups(self, request):
        """返回分组树结构"""
        qs = self.get_queryset()
        group_map = {}
        for p in qs:
            group_map.setdefault(p.group, []).append({
                "code": p.code,
                "name": p.name,
                "version": p.version,
            })
        return Response({"code": 2000, "msg": "success", "data": group_map})
