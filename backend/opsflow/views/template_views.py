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
