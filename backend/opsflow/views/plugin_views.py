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
        """返回所有已注册插件（按 code 聚合版本，不含 form_schema）"""
        qs = self.get_queryset().filter(is_active=True)
        # 按 code 聚合版本
        version_map = {}
        for p in qs:
            if p.code not in version_map:
                version_map[p.code] = {
                    "code": p.code,
                    "name": p.name,
                    "group": p.group,
                    "description": p.description,
                    "risk_level": p.risk_level,
                    "versions": [],
                }
            version_map[p.code]["versions"].append(p.version)
        data = list(version_map.values())
        return Response({"code": 2000, "msg": "success", "data": data})

    def retrieve(self, request, *args, **kwargs):
        """返回单个插件详情 + 完整 form_schema（支持 ?version= 参数）"""
        code = kwargs.get('code')
        version = request.query_params.get('version')
        qs = self.get_queryset().filter(code=code)
        if version:
            qs = qs.filter(version=version)
        if not qs.exists():
            return Response(
                {"code": 4000, "msg": "插件不存在", "data": None},
                status=status.HTTP_404_NOT_FOUND,
            )
        # 取最后一次创建的版本作为主数据
        primary = qs.last()
        all_versions = list(qs.values_list('version', flat=True))
        data = {
            "code": primary.code,
            "name": primary.name,
            "group": primary.group,
            "version": primary.version,
            "description": primary.description,
            "risk_level": primary.risk_level,
            "form_schema": primary.form_schema,
            "output_schema": primary.output_schema,
            "versions": all_versions,
        }
        return Response({"code": 2000, "msg": "success", "data": data})

    @action(detail=False, methods=['get'])
    def groups(self, request):
        """返回分组树结构（按 code 聚合，含版本列表）"""
        qs = self.get_queryset().filter(is_active=True)
        group_map = {}
        seen = set()
        for p in qs:
            key = (p.group, p.code)
            if key not in seen:
                seen.add(key)
                group_map.setdefault(p.group, []).append({
                    "code": p.code,
                    "name": p.name,
                    "version": p.version,
                    "versions": [],
                    "risk_level": p.risk_level,
                    "phase": p.phase,
                    "phase_label": dict(PluginMeta.PHASE_CHOICES).get(p.phase, ''),
                })
            # 添加到版本列表
            for entry in group_map.get(p.group, []):
                if entry["code"] == p.code and p.version not in entry["versions"]:
                    entry["versions"].append(p.version)
        return Response({"code": 2000, "msg": "success", "data": group_map})

    @action(detail=False, methods=['get'])
    def variable_types(self, request):
        """返回所有注册的变量类型，供前端变量编辑器使用"""
        try:
            from opsflow.core.variable_registry import VariableLibrary
            types = VariableLibrary.get_all_variables()
            data = [
                {"code": code, "name": info.get("name", code),
                 "type": info.get("type", "general"),
                 "tag": info.get("tag", "")}
                for code, info in types.items()
            ]
            return Response({"code": 2000, "msg": "success", "data": data})
        except Exception as e:
            return Response({"code": 4000, "msg": str(e), "data": []})
