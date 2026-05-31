import re
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import FlowTemplate
from opsflow.serializers import FlowTemplateSerializer
from opsflow.core.llm_service import generate_pipeline, analyze_pipeline, refine_pipeline
from opsflow.core.layout import compute_layout
from opsflow.core.safety_guard import validate_pipeline
from opsflow.core.bamboo_builder import validate_bamboo_compatibility
from dvadmin.utils.json_response import DetailResponse, SuccessResponse

logger = logging.getLogger(__name__)


class FlowTemplateViewSet(viewsets.ModelViewSet):
    queryset = FlowTemplate.objects.all()
    serializer_class = FlowTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_draft', 'created_by', 'category']
    search_fields = ['name']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return SuccessResponse(data=serializer.data, page=int(request.query_params.get('page', 1)),
                                   limit=self.paginator.get_page_size(request) if hasattr(self.paginator, 'get_page_size') else 10,
                                   total=self.paginator.page.paginator.count if hasattr(self.paginator, 'page') else queryset.count())
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, total=queryset.count())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg='success')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(instance.pipeline_tree or {}, instance.global_vars or {})
        instance.global_vars = cleaned
        instance.save(update_fields=['global_vars'])
        # ── 结束 ──
        return DetailResponse(data=serializer.data, msg='success')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.created_by and instance.created_by != request.user:
            return Response({'code': 4000, 'msg': 'Only the creator can delete this template', 'data': None},
                            status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response({'code': 2000, 'msg': 'success', 'data': None})

    @action(detail=False, methods=['post'])
    def create_from_ai(self, request):
        """接收自然语言描述，调用 DeepSeek 生成 Pipeline Tree，保存为草稿"""
        nl_input = request.data.get('input', '')
        target_hosts = request.data.get('target_hosts', [])
        global_vars = request.data.get('global_vars', {})

        if not nl_input:
            return Response({'code': 4000, 'msg': 'input is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            pipeline = generate_pipeline(nl_input, target_hosts)

            # AI 报告无法完成的请求
            errors = pipeline.get('_errors') or pipeline.get('_unsupported')
            if errors:
                return Response({'code': 4000, 'msg': '好的，我理解您想要这个功能，但目前系统暂不支持，建议换个方式实现',
                                 'data': {'pipeline_tree': pipeline}},
                                status=status.HTTP_400_BAD_REQUEST)

            # AI 不应生成 shell 原子 — 说明用不存在的功能做了 fallback
            if any(n.get('atom_type') == 'shell' for n in pipeline.get('nodes', [])):
                return Response({'code': 4000, 'msg': '好的，我理解您想要这个功能，但目前系统暂不支持，建议换个方式实现',
                                 'data': {'pipeline_tree': pipeline}},
                                status=status.HTTP_400_BAD_REQUEST)

            # 检查跨平台误用：用户说 VM/虚拟机 但 AI 用了其他平台的原子
            nl_lower = nl_input.lower()
            is_vm_request = any(kw in nl_lower for kw in ['vm', '虚拟机', '虚机', 'esxi'])
            for node in pipeline.get('nodes', []):
                atom = node.get('atom_type', '')
                if is_vm_request and atom.startswith('netapp_'):
                    return Response({'code': 4000, 'msg': '好的，我理解您想要这个功能，但目前系统暂不支持，建议换个方式实现',
                                     'data': {'pipeline_tree': pipeline}},
                                    status=status.HTTP_400_BAD_REQUEST)

            validation = validate_pipeline(pipeline)
            bamboo_check = validate_bamboo_compatibility(pipeline)

            # 拒绝保存含有未知原子等严重错误的流程
            if not validation.get('valid'):
                # 检测未知原子类型 → 友善提示
                unknown_atoms = set()
                for err in validation.get('errors', []):
                    m = re.search(r"未知原子类型 '(\w+)'", err)
                    if m:
                        unknown_atoms.add(m.group(1))
                if unknown_atoms:
                    msg = '好的，我理解您的意思，但目前系统还不支持这个操作，咱先试试其他功能吧'
                else:
                    msg = '流程有一些问题需要调整，请检查后重试'
                return Response({
                    'code': 4000, 'msg': msg,
                    'data': {'validation': validation, 'pipeline_tree': pipeline}
                }, status=status.HTTP_400_BAD_REQUEST)

            template = FlowTemplate.objects.create(
                name=f"AI: {nl_input[:50]}",
                pipeline_tree=pipeline,
                target_hosts=target_hosts,
                global_vars=global_vars,
                ai_original_tree=pipeline.copy(),
                is_draft=True,
                created_by=request.user,
            )
            return Response({
                'code': 2000, 'msg': 'success',
                'data': {
                    'template': FlowTemplateSerializer(template).data,
                    'validation': validation,
                    'bamboo_check': bamboo_check,
                }
            })
        except Exception as e:
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def confirm_draft(self, request, pk=None):
        """用户确认草稿，发布为 V1"""
        template = self.get_object()
        if not template.is_draft:
            return Response({'code': 4000, 'msg': '不是草稿状态', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        safety = validate_pipeline(template.pipeline_tree)
        if not safety.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程存在安全风险，请检查后再确认',
                'data': {'validation': safety}
            }, status=status.HTTP_400_BAD_REQUEST)

        bamboo_check = validate_bamboo_compatibility(template.pipeline_tree)
        if not bamboo_check.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程不兼容 bamboo-engine',
                'data': {'bamboo_check': bamboo_check}
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
        template.global_vars = cleaned
        # ── 结束 ──

        template.is_draft = False
        version_note = request.data.get('version_note', '')
        template.publish_snapshot(user=request.user, version_note=version_note)
        return Response({'code': 2000, 'msg': f'已发布 V{template.version - 1}', 'data': FlowTemplateSerializer(template).data})

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """已发布模板发布新版本"""
        template = self.get_object()
        if template.is_draft:
            return Response({'code': 4000, 'msg': '草稿模板请使用 confirm_draft', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        safety = validate_pipeline(template.pipeline_tree)
        if not safety.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程存在安全风险',
                'data': {'validation': safety}
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
        template.global_vars = cleaned
        template.save(update_fields=['global_vars'])
        # ── 结束 ──

        version_note = request.data.get('version_note', '')
        template.publish_snapshot(user=request.user, version_note=version_note)
        return Response({'code': 2000, 'msg': f'已发布 V{template.version - 1}', 'data': FlowTemplateSerializer(template).data})

    @action(detail=True, methods=['get'], url_path='versions')
    def list_versions(self, request, pk=None):
        """返回版本历史列表"""
        template = self.get_object()
        from opsflow.serializers import TemplateVersionSerializer
        qs = template.versions.all()
        serializer = TemplateVersionSerializer(qs, many=True)
        return Response({'code': 2000, 'msg': 'success', 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """回滚到指定版本"""
        template = self.get_object()
        version_id = request.data.get('version')
        if not version_id:
            return Response({'code': 4000, 'msg': 'version is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            target = template.versions.get(version=version_id)
        except Exception:
            return Response({'code': 4000, 'msg': f'版本 V{version_id} 不存在', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)
        template.pipeline_tree = target.pipeline_tree
        template.target_hosts = target.target_hosts
        template.global_vars = target.global_vars
        template.is_draft = False
        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
        template.global_vars = cleaned
        # ── 结束 ──
        template.save()
        return Response({'code': 2000, 'msg': f'已回滚到 V{version_id}', 'data': FlowTemplateSerializer(template).data})

    @action(detail=True, methods=['post'])
    def version_diff(self, request, pk=None):
        """对比两个版本的 pipeline_tree — 使用 DeepDiff"""
        import json
        from deepdiff import DeepDiff
        template = self.get_object()
        v1 = request.data.get('v1')
        v2 = request.data.get('v2')
        if not v1 or not v2:
            return Response({'code': 4000, 'msg': '需要指定 v1 和 v2 版本号', 'data': None})
        try:
            version1 = template.versions.get(version=v1)
            version2 = template.versions.get(version=v2)
        except Exception:
            return Response({'code': 4000, 'msg': '版本号不存在', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)
        diff = DeepDiff(version1.pipeline_tree, version2.pipeline_tree, ignore_order=True)
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {'v1': v1, 'v2': v2, 'diff': json.loads(diff.to_json())}
        })

    @action(detail=True, methods=['get'])
    def diff_draft(self, request, pk=None):
        """对比当前草稿 vs 已发布版本（snapshot）"""
        import json
        from deepdiff import DeepDiff
        template = self.get_object()
        published = template.snapshot or {}
        published_tree = published.get('pipeline_tree')
        if not published_tree:
            return Response({'code': 4000, 'msg': '尚无已发布版本', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        diff = DeepDiff(published_tree, template.pipeline_tree, ignore_order=True)
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'published_version': template.version - 1,
                'diff': json.loads(diff.to_json()),
            }
        })

    @action(detail=False, methods=['post'])
    def ai_layout(self, request):
        """布局优化 — 使用确定性 Sugiyama 分层布局引擎"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return Response({'code': 4000, 'msg': 'nodes is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            positions = compute_layout(nodes, edges)
            return Response({'code': 2000, 'msg': 'success', 'data': {'positions': positions}})
        except Exception as e:
            logger.exception("Layout failed")
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def diff(self, request, pk=None):
        """返回 AI 原稿 vs 当前修改，供前端 Diff 弹窗使用"""
        template = self.get_object()
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'ai_original': template.ai_original_tree,
                'current': template.pipeline_tree,
            }
        })

    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """AI 分析流程：描述流程目的、步骤及潜在风险"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return Response({'code': 4000, 'msg': 'nodes is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            result = analyze_pipeline(nodes, edges)
            return Response({'code': 2000, 'msg': 'success', 'data': result})
        except Exception as e:
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def refine(self, request):
        """多轮对话：根据用户新指令修改现有 Pipeline Tree"""
        nl_input = request.data.get('input', '')
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        target_hosts = request.data.get('target_hosts', [])

        if not nl_input:
            return Response({'code': 4000, 'msg': 'input is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            pipeline = refine_pipeline(nl_input, nodes, edges, target_hosts)

            # AI 报告无法完成的请求
            errors = pipeline.get('_errors') or pipeline.get('_unsupported')
            if errors:
                return Response({'code': 4000, 'msg': '好的，我理解您想要这个功能，但目前系统暂不支持，建议换个方式实现',
                                 'data': {'pipeline_tree': pipeline}},
                                status=status.HTTP_400_BAD_REQUEST)

            # AI 不应生成 shell 原子 — 说明用不存在的功能做了 fallback
            if any(n.get('atom_type') == 'shell' for n in pipeline.get('nodes', [])):
                return Response({'code': 4000, 'msg': '好的，我理解您想要这个功能，但目前系统暂不支持，建议换个方式实现',
                                 'data': {'pipeline_tree': pipeline}},
                                status=status.HTTP_400_BAD_REQUEST)

            # 检查跨平台误用：用户说 VM/虚拟机 但 AI 用了其他平台的原子
            nl_lower = nl_input.lower()
            is_vm_request = any(kw in nl_lower for kw in ['vm', '虚拟机', '虚机', 'esxi'])
            for node in pipeline.get('nodes', []):
                atom = node.get('atom_type', '')
                if is_vm_request and atom.startswith('netapp_'):
                    return Response({'code': 4000, 'msg': '好的，我理解您想要这个功能，但目前系统暂不支持，建议换个方式实现',
                                     'data': {'pipeline_tree': pipeline}},
                                    status=status.HTTP_400_BAD_REQUEST)

            validation = validate_pipeline(pipeline)
            bamboo_check = validate_bamboo_compatibility(pipeline)

            # 拒绝返回含有未知原子等严重错误的流程
            if not validation.get('valid'):
                unknown_atoms = set()
                for err in validation.get('errors', []):
                    m = re.search(r"未知原子类型 '(\w+)'", err)
                    if m:
                        unknown_atoms.add(m.group(1))
                if unknown_atoms:
                    msg = '好的，我理解您的意思，但目前系统还不支持这个操作，咱先试试其他功能吧'
                else:
                    msg = '流程有一些问题需要调整，请检查后重试'
                return Response({
                    'code': 4000, 'msg': msg,
                    'data': {'validation': validation, 'pipeline_tree': pipeline}
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'code': 2000, 'msg': 'success',
                'data': {
                    'pipeline_tree': pipeline,
                    'validation': validation,
                    'bamboo_check': bamboo_check,
                }
            })
        except Exception as e:
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # -- 导出/导入/分类/变量作用域 ------------------------------------

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """导出模板为 JSON 包（含版本历史）"""
        from datetime import datetime
        template = self.get_object()
        versions = template.versions.values(
            'version', 'pipeline_tree', 'target_hosts', 'global_vars',
            'version_note', 'created_at',
        )
        bundle = {
            "opsflow_version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "template": {
                "name": template.name,
                "pipeline_tree": template.pipeline_tree,
                "target_hosts": template.target_hosts,
                "global_vars": template.global_vars,
                "category": template.category or "",
                "tags": template.tags or [],
                "description": template.description or "",
            },
            "versions": list(versions),
        }
        return Response({'code': 2000, 'msg': 'success', 'data': bundle})

    @action(detail=False, methods=['post'])
    def import_template(self, request):
        """导入模板 JSON（创建草稿）"""
        from django.utils import timezone
        data = request.data.get('data') or request.data
        td = data.get('template', data)
        name = td.get('name', 'Imported Template')
        if FlowTemplate.objects.filter(name=name).exists():
            name = f"{name} (imported {timezone.now().strftime('%Y%m%d_%H%M%S')})"
        template = FlowTemplate.objects.create(
            name=name,
            pipeline_tree=td.get('pipeline_tree', {}),
            target_hosts=td.get('target_hosts', []),
            global_vars=td.get('global_vars', {}),
            category=td.get('category', ''),
            tags=td.get('tags', []),
            description=td.get('description', ''),
            is_draft=True,
            created_by=request.user,
        )
        return Response({
            'code': 2000, 'msg': f'已导入模板: {template.name}',
            'data': FlowTemplateSerializer(template).data,
        })

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """返回所有已使用的类别列表"""
        cats = FlowTemplate.objects.values('category').distinct().order_by('category')
        data = [c['category'] for c in cats if c['category']]
        return Response({'code': 2000, 'msg': 'success', 'data': data})

    @action(detail=True, methods=['get', 'post'])
    def hook_variables(self, request, pk=None):
        """获取或更新可提升的全局变量配置"""
        template = self.get_object()
        if request.method == 'GET':
            return Response({
                'code': 2000, 'msg': 'success',
                'data': template.hook_variables or {},
            })
        hook_vars = request.data.get('hook_variables', request.data)
        template.hook_variables = hook_vars
        template.save(update_fields=['hook_variables'])
        return Response({
            'code': 2000, 'msg': '变量配置已更新',
            'data': template.hook_variables,
        })

    # ═══════════════════════════════════════════════════════════════
    # Global Variable System (Phase 1)
    # ═══════════════════════════════════════════════════════════════

    @action(detail=True, methods=['get', 'post', 'patch'], url_path='global-variables')
    def global_variables(self, request, pk=None):
        """全局变量 CRUD

        GET:  返回所有全局变量（规范化结构）
        POST: 批量替换所有全局变量
        PATCH: 部分更新（合并现有变量）
        """
        template = self.get_object()
        from opsflow.core.variable_resolver import normalize_global_vars

        if request.method == 'GET':
            normalized = normalize_global_vars(template.global_vars)
            # 附加引用计数
            tree = template.pipeline_tree or {}
            result = {}
            for key, entry in normalized.items():
                from opsflow.core.variable_resolver import count_variable_references
                entry["reference_count"] = count_variable_references(tree, key)
                result[key] = entry
            return Response({'code': 2000, 'msg': 'success', 'data': result})

        if request.method == 'POST':
            template.global_vars = request.data.get('global_vars', {})
            # ── 无用变量自动清理 ──
            from opsflow.core.variable_resolver import cleanup_unused_vars
            cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
            template.global_vars = cleaned
            # ── 结束 ──
            template.save(update_fields=['global_vars'])
            normalized = normalize_global_vars(template.global_vars)
            return Response({'code': 2000, 'msg': '全局变量已更新', 'data': normalized})

        # PATCH — 合并更新
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
        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
        template.global_vars = cleaned
        # ── 结束 ──
        template.save(update_fields=['global_vars'])
        normalized = normalize_global_vars(template.global_vars)
        return Response({'code': 2000, 'msg': '全局变量已更新', 'data': normalized})

    @action(detail=True, methods=['get'], url_path='variable-browser')
    def variable_browser(self, request, pk=None):
        """返回所有可引用变量（全局变量 + 节点输出），供前端自动补全"""
        template = self.get_object()
        from opsflow.core.variable_resolver import normalize_global_vars
        from opsflow.plugins.registry import get_plugin

        # 1. 全局变量
        normalized = normalize_global_vars(template.global_vars)
        global_vars = [
            {"key": k, "type": v["type"], "source": "global",
             "description": v.get("description", ""),
             "value": v["value"]}
            for k, v in normalized.items()
        ]

        # 2. 节点输出（从插件 output_schema 提取）
        tree = template.pipeline_tree or {}
        node_outputs = []
        for node in tree.get('nodes', []):
            nid = node.get('id', '')
            label = node.get('label', nid)
            node_type = node.get('node_type', '')
            plugin_code = node.get('atom_type') or node.get('plugin_code', '')
            if plugin_code:
                cls = get_plugin(plugin_code)
                if cls:
                    schema = cls.get_output_schema()
                    for field in (schema or []):
                        field_key = field.get('tag_code', field.get('key', ''))
                        if field_key:
                            node_outputs.append({
                                "key": f"{nid}.{field_key}",
                                "node_id": nid,
                                "node_label": label,
                                "source": "node_output",
                                "description": field.get('name', field_key),
                            })
            # 标准 _result 输出
            if node_type in ('atom', '', None):
                node_outputs.append({
                    "key": f"{nid}._result",
                    "node_id": nid,
                    "node_label": label,
                    "source": "node_output",
                    "description": "Execution result (True/False)",
                })

        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                "global_variables": global_vars,
                "node_outputs": node_outputs,
            },
        })

    @action(detail=True, methods=['post'], url_path='hook-variable')
    def hook_variable(self, request, pk=None):
        """将节点参数提升为全局变量

        Request: {
            "var_key": "my_var",       # 变量 key (必填)
            "node_id": "node_xxx",     # 来源节点 ID (必填)
            "tag_code": "param_name",  # 来源字段名
            "var_type": "input",       # 变量类型
            "description": "..."       # 描述
        }
        """
        template = self.get_object()
        var_key = request.data.get('var_key', '')
        node_id = request.data.get('node_id', '')
        tag_code = request.data.get('tag_code', '')
        var_type = request.data.get('var_type', 'input')
        description = request.data.get('description', '')

        if not var_key or not node_id:
            return Response({'code': 4000, 'msg': 'var_key and node_id are required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        from opsflow.core.variable_resolver import normalize_global_vars
        current = normalize_global_vars(template.global_vars)

        current[var_key] = {
            "value": "",
            "type": var_type,
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
        return Response({'code': 2000, 'msg': '变量已提升为全局变量', 'data': current[var_key]})

    @action(detail=True, methods=['post'], url_path='unhook-variable')
    def unhook_variable(self, request, pk=None):
        """移除变量与节点的关联（降级为手动变量）

        Request: {"var_key": "my_var"}
        """
        template = self.get_object()
        var_key = request.data.get('var_key', '')

        from opsflow.core.variable_resolver import normalize_global_vars
        current = normalize_global_vars(template.global_vars)

        if var_key not in current:
            return Response({'code': 4000, 'msg': f'变量 {var_key} 不存在', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)

        # 移除 source_info 但保留变量
        current[var_key].update({
            "source_type": "manual",
            "source_info": None,
        })
        template.global_vars = current
        template.save(update_fields=['global_vars'])
        return Response({'code': 2000, 'msg': '已解除变量关联', 'data': current[var_key]})

    # ═══════════════════════════════════════════════════════════════
    # Subprocess Version Tracking (Phase 3)
    # ═══════════════════════════════════════════════════════════════

    @action(detail=True, methods=['get'], url_path='subprocess-status')
    def subprocess_status(self, request, pk=None):
        """检查子流程引用版本是否过期

        从 snapshot.subprocess_refs 读取引用版本，对比目标模板当前版本。
        """
        template = self.get_object()
        snapshot = template.snapshot or {}
        subprocess_refs = snapshot.get('subprocess_refs', {})

        # fallback: 实时扫描 pipeline_tree
        if not subprocess_refs:
            subprocess_refs = self._extract_subprocess_refs(template)

        from opsflow.models import FlowTemplate

        details = []
        for node_id, ref in subprocess_refs.items():
            target_id = ref.get('target_template_id')
            ref_version = ref.get('target_version')
            try:
                target = FlowTemplate.objects.get(id=target_id)
                current_version = target.version or 1
                stale = (ref_version is not None and
                         current_version is not None and
                         ref_version != current_version)
            except FlowTemplate.DoesNotExist:
                current_version = None
                stale = True

            details.append({
                'node_id': node_id,
                'target_template_id': target_id,
                'target_name': ref.get('target_name', ''),
                'referenced_version': ref_version,
                'current_version': current_version,
                'stale': stale,
            })

        stale_count = sum(1 for d in details if d['stale'])
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'total': len(details),
                'stale': stale_count,
                'details': details,
            },
        })

    @action(detail=True, methods=['post'], url_path='update-subprocess-refs')
    def update_subprocess_refs(self, request, pk=None):
        """批量更新所有子流程引用为最新版本"""
        template = self.get_object()
        tree = template.pipeline_tree or {}
        nodes = tree.get('nodes', [])
        from opsflow.models import FlowTemplate

        updated = []
        for node in nodes:
            if node.get('node_type') != 'subprocess':
                continue
            params = node.get('params', {}) or {}
            target_id = params.get('target_template_id')
            if not target_id:
                continue
            try:
                target = FlowTemplate.objects.get(id=target_id)
                current_version = target.version or 1
                params['_referenced_version'] = current_version
                node['params'] = params
                updated.append({
                    'node_id': node['id'],
                    'target_template_id': target_id,
                    'new_version': current_version,
                })
            except FlowTemplate.DoesNotExist:
                continue

        template.pipeline_tree = tree
        template.save(update_fields=['pipeline_tree'])
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'total': len(updated),
                'updated_nodes': updated,
                'message': f'已更新 {len(updated)} 个子流程引用',
            },
        })

    def _extract_subprocess_refs(self, template) -> dict:
        """从 pipeline_tree 实时提取子流程引用（fallback）"""
        refs = {}
        tree = template.pipeline_tree or {}
        for node in tree.get('nodes', []):
            if node.get('node_type') == 'subprocess':
                params = node.get('params', {}) or {}
                target_id = params.get('target_template_id')
                if target_id:
                    refs[node['id']] = {
                        'target_template_id': target_id,
                        'target_version': None,
                        'target_name': '',
                    }
        return refs
