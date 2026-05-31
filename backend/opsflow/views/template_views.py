import re
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import FlowTemplate
from opsflow.serializers import FlowTemplateSerializer
from opsflow.core.llm_service import generate_pipeline, optimize_layout, analyze_pipeline, refine_pipeline
from opsflow.core.layout import compute_layout
from opsflow.core.safety_guard import validate_pipeline
from opsflow.core.bamboo_builder import validate_bamboo_compatibility
from dvadmin.utils.json_response import DetailResponse

logger = logging.getLogger(__name__)


class FlowTemplateViewSet(viewsets.ModelViewSet):
    queryset = FlowTemplate.objects.all()
    serializer_class = FlowTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_draft', 'created_by']
    search_fields = ['name']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

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
        """用户确认草稿，标记 is_draft=False 正式入库"""
        template = self.get_object()
        if not template.is_draft:
            return Response({'code': 4000, 'msg': '不是草稿状态', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        # 重新校验 SafetyGuard
        safety = validate_pipeline(template.pipeline_tree)
        if not safety.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程存在安全风险，请检查后再确认',
                'data': {'validation': safety}
            }, status=status.HTTP_400_BAD_REQUEST)

        # bamboo-engine 兼容性校验
        bamboo_check = validate_bamboo_compatibility(template.pipeline_tree)
        if not bamboo_check.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程不兼容 bamboo-engine',
                'data': {'bamboo_check': bamboo_check}
            }, status=status.HTTP_400_BAD_REQUEST)

        template.is_draft = False
        template.save()
        return Response({'code': 2000, 'msg': 'success', 'data': FlowTemplateSerializer(template).data})

    @action(detail=False, methods=['post'])
    def ai_layout(self, request):
        """布局优化：默认使用确定性 Sugiyama 算法，?method=ai 走 AI 布局"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return Response({'code': 4000, 'msg': 'nodes is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        method = request.query_params.get('method', 'sugiyama')
        try:
            if method == 'ai':
                positions = optimize_layout(nodes, edges)
            else:
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
