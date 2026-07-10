"""标准插件 API — 对接前端 RenderForm 的插件元数据和表单配置"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from common.utils.json_response import DetailResponse, ErrorResponse
from common.utils.language import get_request_lang

from opsflow.models import PluginMeta
from opsflow.plugins.registry import refresh_plugins, loader, get_plugin


def _apply_project_visibility(qs, project_id):
    """按项目可见性过滤插件列表

    - project_id 为 None 或 0 → 不过滤
    - allowed_projects=[] → 所有项目可见（默认）
    - allowed_projects=[1,2,3] → 仅项目 1/2/3 可见
    """
    if not project_id:
        return qs
    from django.db.models import Q
    return qs.filter(
        Q(allowed_projects=[]) | Q(allowed_projects__contains=project_id)
    )


class PluginViewSet(viewsets.ReadOnlyModelViewSet):
    """标准插件只读接口 — 提供插件列表、详情、分组树"""
    queryset = PluginMeta.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'

    def get_project_filtered_queryset(self):
        """获取按 project_id 过滤后的 queryset"""
        qs = self.get_queryset().filter(is_active=True)
        project_id = self.request.query_params.get('project_id')
        if project_id:
            try:
                qs = _apply_project_visibility(qs, int(project_id))
            except (ValueError, TypeError):
                pass
        return qs

    def list(self, request, *args, **kwargs):
        """返回所有已注册插件（按 code 聚合版本，不含 form_schema）
        GET /api/opsflow/plugins/?project_id=1 → 仅返回项目1可见的插件
        """
        qs = self.get_project_filtered_queryset()
        version_map = {}
        for p in qs:
            if p.code not in version_map:
                version_map[p.code] = {
                    "code": p.code,
                    "name": p.name,
                    "name_en": p.name_en or "",
                    "group": p.group,
                    "description": p.description,
                    "description_en": p.description_en or "",
                    "risk_level": p.risk_level,
                    "icon": p.icon or "",
                    "color": p.color or "",
                    "versions": [],
                }
            version_map[p.code]["versions"].append(p.version)
        return DetailResponse(data=list(version_map.values()))

    def retrieve(self, request, *args, **kwargs):
        """返回单个插件详情 + 完整 form_schema（支持 ?version= 参数）
        始终返回 name 和 name_en，前端根据 locale 选择显示。
        """
        code = kwargs.get('code')
        version = request.query_params.get('version')
        qs = self.get_queryset().filter(code=code)
        if version:
            qs = qs.filter(version=version)
        if not qs.exists():
            return ErrorResponse(msg="Plugin not found", data=None, code=4000, status=status.HTTP_404_NOT_FOUND)
        primary = qs.last()
        all_versions = list(qs.values_list('version', flat=True))
        # 从插件类读取控制字段（不在 DB 中存储，从注册表动态获取）
        plugin_cls = get_plugin(primary.code)
        show_execution_controls = plugin_cls.show_execution_controls if plugin_cls and hasattr(plugin_cls, 'show_execution_controls') else True
        show_loop_config = plugin_cls.show_loop_config if plugin_cls and hasattr(plugin_cls, 'show_loop_config') else True
        return DetailResponse(data={
            "show_execution_controls": show_execution_controls,
            "show_loop_config": show_loop_config,
            "code": primary.code,
            "name": primary.name,
            "name_en": primary.name_en or "",
            "group": primary.group,
            "version": primary.version,
            "description": primary.description,
            "description_en": primary.description_en or "",
            "risk_level": primary.risk_level,
            "icon": primary.icon or "",
            "color": primary.color or "",
            "form_schema": primary.form_schema,
            "output_schema": primary.output_schema,
            "versions": all_versions,
        })

    @action(detail=False, methods=['get'])
    def groups(self, request):
        """返回分组树结构（按 code 聚合，含版本列表）
        GET /api/opsflow/plugins/groups/?project_id=1 → 仅返回项目1可见的插件分组
        """
        qs = self.get_project_filtered_queryset()
        group_map = {}
        seen = set()
        for p in qs:
            key = (p.group, p.code)
            if key not in seen:
                seen.add(key)
                group_map.setdefault(p.group, []).append({
                    "code": p.code,
                    "name": p.name,
                    "name_en": p.name_en or "",
                    "description": p.description,
                    "description_en": p.description_en or "",
                    "version": p.version,
                    "versions": [],
                    "risk_level": p.risk_level,
                    "icon": p.icon or "",
                    "color": p.color or "",
                    "phase": p.phase,
                    "phase_label": dict(PluginMeta.PHASE_CHOICES).get(p.phase, ''),
                })
            for entry in group_map.get(p.group, []):
                if entry["code"] == p.code and p.version not in entry["versions"]:
                    entry["versions"].append(p.version)
        return DetailResponse(data=group_map)

    @action(detail=False, methods=['post'])
    def reload(self, request):
        """扫描插件目录，注册新插件，同步 DB

        POST /api/opsflow/plugins/reload/
        Response: {"changed": 2, "revision": 42}
        """
        count = refresh_plugins()
        return DetailResponse(data={
            "changed": count,
            "revision": loader.get_revision(),
        })

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
            return DetailResponse(data=data)
        except Exception as e:
            return ErrorResponse(msg=str(e), data=[], code=4000)

    # ── 项目级可见性管理 ──────────────────────────────────────────

    @action(detail=True, methods=['get', 'post'], url_path='visibility')
    def visibility(self, request, code=None):
        """管理单个插件的项目可见性

        GET  /plugins/{code}/visibility/ → 查看当前可见性配置
        POST /plugins/{code}/visibility/ → 更新可见性
            Body: {"project_ids": [1, 2, 3]} 或 {"project_ids": []}（对所有项目可见）
        """
        try:
            plugin = PluginMeta.objects.filter(code=code).last()
        except PluginMeta.DoesNotExist:
            return ErrorResponse(msg="Plugin not found", data=None, code=4000, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            versions = PluginMeta.objects.filter(code=code)
            allowed = set()
            for v in versions:
                allowed.update(v.allowed_projects or [])
            is_en = get_request_lang(request) == 'en'
            name = (plugin.name_en or plugin.name) if is_en else plugin.name
            return DetailResponse(data={
                    "code": code,
                    "name": name,
                    "group": plugin.group,
                    "allowed_projects": sorted(allowed),
                    "restricted": len(allowed) > 0,
                })

        # POST: 更新可见性 — 同步到该插件所有版本
        project_ids = request.data.get('project_ids', [])
        if not isinstance(project_ids, list):
            return ErrorResponse(msg="project_ids must be a list", data=None, code=4000, status=status.HTTP_400_BAD_REQUEST)

        updated = PluginMeta.objects.filter(code=code).update(allowed_projects=project_ids)
        return DetailResponse(data={"code": code, "allowed_projects": project_ids, "updated_versions": updated})

    @action(detail=False, methods=['get'], url_path='visibility-list')
    def visibility_list(self, request):
        """返回所有插件的可见性配置（供管理面板使用）

        GET /plugins/visibility-list/ → [
            {code, name, group, allowed_projects, restricted, template_count}
        ]
        """
        qs = PluginMeta.objects.filter(is_active=True)
        seen = set()
        data = []
        for p in qs:
            if p.code not in seen:
                seen.add(p.code)
                data.append({
                    "code": p.code,
                    "name": p.name,
                    "name_en": p.name_en or "",
                    "group": p.group,
                    "description": p.description,
                    "description_en": p.description_en or "",
                    "risk_level": p.risk_level,
                    "icon": p.icon or "",
                    "color": p.color or "",
                    "allowed_projects": p.allowed_projects or [],
                    "restricted": len(p.allowed_projects or []) > 0,
                })
        data.sort(key=lambda x: (x["group"], x["name"]))
        return DetailResponse(data=data)

    @action(detail=False, methods=['post'], url_path='batch-visibility')
    def batch_visibility(self, request):
        """批量更新插件可见性

        POST /plugins/batch-visibility/
        Body: {"plugins": [{"code": "disk_check", "project_ids": [1,2]}, ...]}
        """
        plugins = request.data.get('plugins', [])
        if not isinstance(plugins, list):
            return ErrorResponse(msg="plugins must be a list", data=None, code=4000, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for item in plugins:
            code = item.get('code')
            project_ids = item.get('project_ids', [])
            if not code or not isinstance(project_ids, list):
                continue
            updated = PluginMeta.objects.filter(code=code).update(allowed_projects=project_ids)
            results.append({"code": code, "allowed_projects": project_ids, "updated_versions": updated})

        return DetailResponse(data=results)
