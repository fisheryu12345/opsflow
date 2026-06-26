"""Template Variable — 全局变量/变量浏览器/变量提升端点 Mixin"""

from rest_framework.decorators import action
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from rest_framework.response import Response
from rest_framework import status

from opsflow.core.variable_resolver import normalize_global_vars, count_variable_references
from opsflow.plugins.registry import get_plugin


class TemplateVariableMixin:
    """全局变量系统端点混入"""

    @action(detail=True, methods=['get', 'post'])
    def hook_variables(self, request, pk=None):
        """获取或更新可提升的全局变量配置"""
        template = self.get_object()
        if request.method == 'GET':
            return DetailResponse(data=template.hook_variables or {})
        hook_vars = request.data.get('hook_variables', request.data)
        template.hook_variables = hook_vars
        template.save(update_fields=['hook_variables'])
        return DetailResponse(data=template.hook_variables, msg='Hook variables updated')

    @action(detail=True, methods=['get', 'post', 'patch'], url_path='global-variables')
    def global_variables(self, request, pk=None):
        """全局变量 CRUD

        GET:  返回所有全局变量（规范化结构）
        POST: 批量替换所有全局变量
        PATCH: 部分更新（合并现有变量）
        """
        template = self.get_object()

        if request.method == 'GET':
            normalized = normalize_global_vars(template.global_vars)
            # 附加引用计数
            tree = template.pipeline_tree or {}
            result = {}
            for key, entry in normalized.items():
                entry["reference_count"] = count_variable_references(tree, key)
                result[key] = entry
            return DetailResponse(data=result)

        if request.method == 'POST':
            template.global_vars = request.data.get('global_vars', {})
            template.save(update_fields=['global_vars'])
            normalized = normalize_global_vars(template.global_vars)
            return DetailResponse(data=normalized, msg='Global variables updated')

        # PATCH — 合并更新（不执行 cleanup，PATCH 是增量操作不应删除已有变量）
        updates = request.data.get('global_vars', {})
        current = dict(template.global_vars or {})
        for key, val in updates.items():
            if isinstance(val, dict) and "value" in val:
                current[key] = val
            else:
                # 扁平格式 → 转为结构化
                existing = current.get(key, {})
                if isinstance(existing, dict) and "value" in existing:
                    existing["value"] = val
                    current[key] = existing
                else:
                    current[key] = val
        template.global_vars = current
        template.save(update_fields=['global_vars'])
        normalized = normalize_global_vars(template.global_vars)
        return DetailResponse(data=normalized, msg='全局变量已更新')

    @action(detail=True, methods=['get'], url_path='variable-browser')
    def variable_browser(self, request, pk=None):
        """返回所有可引用变量（全局变量 + 节点输出），供前端自动补全"""
        template = self.get_object()

        # 1. 全局变量
        normalized = normalize_global_vars(template.global_vars)
        tree = template.pipeline_tree or {}
        global_vars = [
            {"key": k, "type": v["type"], "source": "global",
             "description": v.get("description", ""),
             "value": v["value"],
             "reference_count": count_variable_references(tree, k)}
            for k, v in normalized.items()
        ]

        # 2. 节点输出（从插件 output_schema 提取）
        node_outputs = []
        for node in tree.get('nodes', []):
            nid = node.get('id', '')
            label = node.get('label', nid)
            node_type = node.get('node_type', '')
            plugin_code = node.get('atom_type') or node.get('plugin_code', '')
            if plugin_code:
                cls = get_plugin(plugin_code)
                if cls:
                    schema = cls.get_output_schema() or []
                    for field in schema:
                        field_key = field.get('tag_code', field.get('key', field.get('name', '')))
                        if field_key:
                            node_outputs.append({
                                "key": f"{nid}.{field_key}",
                                "node_id": nid,
                                "node_label": label,
                                "source": "node_output",
                                "description": field.get('name', field_key),
                            })
                    # 未定义 output_schema 的插件 → 提供通用 stdout/stderr 字段
                    if not any(field.get('name') or field.get('key') or field.get('tag_code') for field in schema):
                        existing_keys = {o['key'] for o in node_outputs if o['node_id'] == nid}
                        for fallback in ('stdout', 'stderr'):
                            fk = f"{nid}.{fallback}"
                            if fk not in existing_keys:
                                node_outputs.append({
                                    "key": fk, "node_id": nid, "node_label": label,
                                    "source": "node_output",
                                    "description": f"Standard {'output' if fallback == 'stdout' else 'error'}",
                                })
            # 标准 _result 输出（所有 atom 节点）
            if node_type in ('atom', '', None):
                node_outputs.append({
                    "key": f"{nid}._result",
                    "node_id": nid,
                    "node_label": label,
                    "source": "node_output",
                    "description": "Execution result (True/False)",
                })

        # 3. 项目环境变量（项目级共享变量）
        from opsflow.core.variable_resolver import resolve_project_variables
        if template.project_id:
            raw = resolve_project_variables(template.project_id)
            project_vars = [
                {"key": k, "source": "project_env",
                 "description": "", "value": v}
                for k, v in raw.items()
            ]
        else:
            project_vars = []

        return DetailResponse(data={
            "global_variables": global_vars,
            "node_outputs": node_outputs,
            "project_variables": project_vars,
        })

    @action(detail=True, methods=['post'], url_path='hook-variable')
    def hook_variable(self, request, pk=None):
        """将节点参数提升为全局变量

        promote_type="output" (默认): 节点输出提权, source_type=node_output, 运行时懒解析
        promote_type="input":  节点输入提权, source_type=manual, 直接存储值和元数据
        """
        template = self.get_object()
        var_key = request.data.get('var_key', '')
        node_id = request.data.get('node_id', '')
        tag_code = request.data.get('tag_code', '')
        var_type = request.data.get('var_type', 'input')
        description = request.data.get('description', '')
        promote_type = request.data.get('promote_type', 'output')

        if not var_key:
            return ErrorResponse(msg='var_key is required', data=None, code=4000, status=status.HTTP_400_BAD_REQUEST)
        if promote_type == 'output' and not node_id:
            return ErrorResponse(msg='node_id is required for output promotion', data=None, code=4000, status=status.HTTP_400_BAD_REQUEST)

        current = normalize_global_vars(template.global_vars)

        if promote_type == 'input':
            # 输入提权: 直接存储值, source_type=manual
            current[var_key] = {
                "value": request.data.get('value', ''),
                "type": var_type,
                "meta": request.data.get("meta", {}),
                "show_type": True,
                "description": description,
                "source_type": "manual",
                "source_info": None,
                "validation": [],
            }
        else:
            # 输出提权: 运行时懒解析, source_type=node_output
            current[var_key] = {
                "value": "",
                "type": var_type,
                "meta": request.data.get("meta", {}),
                "show_type": True,
                "description": description,
                "source_type": "node_output",
                "source_info": {
                    "node_id": node_id,
                    "tag_code": tag_code,
                },
                "validation": [],
            }

        # 同步更新 hook_variables（向后兼容）
        hook_vars = dict(template.hook_variables or {})
        hook_vars[var_key] = current[var_key]
        template.hook_variables = hook_vars

        template.global_vars = current
        template.save(update_fields=['global_vars', 'hook_variables'])
        return DetailResponse(data=current[var_key], msg='Variable promoted to global')

    @action(detail=True, methods=['post'], url_path='unhook-variable')
    def unhook_variable(self, request, pk=None):
        """移除变量与节点的关联（降级为手动变量）"""
        template = self.get_object()
        var_key = request.data.get('var_key', '')

        current = normalize_global_vars(template.global_vars)

        if var_key not in current:
            return ErrorResponse(msg=f'Variable {var_key} not found', data=None, code=4000, status=status.HTTP_404_NOT_FOUND)

        # 移除 source_info 但保留变量
        current[var_key].update({
            "source_type": "manual",
            "source_info": None,
        })
        template.global_vars = current
        template.save(update_fields=['global_vars'])
        return DetailResponse(data=current[var_key], msg='Variable unhooked')
